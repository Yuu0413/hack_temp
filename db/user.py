from . import get_db_connection
import sqlite3

def create_user(username, password_hash):
    """新規ユーザーを作成する"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        # ユーザー名重複などの場合
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """ユーザー名からユーザー情報を取得（ログイン用）"""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """IDからユーザー情報を取得"""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user