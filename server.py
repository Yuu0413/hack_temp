import os
import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

# 既存のDBモジュール (構成に合わせて適宜調整してください)
from db import user as User
from db import badge_setting as Setting
from db import summary as Summary
from db import purchase as Purchase
# from db import init_db # 今回はserver.py内で初期化を行うためコメントアウト

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
DATABASE = 'oshikatsu.db'
SCHEMA_PATH = os.path.join('db', 'schema.sql') # schema.sqlのパス

# --- データベース接続ヘルパー ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- データベース初期化関数 (エラー解決用) ---
def init_db_if_needed():
    """テーブルが存在しない場合、schema.sqlを実行して初期化する"""
    if not os.path.exists(DATABASE):
        create_needed = True
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        # usersテーブルがあるか確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        result = cursor.fetchone()
        conn.close()
        create_needed = (result is None)

    if create_needed:
        print("Initializing database...")
        if os.path.exists(SCHEMA_PATH):
            conn = get_db_connection()
            with open(SCHEMA_PATH, mode='r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.close()
            print("Database initialized.")
        else:
            print(f"Error: {SCHEMA_PATH} not found. Cannot initialize database.")

# --- フォームクラス ---
class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmed_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

    def validate_username(self, field):
        # Userモジュールがない場合の安全策として直接チェックも実装
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (field.data,)).fetchone()
        conn.close()
        if user:
            raise ValidationError('This username is already taken.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# --- ルート定義 ---

@app.route('/')
def index():
    # ログインしていない場合はログイン画面へ
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = session.get('username', 'User')
    
    conn = get_db_connection()
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')

    # 1. 本日のデータ取得
    daily = conn.execute(
        "SELECT * FROM daily_summaries WHERE user_id = ? AND summary_date = ?",
        (user_id, today_str)
    ).fetchone()

    # 2. 今週のデータ取得 (日曜始まりと仮定)
    # 今日の曜日を取得 (月=0, ... 日=6)
    # 直前の日曜日を計算
    idx = (today.weekday() + 1) % 7 
    sunday = today - datetime.timedelta(days=idx)
    sunday_str = sunday.strftime('%Y-%m-%d')
    
    weekly = conn.execute(
        "SELECT * FROM weekly_summaries WHERE user_id = ? AND start_date = ?",
        (user_id, sunday_str)
    ).fetchone()

    # 3. 今月のデータ取得
    monthly = conn.execute(
        "SELECT * FROM monthly_summaries WHERE user_id = ? AND year = ? AND month = ?",
        (user_id, today.year, today.month)
    ).fetchone()
    
    conn.close()

    # テンプレートに渡すデータを作成（データがない場合は0を入れる）
    data = {
        'daily_total': daily['daily_total'] if daily else 0,
        'drink': daily['drink_total'] if daily else 0,
        'snack': daily['snack_total'] if daily else 0,
        'main': daily['main_dish_total'] if daily else 0,
        
        'weekly_total': weekly['weekly_total'] if weekly else 0,
        'monthly_total': monthly['monthly_total'] if monthly else 0
    }

    return render_template('index.html', username=username, data=data)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                         (form.username.data, hashed_password))
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {e}', 'danger')
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (form.username.data,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], form.password.data):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 既存のinsert処理（省略せず必要な場合は前回のコードを参照して統合してください）
    # ここではルーティングのみ示します
    if request.method == 'POST':
        # ... (前回のコードのDB保存処理) ...
        # 今回のエラー解決が主眼のため、詳細は省略しますが
        # Purchase.add_purchase 等を呼び出す処理が入ります
        pass 

    return render_template('datainsert.html')

@app.route('/otaku')
def otaku():
    # 痛バ画面（HTMLにあったリンク先）
    return render_template('otaku.html')

if __name__ == '__main__':
    # 起動時にDBチェックを実行
    init_db_if_needed()
    app.run(debug=True, port=8092)