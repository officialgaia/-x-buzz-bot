"""
X (Twitter) 旅行・クレカ・航空券バズ投稿ボット
- 旅行/一人旅/クレ活/ラウンジ/空港/航空券に特化
- 過去ネタをJSONで記録してかぶりを防止
- 9投稿に1回だけ画像付き（Stability AI）
- X API v2で自動投稿
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
    "知らないと損する航空券の最安値の取り方",
    "マイルを最速で貯める裏技",
    "ビジネスクラスに格安で乗る方法",
    "航空券の価格が下がるタイミングと曜日",
    "LCCの隠れた落とし穴と回避法",
    "特典航空券の空席を見つけるコツ",
    "航空会社のステータス修行の賢いやり方",
    "オープンジョーとストップオーバーの活用術",
    "旅行好きが絶対持つべきクレジットカード",
    "年会費無料でラウンジが使えるカードの真実",
    "海外旅行保険が自動付帯されるカードの選び方",
    "ポイント二重取り・三重取りの具体的な方法",
    "クレカの旅行特典で実質無料になるもの一覧",
    "プライオリティパスの賢い取得方法",
    "外貨手数料ゼロのカードで海外旅費を節約する方法",
    "空港ラウンジを無料で使う全方法まとめ",
    "世界最高クラスの空港ラウンジ体験談",
    "成田・羽田の隠れた穴場ラウンジ情報",
    "ラウンジでもらえる無料サービスを最大活用する方法",
    "同伴者もラウンジに入れる条件と方法",
    "一人旅初心者が絶対知るべき安全対策",
    "海外一人旅でホテル代を半額以下にする方法",
    "一人旅でビジネスクラスが劇的に捗る理由",
    "海外旅行で絶対入れるべき保険と不要な保険",
    "一人旅で現地の食事代を節約する現地民の知恵",
    "深夜便・早朝便を快適に過ごす完全ガイド",
    "海外SIMとポケットWiFiどちらが本当にお得か",
    "保安検査を最速で通過するパッキング術",
    "受託手荷物料金をゼロにする合法的な方法",
    "空港での時間を最大限有効活用する方法",
    "フライト遅延・欠航時に絶対やるべきこと",
    "座席指定で快適度が劇的に変わる選び方",
    "国際線の機内食を無料でアップグレードする方法",
    "旅行者が知らない空港の隠れたサービス",
]

# ── サイト宣伝設定（Card Collection） ──────────────────────────
PROMO_URL = os.environ.get("PROMO_URL", "https://credit-card-collection.vercel.app")
# 何投稿に1回 宣伝ツイートを挟むか（0で無効。デフォルト5＝5回に1回）
PROMO_EVERY = int(os.environ.get("PROMO_EVERY", "5"))
PROMO_ANGLES = [
    "日本で発行できるクレジットカードを一覧で比較できる",
    "持っているカードをチェックしてコレクションとして可視化できる",
    "年会費・還元率・空港ラウンジなどの条件でカードを絞り込める",
    "自分の所有カードの合計年会費や収集率が一目でわかる",
    "ポイント還元シミュレーターで自分に合う1枚が見つかる",
    "ゴールド・プラチナ・ブラックなどランク別にカードを集められる",
    "海外旅行保険が自動付帯のカードを条件で探せる",
]

# ── 投稿カウント管理 ────────────────────────────────────────────
COUNTER_FILE = "logs/post_counter.json"

def load_counter():
    path = Path(COUNTER_FILE)
    if not path.exists():
        return {"count": 0}
    with open(path, "r") as f:
        return json.load(f)

def save_counter(count):
    path = Path(COUNTER_FILE)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w") as f:
        json.dump({"count": count}, f)

def should_post_image():
    """9投稿に1回だけ画像付き"""
    counter = load_counter()
    return counter["count"] % 9 == 0

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
    used.append({"topic": topic, "tweet": tweet, "date": datetime.utcnow().isoformat()})
    used = used[-100:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

def get_unused_topics():
    used = load_used_topics()
    used_topics = {u["topic"] for u in used}
    unused = [t for t in TOPICS if t not in used_topics]
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
    prompt = f"""あなたは旅行・マイル・クレジットカード・空港ラウンジの情報を発信するTwitterアカウントの運営者です。

トピック：{topic}

以下の過去ツイートと内容がかぶらないようにしてください：
{used_examples}

【文体の条件】
- 140文字以内
- 絵文字は使わない
- 「知らないと損」「実は」「【衝撃】」「驚き」などの決まり文句は使わない
- AIが書いた感じにならないよう、実際に旅行好きの人間が書いたような自然な口語体
- 体験談・気づき・具体的な数字を使って信頼感を出す
- 文末に軽い問いかけや余白を入れてもOK
- ハッシュタグは使わない

【良い例】
- 「楽天プレミアムカード、年会費11000円って高く見えるけど羽田ラウンジ使うだけで元取れる。年4回以上国内線乗る人はマジでおすすめ。」
- 「JALの特典航空券、火曜と水曜に空席が出やすい。毎週この曜日にチェックするだけでハワイのビジネスが取れた。」

