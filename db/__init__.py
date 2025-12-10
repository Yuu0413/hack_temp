import sqlite3
import os

# このファイルのディレクトリパスを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')

def get_db_connection():
    """データベース接続を取得し、Rowファクトリを設定して返す"""
    conn = sqlite3.connect(DB_PATH)
    # カラム名で値を取得できるようにする (row['user_id'] のように)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """schema.sql を読み込んでテーブルを作成する"""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.close()
    print(f"Database initialized at: {DB_PATH}")