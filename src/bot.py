import os
import json
import random
import requests
import tweepy
from datetime import datetime
from pathlib import Path

def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

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

def call_claude(prompt):
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

def generate_tweet(topic):
    prompt = f"""あなたはTwitterで何十万インプレッションも稼ぐ「雑学・豆知識」アカウントの中の人です。
トピック：{topic}
バズりやすいツイートを1つ作成してください。
条件：140文字以内、絵文字2〜4個、ハッシュタグ1〜2個、冒頭でスクロールを止めるhook。
JSONのみ返す：{{"tweet":"本文","hook_score":8,"curiosity_score":7,"share_score":9,"reason":"理由"}}"""
    raw = call_claude(prompt).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["topic"] = topic
    data["total_score"] = data["hook_score"] + data["curiosity_score"] + data["share_score"]
    return data

def pick_best_tweet():
    topics = random.sample(TOPICS, 3)
    candidates = []
    for topic in topics:
        try:
            result = generate_tweet(topic)
            candidates.append(result)
            print(f"  [{result['total_score']}/30] {result['tweet'][:40]}...")
        except Exception as e:
            print(f"  エラー（{topic}）: {e}")
    if not candidates:
        raise RuntimeError("候補を生成できませんでした")
    return max(candidates, key=lambda x: x["total_score"])

def main():
    print("🤖 ボット起動")
    twitter = get_twitter_client()
    print("📝 ツイート生成中...")
    best = pick_best_tweet()
    print(f"✨ スコア{best['total_score']}/30: {best['tweet']}")
    if best["total_score"] < 18:
        print("⚠️ スコア不足のためスキップ")
        return
    print("🚀 投稿中...")
    resp = twitter.create_tweet(text=best["tweet"])
    tweet_id = resp.data["id"]
    print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}")

if __name__ == "__main__":
    main()
