#~/hackathon/hack_temp % python -m db.test_db　ここで実行する



from db import init_db
from db import user as User
from db import badge_setting as Setting
from db import purchase as Purchase
from db import summary as Summary
import datetime

def test_db_operations():
    # 1. DB初期化 (初回のみ実行される)
    print("--- DB初期化 ---")
    try:
        init_db()
    except Exception as e:
        print(e)

    # 2. ユーザー登録
    print("\n--- ユーザー登録 ---")
    username = "otaku_user"
    user_id = User.create_user(username, "hashed_password_123")
    
    if user_id:
        print(f"User created: ID {user_id}")
        Setting.create_default_settings(user_id)
    else:
        # 重複時などは既存IDを取得
        existing_user = User.get_user_by_username(username)
        user_id = existing_user['user_id']
        print(f"User already exists: ID {user_id}")

    # 3. 購入データの入力
    print("\n--- 購入入力 ---")
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    # 朝ごはん (飲み物とパン)
    Purchase.add_purchase(
        user_id, today, '朝', 
        {'drink': 150, 'snack': 200}, 
        memo="コンビニのパン"
    )
    
    # 昼ごはん (ランチ)
    Purchase.add_purchase(
        user_id, today, '昼', 
        {'main': 1200}, 
        memo="推し活カフェ"
    )

    # 4. 集計処理を実行 (ここが重要：購入後に必ず呼ぶ)
    print("\n--- 集計処理 ---")
    Summary.update_daily_summary(user_id, today)

    # 5. 結果の表示
    print("\n--- 結果確認 ---")
    summary = Summary.get_daily_summary(user_id, today)
    settings = Setting.get_settings(user_id)
    
    if summary:
        print(f"日付: {summary['summary_date']}")
        print(f"総支出: {summary['daily_total']}円")
        print(f"飲み物: {summary['drink_total']}円")
        print(f"メイン: {summary['main_dish_total']}円")
        print(f"-"*20)
        print(f"缶バッジ単価: {settings['badge_price']}円")
        print(f"我慢できた缶バッジ数: {summary['badge_equivalent']:.2f} 個")
        print(f"痛バッグ換算: {summary['itabag_equivalent']:.4f} 個分")
    else:
        print("集計データがありません")

if __name__ == "__main__":
    test_db_operations()