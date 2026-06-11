"""
X (Twitter) 雑学バズ投稿ボット
- Claude APIでバズりやすい雑学ツイートを生成（requests直接呼び出し）
- スコアリングして品質チェック
- X API v2で自動投稿
"""

import os
import json
import random
import requests
import tweepy
from datetime import datetime
from pathlib import Path

# ── クライアント初期化 ──────────────────────────────────────────
def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

# ── トピック一覧（雑学・豆知識ジャンル） ────────────────────────
TOPICS = [
    "人体・脳科学の不思議な事実",
    "歴史上の意外な出来事",
    "動物・生き物の驚くべき能力",
    "食べ物・料理の意外な起源",
    "宇宙・地球のスケールが大きすぎる話",
    "言語・語源の面白い話",
    "心理学の不思議な現象",
    "科学・物理の直感に反する事実",
    "数学の面白いトリビア",
    "お金・経済の意外な話",
    "テクノロジーの知られざる歴史",
    "日本の文化・習慣の意外なルーツ",
]

# ── Claude API呼び出し（requests直接） ──────────────────────────
def call_claude(prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]

# ── ツイート生成 ────────────────────────────────────────────────
def generate_tweet(topic: str) -> dict:
    prompt = f"""あなたはTwitterで何十万インプレッションも稼ぐ「雑学・豆知識」アカウントの中の人です。

以下のトピックについて、バズりやすいツイートを1つ作成してください。

トピック：{topic}

【バズるツイートの条件】
- 「え、知らなかった！」「本当に？」と思わず反応したくなる内容
- 数字や具体例を入れて説得力を出す
- 冒頭の一文でスクロールを止める（hook）
- リプ・引用RTしたくなる問いかけや余白を残す
- 140文字以内に収める
- 絵文字を効果的に使う（2〜4個）
- ハッシュタグは1〜2個まで

【出力形式】（JSONのみ返す。余分なテキスト不要）
{{"tweet": "ツイート本文", "hook_score": 8, "curiosity_score": 7, "share_score": 9, "reason": "バズ理由一文"}}"""

    raw = call_claude(prompt).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["topic"] = topic
    data["total_score"] = data["hook_score"] + data["curiosity_score"] + data["share_score"]
    return data

# ── 複数候補を生成してベストを選ぶ ─────────────────────────────
def pick_best_tweet(n_candidates: int = 3) -> dict:
    topics = random.sample(TOPICS, min(n_candidates, len(TOPICS)))
    candidates = []
    for topic in topics:
        try:
            result = generate_tweet(topic)
            candidates.append(result)
            print(f"  [{result['total_score']}/30] {result['tweet'][:40]}...")
        except Exception as e:
            print(f"  生成エラー（{topic}）: {e}")
    if not candidates:
        raise RuntimeError("ツイート候補を1件も生成できませんでした")
    return max(candidates, key=lambda x: x["total_score"])

# ── 投稿 ────────────────────────────────────────────────────────
def post_tweet(client: tweepy.Client, tweet_text: str) -> str:
    response = client.create_tweet(text=tweet_text)
    return response.data["id"]

# ── ログ保存 ─────────────────────────────────────────────────────
def save_log(data: dict, tweet_id: str):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "tweet_history.jsonl"
    entry = {"timestamp": datetime.utcnow().isoformat(), "tweet_id": tweet_id, **data}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  ログ保存: {log_file}")

# ── メイン ──────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"🤖 X バズ投稿ボット起動 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print(f"{'='*50}")

    twitter = get_twitter_client()

    print("\n📝 ツイート候補を生成中...")
    best = pick_best_tweet(n_candidates=3)

    print(f"\n✨ 最高スコアのツイート（{best['total_score']}/30）")
    print(f"  トピック: {best['topic']}")
    print(f"  内容: {best['tweet']}")
    print(f"  理由: {best['reason']}")

    if best["total_score"] < 18:
        print(f"\n⚠️  スコアが基準（18点）未満のため投稿をスキップしました")
        return

    print("\n🚀 投稿中...")
    tweet_id = post_tweet(twitter, best["tweet"])
    print(f"  ✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}")

    save_log(best, tweet_id)
    print("\n完了！\n")

if __name__ == "__main__":
    main()
