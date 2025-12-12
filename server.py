import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# 既存のDBモジュールをインポート
from db import user as User
from db import badge_setting as Setting
from db import summary as Summary
from db import purchase as Purchase
from db import init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  # セキュリティのため変更推奨

# --- フォームクラス定義 (Templatesの要求に対応) ---
class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmed_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

    def validate_username(self, field):
        if User.get_user_by_username(field.data):
            raise ValidationError('This username is already taken.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# --- ダッシュボード用テンプレート (index.htmlなしで動作させるため) ---
DASHBOARD_TEMPLATE = """
{% extends "base.html" %}

{% block title %}Dashboard | Oshikatsu Savings{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2 class="mb-4">ようこそ、{{ username }} さん</h2>
        
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                本日の推し活・節約状況 ({{ today }})
            </div>
            <div class="card-body">
                {% if summary %}
                    <div class="row text-center">
                        <div class="col-md-4">
                            <h4>支出合計</h4>
                            <p class="display-6 text-danger">{{ summary['daily_total'] }}円</p>
                        </div>
                        <div class="col-md-4">
                            <h4>我慢できた缶バッジ</h4>
                            <p class="display-6 text-success">{{ "%.2f"|format(summary['badge_equivalent']) }}個</p>
                        </div>
                        <div class="col-md-4">
                            <h4>痛バ完成度</h4>
                            <p class="display-6 text-info">{{ "%.4f"|format(summary['itabag_equivalent']) }}個分</p>
                        </div>
                    </div>
                    <hr>
                    <p>内訳: 飲 {{ summary['drink_total'] }}円 / 菓 {{ summary['snack_total'] }}円 / 飯 {{ summary['main_dish_total'] }}円</p>
                {% else %}
                    <p class="text-muted">本日のデータはまだありません。</p>
                {% endif %}
            </div>
        </div>

        <div class="d-grid gap-2 d-md-block">
            <a href="{{ url_for('insert') }}" class="btn btn-success btn-lg">購入データを入力する</a>
            <a href="{{ url_for('settings') }}" class="btn btn-outline-secondary">設定変更</a>
        </div>
    </div>
</div>
{% endblock %}
"""

# --- ルーティング ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # 本日のサマリー取得
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    summary = Summary.get_daily_summary(user_id, today_str)

    # index.html ファイルを使わず、文字列からレンダリング
    return render_template_string(
        DASHBOARD_TEMPLATE, 
        username=user['username'], 
        today=today_str,
        summary=summary
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        # パスワードをハッシュ化して保存
        hashed_pw = generate_password_hash(form.password.data)
        user_id = User.create_user(form.username.data, hashed_pw)
        
        if user_id:
            # デフォルト設定を作成
            Setting.create_default_settings(user_id)
            flash('Account created successfully. Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error creating account.', 'danger')
            
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_user_by_username(form.username.data)
        # ハッシュ化されたパスワードを照合
        if user and check_password_hash(user['password_hash'], form.password.data):
            session['user_id'] = user['user_id']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # logout.htmlもフォームを使っているので対応（POSTの場合）
    # シンプルにGETでログアウトさせる場合も考慮
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# 仮のルート（リンク切れ防止）
@app.route('/settings')
def settings():
    return "設定ページ（未実装） <a href='/'>戻る</a>"

@app.route('/report')
def report():
    return "レポートページ（未実装） <a href='/'>戻る</a>"

@app.route('/insert')
def insert():
    return render_template('datainsert.html')

if __name__ == '__main__':
    # DB初期化（存在しない場合）
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'db', 'app.db')):
        init_db()
        
    app.run(debug=True, port=8080)