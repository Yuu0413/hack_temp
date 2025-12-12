import os
import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
DATABASE = 'oshikatsu.db'
SCHEMA_PATH = os.path.join('db', 'schema.sql')

# --- データベース接続ヘルパー ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- データベース初期化関数 ---
def init_db_if_needed():
    """テーブルが存在しない場合、schema.sqlを実行して初期化する"""
    create_needed = False
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

# --- 集計更新ヘルパー関数 (新規追加) ---
def update_summaries(user_id, date_str):
    """
    指定された日付に関連する日次、週次、月次の集計を再計算して更新する
    date_str: 'YYYY-MM-DD' 形式
    """
    conn = get_db_connection()
    
    # 日付オブジェクト変換
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        conn.close()
        return

    # --- 1. 日次集計 (Daily) ---
    purchases = conn.execute("""
        SELECT drink_amount, snack_amount, main_dish_amount, irregular_amount
        FROM purchases
        WHERE user_id = ? AND purchase_date = ?
    """, (user_id, date_str)).fetchall()
    
    drink_total = sum(p['drink_amount'] for p in purchases)
    snack_total = sum(p['snack_amount'] for p in purchases)
    main_total = sum(p['main_dish_amount'] for p in purchases)
    irr_total = sum(p['irregular_amount'] for p in purchases)
    daily_total = drink_total + snack_total + main_total + irr_total
    
    # REPLACE INTO で更新 (UNIQUE制約を利用して上書き)
    conn.execute("""
        INSERT OR REPLACE INTO daily_summaries 
        (user_id, summary_date, drink_total, snack_total, main_dish_total, irregular_total, daily_total, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (user_id, date_str, drink_total, snack_total, main_total, irr_total, daily_total))

    # --- 2. 月次集計 (Monthly) ---
    year = target_date.year
    month = target_date.month
    
    # SQLiteの日付関数で月ごとの集計
    monthly_rows = conn.execute("""
        SELECT drink_amount, snack_amount, main_dish_amount, irregular_amount
        FROM purchases
        WHERE user_id = ? AND CAST(strftime('%Y', purchase_date) AS INTEGER) = ? 
        AND CAST(strftime('%m', purchase_date) AS INTEGER) = ?
    """, (user_id, year, month)).fetchall()
    
    m_drink = sum(p['drink_amount'] for p in monthly_rows)
    m_snack = sum(p['snack_amount'] for p in monthly_rows)
    m_main = sum(p['main_dish_amount'] for p in monthly_rows)
    m_irr = sum(p['irregular_amount'] for p in monthly_rows)
    m_total = m_drink + m_snack + m_main + m_irr
    
    conn.execute("""
        INSERT OR REPLACE INTO monthly_summaries 
        (user_id, year, month, drink_total, snack_total, main_dish_total, irregular_total, monthly_total, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (user_id, year, month, m_drink, m_snack, m_main, m_irr, m_total))

    # --- 3. 週次集計 (Weekly) ---
    # 週の開始日(日曜)を計算
    idx = (target_date.weekday() + 1) % 7
    sunday = target_date - datetime.timedelta(days=idx)
    sunday_str = sunday.strftime('%Y-%m-%d')
    saturday = sunday + datetime.timedelta(days=6)
    saturday_str = saturday.strftime('%Y-%m-%d')
    
    weekly_rows = conn.execute("""
        SELECT drink_amount, snack_amount, main_dish_amount, irregular_amount
        FROM purchases
        WHERE user_id = ? AND purchase_date >= ? AND purchase_date <= ?
    """, (user_id, sunday_str, saturday_str)).fetchall()
    
    w_drink = sum(p['drink_amount'] for p in weekly_rows)
    w_snack = sum(p['snack_amount'] for p in weekly_rows)
    w_main = sum(p['main_dish_amount'] for p in weekly_rows)
    w_irr = sum(p['irregular_amount'] for p in weekly_rows)
    w_total = w_drink + w_snack + w_main + w_irr
    
    conn.execute("""
        INSERT OR REPLACE INTO weekly_summaries 
        (user_id, start_date, end_date, drink_total, snack_total, main_dish_total, irregular_total, weekly_total, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (user_id, sunday_str, saturday_str, w_drink, w_snack, w_main, w_irr, w_total))

    conn.commit()
    conn.close()

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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = session.get('username', 'User')
    
    conn = get_db_connection()
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')

    # 本日のデータ
    daily = conn.execute(
        "SELECT * FROM daily_summaries WHERE user_id = ? AND summary_date = ?",
        (user_id, today_str)
    ).fetchone()

    # 今週のデータ
    idx = (today.weekday() + 1) % 7 
    sunday = today - datetime.timedelta(days=idx)
    sunday_str = sunday.strftime('%Y-%m-%d')
    
    weekly = conn.execute(
        "SELECT * FROM weekly_summaries WHERE user_id = ? AND start_date = ?",
        (user_id, sunday_str)
    ).fetchone()

    # 今月のデータ
    monthly = conn.execute(
        "SELECT * FROM monthly_summaries WHERE user_id = ? AND year = ? AND month = ?",
        (user_id, today.year, today.month)
    ).fetchone()
    
    conn.close()

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
    
    if request.method == 'POST':
        user_id = session['user_id']
        
        # フォームからのデータ取得
        # datainsert.html の input name 属性が date, time_period, category, amount であると想定
        date_val = request.form.get('date') # 2025-12-12 or 2025/12/12
        time_period = request.form.get('time_period') # 朝, 昼, 晩
        category = request.form.get('category') # ドリンク, スナック, フード, その他
        amount_str = request.form.get('amount')
        
        if date_val and amount_str and category:
            # 日付の正規化 (DBは YYYY-MM-DD)
            date_val = date_val.replace('/', '-')
            
            try:
                amount = int(amount_str)
            except ValueError:
                flash('金額は数値で入力してください', 'danger')
                return redirect(url_for('insert'))

            # カテゴリ振り分け
            drink = amount if category == 'ドリンク' else 0
            snack = amount if category == 'スナック' else 0
            main = amount if category == 'フード' else 0
            irr = amount if category == 'その他' else 0
            
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO purchases (user_id, purchase_date, time_period, drink_amount, snack_amount, main_dish_amount, irregular_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, date_val, time_period, drink, snack, main, irr))
            conn.commit()
            conn.close()
            
            # 【重要】集計データの更新
            update_summaries(user_id, date_val)
            
            flash('購入データを記録しました！', 'success')
        else:
            flash('すべての項目を入力してください', 'warning')
            
        return redirect(url_for('insert'))

    return render_template('datainsert.html')

@app.route('/otaku')
def otaku():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    today = datetime.date.today()
    
    # 月次データの取得
    monthly = conn.execute(
        "SELECT monthly_total FROM monthly_summaries WHERE user_id = ? AND year = ? AND month = ?",
        (user_id, today.year, today.month)
    ).fetchone()
    monthly_total = monthly['monthly_total'] if monthly else 0
    
    # バッジ設定の取得
    settings = conn.execute(
        "SELECT badge_price, badges_per_bag FROM badge_settings WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    
    if settings:
        badge_price = settings['badge_price']
        itabag_count = settings['badges_per_bag']
    else:
        badge_price = 440
        itabag_count = 40
        
    conn.close()
    
    # 獲得バッジ数の計算
    if badge_price > 0:
        earned_badges = int(monthly_total // badge_price)
    else:
        earned_badges = 0
    
    data = {
        'monthly_total': monthly_total,
        'badge_price': badge_price,
        'earned_badges': earned_badges,
        'itabag_count': itabag_count
    }
    
    return render_template('otaku.html', data=data)

if __name__ == '__main__':
    init_db_if_needed()
    app.run(debug=True, port=8100)