#~/hackathon/hack_temp % python -m db.test_db_multiple_buy　ここで実行する




import random
import datetime
import os
from db import init_db
from db import user as User
from db import badge_setting as Setting
from db import purchase as Purchase
from db import summary as Summary

def get_random_amount(min_val=100, max_val=500):
    """指定範囲のランダムな金額（10円単位）を返す"""
    return random.randrange(min_val, max_val, 10)

def test_multiple_buy():
    print("=== 複数日程・ランダム購入テスト (Date Range版) ===")

    # 0. 既存DBのクリーンアップ (スキーマ変更対応のため)
    # ※本番では絶対やってはいけませんが、開発中のテストなのでDBをリセットします
    db_path = os.path.join(os.path.dirname(__file__), 'db', 'app.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("-> 古いDBファイルを削除しました (Schema更新のため)")

    # 1. DB初期化
    try:
        init_db()
    except Exception as e:
        print(f"DB初期化エラー: {e}")
        return

    # 2. ユーザー取得
    username = "otaku_user"
    user_id = User.create_user(username, "hashed_password_123")
    Setting.create_default_settings(user_id)
    print(f"新規ユーザーを作成: {username} (ID: {user_id})")

    # 設定情報の取得
    settings = Setting.get_settings(user_id)
    badge_price = settings['badge_price']
    print(f"設定: 缶バッジ単価 = {badge_price}円\n")

    # 3. 日付範囲の設定 (2025/12/28 ~ 2026/01/05)
    # 年跨ぎの週を確認できるよう、年末年始の日程にします
    start_date = datetime.date(2025, 12, 28) # 日曜日
    end_date = datetime.date(2026, 1, 5)     # 翌年月曜日
    delta = datetime.timedelta(days=1)

    current_date = start_date
    
    print(">>> 日次レポート (Daily)")
    print(f"{'日付':<12} | {'購入内容':<25} | {'日次合計':<8} | {'バッジ換算'}")
    print("-" * 75)

    # 4. ループ処理
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # --- ランダムな購入データの生成 ---
        daily_transactions = random.randint(1, 2)
        purchase_desc = []

        for _ in range(daily_transactions):
            amounts = {}
            p_type = random.choice(['朝', '昼', '晩'])
            cat_choice = random.choice(['drink', 'snack', 'main'])
            amount = get_random_amount(100, 600)
            amounts[cat_choice] = amount
            
            # 保存
            Purchase.add_purchase(
                user_id, date_str, p_type, amounts, 
                memo=f"自動テスト購入: {cat_choice}"
            )
            
            cat_name = {'drink': '飲', 'snack': '菓', 'main': '飯'}.get(cat_choice)
            purchase_desc.append(f"{cat_name}:{amount}")

        # --- 集計処理の実行 ---
        # 1. 日次集計更新
        Summary.update_daily_summary(user_id, date_str)
        
        # 2. 週次集計更新 (ロジック変更: 日〜土の範囲で集計)
        Summary.update_weekly_summary(user_id, current_date)
        
        # 3. 月次集計更新
        Summary.update_monthly_summary(user_id, current_date)

        # --- 日次結果表示 ---
        summary = Summary.get_daily_summary(user_id, date_str)
        
        desc_str = ", ".join(purchase_desc)
        total = summary['daily_total']
        badge_eq = summary['badge_equivalent']
        star = "★" if badge_eq >= 1.0 else "  "

        print(f"{date_str} | {desc_str:<25} | {total:>5}円 | {badge_eq:.2f} 個 {star}")

        current_date += delta

    print("-" * 75)
    print("\n")

    # 5. 週次レポートの表示 (DBから取得)
    # ここが今回の変更のメインです
    print(">>> 週次レポート (Weekly Summary: Sun ~ Sat)")
    print(f"{'期間 (開始 ~ 終了)':<25} | {'週合計':<8} | {'バッジ換算'} | {'痛バ換算'}")
    print("-" * 75)
    
    weekly_rows = Summary.get_weekly_summaries(user_id)
    if weekly_rows:
        for row in weekly_rows:
            # start_date, end_date カラムを使用
            period = f"{row['start_date']} ~ {row['end_date']}"
            total = row['weekly_total']
            badge = row['badge_equivalent']
            itabag = row['itabag_equivalent']
            print(f"{period:<25} | {total:>5}円 | {badge:.2f} 個   | {itabag:.4f} 個分")
    else:
        print("データなし")
    print("-" * 75)
    print("\n")

    # 6. 月次レポートの表示 (DBから取得)
    print(">>> 月次レポート (Monthly Summary)")
    print(f"{'年':<6} | {'月':<6} | {'月合計':<8} | {'バッジ換算'} | {'痛バ換算'}")
    print("-" * 60)
    
    monthly_rows = Summary.get_monthly_summaries(user_id)
    if monthly_rows:
        for row in monthly_rows:
            year = row['year']
            month = row['month']
            total = row['monthly_total']
            badge = row['badge_equivalent']
            itabag = row['itabag_equivalent']
            print(f"{year:<6} | {month:<6} | {total:>5}円 | {badge:.2f} 個   | {itabag:.4f} 個分")
    else:
        print("データなし")
    print("-" * 60)

    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_multiple_buy()