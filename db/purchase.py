from . import get_db_connection
from datetime import datetime

def add_purchase(user_id, date_str, time_period, amounts, memo=""):
    """
    購入データを追加する
    amounts: {'drink': 100, 'snack': 200, ...} のような辞書を想定
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO purchases 
        (user_id, purchase_date, time_period, drink_amount, snack_amount, 
         main_dish_amount, irregular_amount, memo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, 
            date_str, 
            time_period, 
            amounts.get('drink', 0),
            amounts.get('snack', 0),
            amounts.get('main', 0),
            amounts.get('irregular', 0),
            memo
        )
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid

def get_purchases_by_date(user_id, date_str):
    """指定した日付の購入履歴を取得"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM purchases WHERE user_id = ? AND purchase_date = ?",
        (user_id, date_str)
    ).fetchall()
    conn.close()
    return rows