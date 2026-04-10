# DeepTech News Tracker

ディープテック（Physical AI / 自動運転 / ヒューマノイド / 量子 / フュージョン / バイオテックなど）と主要国際学会（ICLR / CVPR / NeurIPS / ICML / ICRA / CoRL / ECCV / ICCV / SIGGRAPH など）の最新動向を、毎日・毎週自動で収集してMarkdown形式のレポートにまとめるシステムです。

## 目的

1. **毎日5件のディープテックニュース** を X(Twitter) / RSS / オンラインメディアから収集
2. **主要国際学会の論文** を arXiv / OpenReview / 公式サイトから収集し、特徴・進歩性を要約
3. GitHub Actions 上で定期実行し、`reports/` 配下に履歴として蓄積

## ディレクトリ構成

```
deeptech-tracker/
├── README.md                 # このファイル
├── requirements.txt          # Python 依存パッケージ
├── sources.yaml              # ニュース・論文ソースの設定
├── scripts/
│   ├── fetch_news.py         # RSS / X ポスト収集
│   ├── fetch_papers.py       # arXiv / OpenReview 論文収集
│   ├── summarize.py          # Claude API で要約（任意）
│   └── generate_report.py    # 日次 / 週次レポート生成
└── reports/
    ├── daily/                # 毎日のニュースレポート (YYYY-MM-DD.md)
    └── conferences/          # 学会論文の週次レポート
```

## 実行方法

### ローカル実行

```bash
cd deeptech-tracker
pip install -r requirements.txt

# 毎日のニュースレポートを生成
python scripts/generate_report.py --mode daily

# 週次の学会論文レポートを生成
python scripts/generate_report.py --mode conference
```

### GitHub Actions による自動実行

- **毎日 09:00 JST** → `deeptech-daily.yml` がデイリーニュースレポートを `reports/daily/` に自動コミット
- **毎週月曜 09:00 JST** → `deeptech-papers-weekly.yml` が学会論文の週次レポートを `reports/conferences/` に自動コミット

いずれも `workflow_dispatch` に対応しており、GitHub 上から手動トリガーも可能です。

## ソース設定 (`sources.yaml`)

`sources.yaml` にて収集対象の RSS フィード、X アカウント、arXiv カテゴリ、学会名を柔軟に追加・編集できます。カテゴリごとに優先度を設定できるため、Physical AI 関連をトップに寄せるなどの制御が可能です。

## 要約品質について

`scripts/summarize.py` は `ANTHROPIC_API_KEY` が設定されている場合に Claude API (`claude-opus-4-6` / `claude-sonnet-4-6`) を利用して日本語要約を行います。API キーがない場合はフォールバックとしてタイトル + スニペットをそのまま使用します。

## 対象技術領域

### Physical AI

- ヒューマノイドロボット (Figure, Tesla Optimus, Unitree, Agibot, 1X, Sanctuary など)
- 自動運転 (Waymo, Tesla FSD, Wayve, Mobileye, Pony.ai, Momenta など)
- VLA (Vision-Language-Action) / Robot Foundation Model (NVIDIA GR00T, π0, OpenVLA, RT-X など)
- Embodied AI / ロボット基盤モデル
- Drone / UAV / Swarm

### その他ディープテック

- 量子コンピューティング (超伝導 / 中性原子 / イオントラップ / 光量子)
- 核融合 / SMR / 次世代原子力
- バイオテック / 創薬AI / 合成生物学
- 半導体 / フォトニクス / HBM / チップレット
- 宇宙 / 衛星コンステレーション / 再使用ロケット
- 暗号 / PQC / ゼロ知識証明

## 関連ワークフロー

- `.github/workflows/deeptech-daily.yml`
- `.github/workflows/deeptech-papers-weekly.yml`
