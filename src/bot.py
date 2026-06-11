"""
X (Twitter) 旅行・クレカ・航空券バズ投稿ボット
- 旅行/一人旅/クレ活/ラウンジ/空港/航空券に特化
- 過去ネタをJSONで記録してかぶりを防止
- Stability AIで画像生成
- X API v2で画像付き自動投稿
"""

import os
import json
import random
import requests
import tweepy
from datetime import datetime
from pathlib import Path

# ── Twitterクライアント ──────────────────────────────────────────
def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

def get_twitter_api_v1():
    auth = tweepy.OAuth1UserHandler(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    return tweepy.API(auth)

# ── トピック一覧（旅行・クレ活特化） ───────────────────────────
TOPICS = [
    # 航空券・マイル
    "知らないと損する航空券の最安値の取り方",
    "マイルを最速で貯める裏技",
    "ビジネスクラスに格安で乗る方法",
    "航空券の価格が下がるタイミングと曜日",
    "LCCの隠れた落とし穴と回避法",
    "特典航空券の空席を見つけるコツ",
    "航空会社のステータス修行の賢いやり方",
    "オープンジョーとストップオーバーの活用術",

    # クレジットカード・クレ活
    "旅行好きが絶対持つべきクレジットカード",
    "年会費無料でラウンジが使えるカードの真実",
    "海外旅行保険が自動付帯されるカードの選び方",
    "ポイント二重取り・三重取りの具体的な方法",
    "クレカの旅行特典で実質無料になるもの一覧",
    "プライオリティパスの賢い取得方法",
    "外貨手数料ゼロのカードで海外旅費を節約する方法",

    # 空港ラウンジ
    "空港ラウンジを無料で使う全方法まとめ",
    "世界最高クラスの空港ラウンジ体験談",
    "成田・羽田の隠れた穴場ラウンジ情報",
    "ラウンジでもらえる無料サービスを最大活用する方法",
    "同伴者もラウンジに入れる条件と方法",

    # 一人旅・海外旅行
    "一人旅初心者が絶対知るべき安全対策",
    "海外一人旅でホテル代を半額以下にする方法",
    "一人旅でビジネスクラスが劇的に捗る理由",
    "海外旅行で絶対入れるべき保険と不要な保険",
    "一人旅で現地の食事代を節約する現地民の知恵",
    "深夜便・早朝便を快適に過ごす完全ガイド",
    "海外SIMとポケットWiFiどちらが本当にお得か",

    # 空港・旅のノウハウ
    "保安検査を最速で通過するパッキング術",
    "受託手荷物料金をゼロにする合法的な方法",
    "空港での時間を最大限有効活用する方法",
    "フライト遅延・欠航時に絶対やるべきこと",
    "座席指定で快適度が劇的に変わる選び方",
    "国際線の機内食を無料でアップグレードする方法",
    "旅行者が知らない空港の隠れたサービス",
]

# ── 過去ネタ管理（かぶり防止） ──────────────────────────────────
USED_TOPICS_FILE = "logs/used_topics.json"

def load_used_topics():
    path = Path(USED_TOPICS_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_used_topic(topic, tweet):
    path = Path(USED_TOPICS_FILE)
    path.parent.mkdir(exist_ok=True)
    used = load_used_topics()
    used.append({
        "topic": topic,
        "tweet": tweet,
        "date": datetime.utcnow().isoformat()
    })
    # 直近100件だけ保持
    used = used[-100:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

def get_unused_topics():
    used = load_used_topics()
    used_topics = {u["topic"] for u in used}
    unused = [t for t in TOPICS if t not in used_topics]
    # 全部使い切ったらリセット
    if not unused:
        print("  全トピック使用済み→リセット")
        return TOPICS
    return unused

# ── Claude API ──────────────────────────────────────────────────
def call_claude(prompt):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]

# ── ツイート生成 ────────────────────────────────────────────────
def generate_tweet(topic, used_tweets):
    used_examples = "\n".join([f"- {t}" for t in used_tweets[-10:]]) if used_tweets else "なし"

    prompt = f"""あなたは旅行・マイル・クレジットカード・空港ラウンジに詳しく、Twitterで何十万インプレッションを稼ぐアカウントの運営者です。

トピック：{topic}

以下の過去ツイートと内容がかぶらないようにしてください：
{used_examples}

【条件】
- 140文字以内
- 絵文字は使わない
- 自然な日本語・体験談風または驚き情報風
- 「知らないと損」「実は」「○○するだけで」など具体的なhookで始める
- 数字や具体的なサービス名を入れてリアリティを出す
- ハッシュタグは1〜2個（#旅行 #クレカ #マイル #一人旅 #空港 から選ぶ）

JSONのみ返す：{{"tweet":"本文","image_prompt":"この内容に合う画像の英語プロンプト（空港・飛行機・ラウンジ・旅行風景など、photorealistic）","hook_score":8,"curiosity_score":7,"share_score":9,"reason":"理由"}}"""

    raw = call_claude(prompt).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["topic"] = topic
    data["total_score"] = data["hook_score"] + data["curiosity_score"] + data["share_score"]
    return data

# ── 複数候補からベストを選ぶ ────────────────────────────────────
def pick_best_tweet():
    unused = get_unused_topics()
    topics = random.sample(unused, min(3, len(unused)))
    used_tweets = [u["tweet"] for u in load_used_topics()]
    candidates = []

    for topic in topics:
        try:
            result = generate_tweet(topic, used_tweets)
            candidates.append(result)
            print(f"  [{result['total_score']}/30] {result['tweet'][:40]}...")
        except Exception as e:
            print(f"  エラー（{topic}）: {e}")

    if not candidates:
        raise RuntimeError("候補を生成できませんでした")
    return max(candidates, key=lambda x: x["total_score"])

# ── Stability AI 画像生成 ───────────────────────────────────────
def generate_image(image_prompt):
    import base64
    print(f"  画像生成中: {image_prompt[:50]}...")
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "authorization": f"Bearer {os.environ['STABILITY_API_KEY']}",
        "content-type": "application/json",
        "accept": "application/json",
    }
    body = {
        "text_prompts": [
            {"text": image_prompt + ", photorealistic, high quality, travel photography", "weight": 1}
        ],
        "width": 1024,
        "height": 576,
        "steps": 30,
        "samples": 1,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    img_data = resp.json()["artifacts"][0]["base64"]
    img_path = "/tmp/tweet_image.jpg"
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(img_data))
    print("  画像生成完了！")
    return img_path

# ── 画像付きツイート投稿 ────────────────────────────────────────
def post_tweet_with_image(client, api_v1, tweet_text, img_path):
    media = api_v1.media_upload(img_path)
    media_id = media.media_id
    print(f"  画像アップロード完了 (media_id: {media_id})")
    resp = client.create_tweet(text=tweet_text, media_ids=[media_id])
    return resp.data["id"]

# ── メイン ──────────────────────────────────────────────────────
def main():
    print("🤖 ボット起動")
    twitter = get_twitter_client()
    api_v1 = get_twitter_api_v1()

    print("📝 ツイート生成中...")
    best = pick_best_tweet()
    print(f"✨ スコア{best['total_score']}/30: {best['tweet']}")

    if best["total_score"] < 18:
        print("⚠️ スコア不足のためスキップ")
        return

    img_path = generate_image(best["image_prompt"])

    print("🚀 投稿中...")
    tweet_id = post_tweet_with_image(twitter, api_v1, best["tweet"], img_path)
    print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}")

    save_used_topic(best["topic"], best["tweet"])

if __name__ == "__main__":
    main()
