from . import get_db_connection

def create_default_settings(user_id):
    """ユーザー作成時にデフォルト設定を保存する"""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO badge_settings 
        (user_id, badge_price, itabag_badge_count, itabag_total_price)
        VALUES (?, 600, 35, 19250)
        """,
        (user_id,)
    )
    conn.commit()
    conn.close()

def get_settings(user_id):
    """ユーザーの設定を取得する"""
    conn = get_db_connection()
    settings = conn.execute(
        "SELECT * FROM badge_settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return settings

def update_settings(user_id, badge_price, itabag_badge_count):
    """設定を更新する（痛バ総額は自動計算）"""
    itabag_total_price = badge_price * itabag_badge_count
    
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE badge_settings
        SET badge_price = ?, itabag_badge_count = ?, itabag_total_price = ?
        WHERE user_id = ?
        """,
        (badge_price, itabag_badge_count, itabag_total_price, user_id)
    )
    conn.commit()
    conn.close()