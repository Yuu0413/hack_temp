#~/hackathon/hack_temp % python -m db.test_db_multiple_buy　ここで実行する

import random
import datetime
import calendar  # 月末の日付計算用に追加
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

    # 0. 既存DBのクリーンアップ
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'app.db')
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("-> 古いDBファイルを削除しました (Schema更新のため)")
        except PermissionError:
            print("-> DBファイルが開かれているため削除できませんでした。既存DBを使用します。")

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
        daily_transactions = random.randint(1, 3)
        purchase_desc = []

        for _ in range(daily_transactions):
            amounts = {}
            
            # DBの制約に従い、'朝', '昼', '晩' のいずれかを選択
            p_type = random.choice(['朝', '昼', '晩'])
            
            # カテゴリ選択
            cat_choice = random.choice(['drink', 'snack', 'main'])
            amount = get_random_amount(100, 600)
            amounts[cat_choice] = amount
            
            # 保存
            Purchase.add_purchase(
                user_id, date_str, p_type, amounts, 
                memo=f"自動テスト購入: {cat_choice}"
            )
            
            # 表示用文字列作成
            cat_name = {'drink': '飲', 'snack': '菓', 'main': '飯'}.get(cat_choice)
            purchase_desc.append(f"{p_type}-{cat_name}:{amount}")

        # --- 集計処理の実行 ---
        Summary.update_daily_summary(user_id, date_str)
        Summary.update_weekly_summary(user_id, current_date)
        Summary.update_monthly_summary(user_id, current_date)

        # --- 日次結果表示 ---
        # A. 基本サマリー取得
        summary = Summary.get_daily_summary(user_id, date_str)
        
        # B. 時間帯別詳細の取得
        time_details = Summary.get_daily_details_by_time_period(user_id, date_str)
        
        desc_str = ", ".join(purchase_desc)
        if len(desc_str) > 25:
            desc_str = desc_str[:22] + "..."
            
        total = summary['daily_total']
        badge_eq = summary['badge_equivalent']
        star = "★" if badge_eq >= 1.0 else "  "

        print(f"{date_str} | {desc_str:<25} | {total:>5}円 | {badge_eq:.2f} 個 {star}")
        
        # 内訳表示
        print(f"   └ [内訳] 朝:{time_details.get('朝', 0)} 昼:{time_details.get('昼', 0)} "
              f"晩:{time_details.get('晩', 0)} 合計:{time_details.get('total', 0)}")

        current_date += delta

    print("-" * 75)
    print("\n")

    # 5. 週次レポートの表示
    print(">>> 週次レポート (Weekly Summary: Sun ~ Sat)")
    print(f"{'期間 (開始 ~ 終了)':<25} | {'週合計':<8} | {'バッジ換算'} | {'痛バ換算'}")
    print("-" * 75)
    
    weekly_rows = Summary.get_weekly_summaries(user_id)
    if weekly_rows:
        for row in weekly_rows:
            period = f"{row['start_date']} ~ {row['end_date']}"
            total = row['weekly_total']
            badge = row['badge_equivalent']
            itabag = row['itabag_equivalent']
            
            print(f"{period:<25} | {total:>5}円 | {badge:.2f} 個   | {itabag:.4f} 個分")
            
            # --- 追加: 週次の時間帯別内訳 ---
            # summary.py に新しく追加した関数を使用
            w_details = Summary.get_period_details_by_date_range(
                user_id, row['start_date'], row['end_date']
            )
            print(f"   └ [内訳] 朝:{w_details.get('朝', 0)} 昼:{w_details.get('昼', 0)} "
                  f"晩:{w_details.get('晩', 0)} 合計:{w_details.get('total', 0)}")

    else:
        print("データなし")
    print("-" * 75)
    print("\n")

    # 6. 月次レポートの表示
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
            
            # --- 追加: 月次の時間帯別内訳 ---
            # 月初と月末の日付を計算
            last_day = calendar.monthrange(year, month)[1] # 月末日を取得
            start_str = f"{year}-{month:02d}-01"
            end_str = f"{year}-{month:02d}-{last_day}"
            
            m_details = Summary.get_period_details_by_date_range(
                user_id, start_str, end_str
            )
            print(f"   └ [内訳] 朝:{m_details.get('朝', 0)} 昼:{m_details.get('昼', 0)} "
                  f"晩:{m_details.get('晩', 0)} 合計:{m_details.get('total', 0)}")

    else:
        print("データなし")
    print("-" * 60)

    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_multiple_buy()