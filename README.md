# 🤖 X バズ投稿ボット（雑学・豆知識特化）

Claude APIで「バズりやすい雑学ツイート」を自動生成し、1日3回 X に投稿するボットです。

---

## 仕組み

```
毎日 8:00 / 12:00 / 20:00（JST）
    ↓
3つのランダムトピックでツイート候補を生成
    ↓
Hook・Curiosity・Share の3軸でスコアリング
    ↓
最高スコアのツイートを採用（18点未満はスキップ）
    ↓
X に自動投稿 → ログ保存
```

---

## セットアップ手順

### Step 1：X API キーを取得する

1. [https://developer.x.com](https://developer.x.com) にアクセス
2. 「Sign up for Free Account」で登録
3. アプリを作成し、以下の4つを取得：
   - `API Key`
   - `API Secret`
   - `Access Token`（Read and Write権限が必要）
   - `Access Token Secret`

> ⚠️ Access TokenはRead and Write権限で生成してください（Readのみだと投稿できません）

### Step 2：Anthropic API キーを取得する

1. [https://console.anthropic.com](https://console.anthropic.com) にアクセス
2. API Keys → 「Create Key」で取得

### Step 3：GitHubリポジトリにシークレットを登録

リポジトリの `Settings > Secrets and variables > Actions` に以下を追加：

| シークレット名 | 値 |
|---|---|
| `X_API_KEY` | X APIのAPI Key |
| `X_API_SECRET` | X APIのAPI Secret |
| `X_ACCESS_TOKEN` | X APIのAccess Token |
| `X_ACCESS_TOKEN_SECRET` | X APIのAccess Token Secret |
| `ANTHROPIC_API_KEY` | AnthropicのAPI Key |

### Step 4：GitHub Actionsを有効化

1. リポジトリの「Actions」タブを開く
2. Workflowを有効化する
3. 「Run workflow」で手動テスト実行できます

---

## ローカルでテスト（投稿なし）

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=your_key_here
python test_dry_run.py
```

---

## カスタマイズ

### 投稿時間を変える
`.github/workflows/tweet.yml` の `cron` を編集（UTC表記）

```yaml
# JST = UTC + 9時間
- cron: "0 23 * * *"  # JST 08:00
- cron: "0 3 * * *"   # JST 12:00
- cron: "0 11 * * *"  # JST 20:00
```

### トピックを追加・変更する
`src/bot.py` の `TOPICS` リストを編集

### サイト宣伝ツイートの頻度を変える
`PROMO_EVERY` 投稿に1回、Card Collection（クレカ比較・コレクションサイト）の宣伝ツイートを
通常投稿の代わりに自動投稿します。宣伝文はClaudeが毎回自然な口語で生成し、末尾にサイトURLを付与します。

- デフォルトは **2**（2投稿に1回＝1日3投稿なら毎日1〜2回）
- 無効化するには `0`
- 変更は GitHub Actions の env か、リポジトリの Variables で `PROMO_EVERY` を設定
- 宣伝先URLは `PROMO_URL`（デフォルト `https://credit-card-collection.vercel.app`）

### 品質ゲートのスコアを変える
`src/bot.py` の `if best["total_score"] < 18:` の数値を調整
（18〜24推奨。高いほど厳しくなりスキップが増える）

---

## ファイル構成

```
x-buzz-bot/
├── src/
│   └── bot.py              # メインのボットスクリプト
├── .github/
│   └── workflows/
│       └── tweet.yml       # GitHub Actions（自動実行）
├── logs/
│   └── tweet_history.jsonl # 投稿ログ（自動生成）
├── test_dry_run.py         # ローカルテスト用
└── requirements.txt
```