JSONのみ返す：{{"tweet":"本文","image_prompt":"この内容に合う画像の英語プロンプト（空港・飛行機・ラウンジ・旅行風景など、photorealistic, no text, no people）","hook_score":8,"curiosity_score":7,"share_score":9,"reason":"理由"}}"""

    raw = call_claude(prompt).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    data["topic"] = topic
    data["total_score"] = data["hook_score"] + data["curiosity_score"] + data["share_score"]
    return data

# ── サイト宣伝ツイート生成 ──────────────────────────────────────
def generate_promo_tweet():
    """Card Collection の宣伝ツイートを自然な口語で生成し、末尾にURLを付ける。"""
    angle = random.choice(PROMO_ANGLES)
    used_tweets = [u["tweet"] for u in load_used_topics()]
    recent = "\n".join([f"- {t}" for t in used_tweets[-10:]]) if used_tweets else "なし"
    prompt = f"""あなたは旅行・マイル・クレジットカードの情報を発信するTwitterアカウントの運営者です。
自分が作った無料のクレジットカード比較・コレクションサイト「Card Collection」を、さりげなく紹介するツイートを書きます。

今回の切り口：{angle}

【文体の条件】
- 140文字以内（URLは別途末尾に自動で付くので、本文にURLは含めない）
- 絵文字・ハッシュタグは使わない
- 宣伝くさくしすぎない。普段の発信の延長で、実際に役立つトーン
- 「知らないと損」「衝撃」「驚き」などの煽り文句は使わない
- AIが書いた感じにならない自然な口語体
- サービス名「Card Collection」を一度だけ自然に入れる

以下の過去ツイートと内容・言い回しがかぶらないように：
{recent}

JSONのみ返す：{{"tweet":"本文（URLは含めない）"}}"""
    raw = call_claude(prompt).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    body = data["tweet"].strip()
    return f"{body}\n{PROMO_URL}", angle

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
    print(f"  画像生成中: {image_prompt[:50]}...")
    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "authorization": f"Bearer {os.environ['STABILITY_API_KEY']}",
        "accept": "image/*",
    }
    files = {
        "prompt": (None, image_prompt + ", photorealistic, high quality, travel photography, no text, no people"),
        "output_format": (None, "jpeg"),
        "model": (None, "sd3-turbo"),
        "aspect_ratio": (None, "16:9"),
    }
    resp = requests.post(url, headers=headers, files=files, timeout=60)
    if not resp.ok:
        print(f"  画像生成エラー: {resp.status_code} {resp.text[:200]}")
        return None
    img_path = "/tmp/tweet_image.jpg"
    with open(img_path, "wb") as f:
        f.write(resp.content)
    print("  画像生成完了！")
    return img_path

# ── 投稿 ────────────────────────────────────────────────────────
def post_tweet(client, tweet_text):
    resp = client.create_tweet(text=tweet_text)
    return resp.data["id"]

def post_tweet_with_image(client, api_v1, tweet_text, img_path):
    media = api_v1.media_upload(img_path)
    print(f"  画像アップロード完了 (media_id: {media.media_id})")
    resp = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
    return resp.data["id"]

# ── メイン ──────────────────────────────────────────────────────
def main():
    print("🤖 ボット起動")
    twitter = get_twitter_client()
    api_v1 = get_twitter_api_v1()

    counter = load_counter()

    # 一定間隔で Card Collection の宣伝ツイートを投稿（バズ投稿の代わり）
    if PROMO_EVERY > 0 and counter["count"] > 0 and counter["count"] % PROMO_EVERY == 0:
        print("📣 宣伝ツイート生成中...")
        try:
            tweet_text, angle = generate_promo_tweet()
            print(f"📣 {tweet_text}")
            tweet_id = post_tweet(twitter, tweet_text)
            print(f"✅ 宣伝投稿完了！ https://x.com/i/web/status/{tweet_id}")
            save_counter(counter["count"] + 1)
            save_used_topic(f"PROMO:{angle}", tweet_text)
            return
        except Exception as e:
            print(f"⚠️ 宣伝ツイート失敗（通常投稿に切替）: {e}")

    print("📝 ツイート生成中...")
    best = pick_best_tweet()
    print(f"✨ スコア{best['total_score']}/30: {best['tweet']}")

    if best["total_score"] < 18:
        print("⚠️ スコア不足のためスキップ")
        return

    use_image = should_post_image()
    print(f"  投稿カウント: {counter['count']} / 画像付き: {use_image}")

    tweet_id = None
    if use_image:
        img_path = generate_image(best["image_prompt"])
        if img_path:
            print("🚀 画像付きで投稿中...")
            tweet_id = post_tweet_with_image(twitter, api_v1, best["tweet"], img_path)
        else:
            print("🚀 画像生成失敗のためテキストのみ投稿...")
            tweet_id = post_tweet(twitter, best["tweet"])
    else:
        print("🚀 テキストのみで投稿中...")
        tweet_id = post_tweet(twitter, best["tweet"])

    print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}")
    save_counter(counter["count"] + 1)
    save_used_topic(best["topic"], best["tweet"])

if __name__ == "__main__":
    main()
