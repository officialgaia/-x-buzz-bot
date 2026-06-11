"""
ローカルテスト用スクリプト
実際には投稿せず、生成されるツイートを確認できる
"""

import os
import json
import random
from src.bot import get_claude_client, pick_best_tweet

def main():
    print("🧪 テストモード（投稿しません）\n")

    # ANTHROPIC_API_KEYだけ設定すれば動作確認できる
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        print("   export ANTHROPIC_API_KEY=your_key_here")
        return

    claude = get_claude_client()

    print("📝 ツイート候補を3件生成中...\n")
    best = pick_best_tweet(claude, n_candidates=3)

    print(f"\n{'='*50}")
    print(f"✨ 最高スコア: {best['total_score']}/30")
    print(f"トピック: {best['topic']}")
    print(f"\n【ツイート本文】\n{best['tweet']}")
    print(f"\n【スコア内訳】")
    print(f"  Hook（引きつけ力）  : {best['hook_score']}/10")
    print(f"  Curiosity（知りたい度）: {best['curiosity_score']}/10")
    print(f"  Share（シェアしたい度）: {best['share_score']}/10")
    print(f"\n【バズ予想理由】\n{best['reason']}")
    print(f"{'='*50}")

    if best["total_score"] >= 18:
        print("\n✅ このツイートは品質ゲートを通過します（本番では投稿されます）")
    else:
        print("\n⚠️  スコアが18点未満のため、本番では投稿をスキップします")

if __name__ == "__main__":
    main()
