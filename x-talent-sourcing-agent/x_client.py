"""X (Twitter) API client for talent sourcing."""

import tweepy
from dataclasses import dataclass, field


@dataclass
class XUserProfile:
    """Represents a user profile fetched from X."""

    user_id: str
    username: str
    name: str
    bio: str
    location: str
    url: str
    followers_count: int
    following_count: int
    tweet_count: int
    verified: bool
    profile_url: str
    recent_tweets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "name": self.name,
            "bio": self.bio,
            "location": self.location,
            "url": self.url,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "tweet_count": self.tweet_count,
            "verified": self.verified,
            "profile_url": self.profile_url,
            "recent_tweets": self.recent_tweets,
        }


class XClient:
    """Client for searching X users and tweets."""

    def __init__(self, bearer_token: str):
        self.client = tweepy.Client(bearer_token=bearer_token)

    def search_tweets(
        self, query: str, max_results: int = 50
    ) -> list[dict]:
        """Search recent tweets matching the query.

        Returns list of dicts with tweet text, author_id, and tweet metadata.
        """
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=["author_id", "created_at", "public_metrics", "lang"],
                user_fields=[
                    "name",
                    "username",
                    "description",
                    "location",
                    "public_metrics",
                    "url",
                    "verified",
                ],
                expansions=["author_id"],
            )
        except tweepy.errors.TweepyException as e:
            print(f"[Error] Tweet search failed: {e}")
            return []

        if not response.data:
            return []

        users_map = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                users_map[user.id] = user

        results = []
        for tweet in response.data:
            author = users_map.get(tweet.author_id)
            results.append(
                {
                    "tweet_id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(tweet.author_id),
                    "created_at": str(tweet.created_at),
                    "metrics": tweet.public_metrics,
                    "author": (
                        {
                            "name": author.name,
                            "username": author.username,
                            "bio": author.description or "",
                            "location": author.location or "",
                            "followers": author.public_metrics["followers_count"],
                        }
                        if author
                        else None
                    ),
                }
            )
        return results

    def get_user_profile(self, username: str) -> XUserProfile | None:
        """Fetch a user's full profile by username."""
        try:
            response = self.client.get_user(
                username=username,
                user_fields=[
                    "name",
                    "username",
                    "description",
                    "location",
                    "public_metrics",
                    "url",
                    "verified",
                    "created_at",
                ],
            )
        except tweepy.errors.TweepyException as e:
            print(f"[Error] Failed to fetch user @{username}: {e}")
            return None

        if not response.data:
            return None

        user = response.data
        metrics = user.public_metrics

        profile = XUserProfile(
            user_id=str(user.id),
            username=user.username,
            name=user.name,
            bio=user.description or "",
            location=user.location or "",
            url=user.url or "",
            followers_count=metrics["followers_count"],
            following_count=metrics["following_count"],
            tweet_count=metrics["tweet_count"],
            verified=user.verified or False,
            profile_url=f"https://x.com/{user.username}",
        )

        profile.recent_tweets = self._fetch_recent_tweets(user.id)
        return profile

    def _fetch_recent_tweets(self, user_id: int, max_results: int = 10) -> list[str]:
        """Fetch recent tweets from a user."""
        try:
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=["created_at"],
                exclude=["retweets"],
            )
        except tweepy.errors.TweepyException:
            return []

        if not response.data:
            return []

        return [tweet.text for tweet in response.data]

    def search_users_by_keywords(
        self, keywords: list[str], max_results_per_keyword: int = 30
    ) -> dict[str, XUserProfile]:
        """Search for users across multiple keywords, deduplicated by username."""
        seen_users: dict[str, XUserProfile] = {}

        for keyword in keywords:
            tweets = self.search_tweets(
                query=f"{keyword} -is:retweet lang:ja",
                max_results=max_results_per_keyword,
            )

            usernames_to_fetch = set()
            for tweet in tweets:
                if tweet["author"] and tweet["author"]["username"] not in seen_users:
                    usernames_to_fetch.add(tweet["author"]["username"])

            for username in usernames_to_fetch:
                if username not in seen_users:
                    profile = self.get_user_profile(username)
                    if profile:
                        seen_users[username] = profile

        return seen_users
