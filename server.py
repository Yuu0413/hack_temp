import os
import datetime
import calendar
from flask import Flask, render_template, request, redirect, url_for, session, flash

# dbパッケージから必要なモジュールをインポート
from db import init_db, DB_PATH
from db import user as User
from db import purchase as Purchase
from db import summary as Summary
from db import badge_setting as Setting

app = Flask(__name__)
app.secret_key = 'super_secret_otaku_key'  # セッション情報の暗号化キー

# --- ヘルパー関数 ---

def check_and_init_db():
    """起動時にDBファイルを確認し、なければ初期化する"""
    if not os.path.exists(DB_PATH):
        print(f"データベースが見つかりません: {DB_PATH}")
        print("データベースを初期化します...")
        try:
            init_db()
            print("初期化完了。")
        except Exception as e:
            print(f"初期化エラー: {e}")
    else:
        print(f"データベースを確認しました: {DB_PATH}")

def get_target_date():
    """リクエストパラメータから対象日付を取得。なければ今日を返す"""
    date_str = request.args.get('date')
    if date_str:
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return datetime.date.today()

def normalize_time_period(value):
    """入力された時間帯をDB仕様('朝', '昼', '晩')に変換する"""
    mapping = {
        'morning': '朝',
        'noon': '昼',
        'night': '晩',
        '朝': '朝',
        '昼': '昼',
        '晩': '晩'
    }
    # マッピングになければデフォルトで'昼'、あるいはNoneを返す
    return mapping.get(value, '昼')

# --- ルーティング ---

@app.route('/')
def index():
    """メイン画面：指定日の集計と入力フォームを表示"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # 日付指定の取得 (デフォルトは今日)
    target_date = get_target_date()
    target_date_str = target_date.strftime('%Y-%m-%d')

    # 1. 指定日の集計データを取得
    daily_summary = Summary.get_daily_summary(user_id, target_date_str)
    
    # 2. 時間帯別の詳細内訳を取得 (新規機能)
    daily_details = Summary.get_daily_details_by_time_period(user_id, target_date_str)
    
    # 3. 設定（レート）を取得
    settings = Setting.get_settings(user_id)
    
    # データがない場合のデフォルト値
    if not daily_summary:
        daily_summary = {
            'daily_total': 0,
            'badge_equivalent': 0.0,
            'itabag_equivalent': 0.0,
            'drink_total': 0, 'snack_total': 0, 'main_dish_total': 0, 'irregular_total': 0
        }

    return render_template('index.html', 
                           summary=daily_summary, 
                           details=daily_details,
                           settings=settings,
                           target_date=target_date_str,
                           username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン画面"""
    if request.method == 'POST':
        username = request.form['username']
        
        # 簡易ログイン：ユーザーがいればID取得、いなければ新規作成
        user = User.get_user_by_username(username)
        if user:
            user_id = user['user_id']
        else:
            user_id = User.create_user(username, "default_password")
        
        session['user_id'] = user_id
        session['username'] = username
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add_purchase():
    """購入データの登録処理"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # フォームから日付を取得 (指定がなければ今日)
    date_str = request.form.get('date')
    if not date_str:
        date_str = datetime.date.today().strftime('%Y-%m-%d')
    
    try:
        # 日付オブジェクト変換 (集計更新用)
        target_date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return "無効な日付形式です", 400

    # 金額の取得
    try:
        amounts = {
            'drink': int(request.form.get('drink', 0) or 0),
            'snack': int(request.form.get('snack', 0) or 0),
            'main': int(request.form.get('main', 0) or 0),
            'irregular': int(request.form.get('irregular', 0) or 0)
        }
    except ValueError:
        return "金額には数値を入力してください", 400

    # 時間帯の取得と変換
    raw_time = request.form.get('time_period', 'noon')
    time_period = normalize_time_period(raw_time)
    
    memo = request.form.get('memo', '')

    # 合計が0円でなければ保存
    if sum(amounts.values()) > 0:
        # 1. 購入データの保存
        Purchase.add_purchase(user_id, date_str, time_period, amounts, memo)

        # 2. 集計データの更新
        Summary.update_daily_summary(user_id, date_str)
        Summary.update_weekly_summary(user_id, target_date_obj)
        Summary.update_monthly_summary(user_id, target_date_obj)

    # 元の日付のページに戻る
    return redirect(url_for('index', date=date_str))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """設定画面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']

    if request.method == 'POST':
        try:
            badge_price = int(request.form['badge_price'])
            itabag_count = int(request.form['itabag_count'])
            Setting.update_settings(user_id, badge_price, itabag_count)
            
            # 設定変更の影響範囲として、とりあえず当日の再集計を行う
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            Summary.update_daily_summary(user_id, today_str)
            
            return redirect(url_for('index'))
        except ValueError:
            return "数値で入力してください", 400

    current_settings = Setting.get_settings(user_id)
    return render_template('settings.html', settings=current_settings)

@app.route('/report')
def report():
    """レポート画面：週次・月次の履歴と詳細を表示"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # --- 週次レポート作成 ---
    weekly_data = []
    weekly_rows = Summary.get_weekly_summaries(user_id)
    
    if weekly_rows:
        for row in weekly_rows:
            # 各週の時間帯別内訳を取得
            details = Summary.get_period_details_by_date_range(
                user_id, row['start_date'], row['end_date']
            )
            # Rowオブジェクトは書き換えできない場合があるため辞書化して結合
            item = dict(row)
            item['details'] = details
            weekly_data.append(item)

    # --- 月次レポート作成 ---
    monthly_data = []
    monthly_rows = Summary.get_monthly_summaries(user_id)
    
    if monthly_rows:
        for row in monthly_rows:
            # 月初と月末を計算して期間を指定
            year, month = row['year'], row['month']
            last_day = calendar.monthrange(year, month)[1]
            start_str = f"{year}-{month:02d}-01"
            end_str = f"{year}-{month:02d}-{last_day}"
            
            # 各月の時間帯別内訳を取得
            details = Summary.get_period_details_by_date_range(
                user_id, start_str, end_str
            )
            
            item = dict(row)
            item['details'] = details
            monthly_data.append(item)

    return render_template('report.html', 
                           weekly_data=weekly_data, 
                           monthly_data=monthly_data)

if __name__ == '__main__':
    # サーバー起動前にDBチェック
    check_and_init_db()
    
    # デバッグモードで起動
    # host='0.0.0.0' にすると外部からもアクセス可能になります
    app.run(debug=True, port=8081)