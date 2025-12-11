from . import get_db_connection
from .badge_setting import get_settings
import datetime

# --- 共通ヘルパー関数 ---
def _calculate_amounts_and_upsert(conn, user_id, time_filter_sql, filter_params, target_table, conflict_target, extra_cols_dict):
    """
    集計計算とUpsertを行う共通関数
    time_filter_sql: WHERE句の日付条件 (例: "AND purchase_date = ?")
    filter_params: SQLパラメータのタプル
    target_table: 保存先のテーブル名
    conflict_target: UNIQUE制約のカラム名 (例: "user_id, summary_date")
    extra_cols_dict: 追加で保存するカラムと値 (例: {'start_date': '...', 'end_date': '...'})
    """
    
    # 1. purchasesテーブルから集計
    sql = f"""
        SELECT 
            SUM(drink_amount) as drink,
            SUM(snack_amount) as snack,
            SUM(main_dish_amount) as main,
            SUM(irregular_amount) as irregular
        FROM purchases
        WHERE user_id = ? {time_filter_sql}
    """
    agg = conn.execute(sql, (user_id,) + filter_params).fetchone()

    drink = agg['drink'] or 0
    snack = agg['snack'] or 0
    main = agg['main'] or 0
    irregular = agg['irregular'] or 0
    total_amount = drink + snack + main + irregular

    # 2. 設定を取得して換算
    settings = get_settings(user_id) 
    badge_price = settings['badge_price']
    itabag_total_price = settings['itabag_total_price']

    badge_eq = total_amount / badge_price if badge_price else 0
    itabag_eq = total_amount / itabag_total_price if itabag_total_price else 0

    # 3. 保存 (Upsert)
    # カラムの準備
    cols = ['user_id', 'drink_total', 'snack_total', 'main_dish_total', 'irregular_total', 
            target_table.replace('_summaries', '_total'), 'badge_equivalent', 'itabag_equivalent']
    vals = [user_id, drink, snack, main, irregular, total_amount, badge_eq, itabag_eq]

    # 追加カラム (日付やstart_date, end_dateなど)
    for col_name, col_val in extra_cols_dict.items():
        cols.append(col_name)
        vals.append(col_val)

    col_str = ", ".join(cols)
    val_ph = ", ".join(["?"] * len(vals))
    
    # UPDATE句の生成
    # user_id や extra_cols_dict に含まれるキー(UNIQUEキーになるもの)は更新対象外
    update_parts = [f"{c}=excluded.{c}" for c in cols if c != 'user_id' and c not in extra_cols_dict]
    update_parts.append("updated_at=DATETIME('now', 'localtime')")
    update_str = ", ".join(update_parts)

    upsert_sql = f"""
        INSERT INTO {target_table} ({col_str})
        VALUES ({val_ph})
        ON CONFLICT({conflict_target}) DO UPDATE SET
        {update_str}
    """
    
    conn.execute(upsert_sql, vals)

# --- ヘルパー: 日付計算 ---
def _get_sunday_to_saturday_range(date_obj):
    """
    指定された日付が含まれる週の、日曜日(開始)と土曜日(終了)を返す
    Pythonのweekday(): 月=0 ... 日=6
    欲しい仕様: 日=0 ... 土=6 として計算する
    """
    # Pythonのweekday() (月0-日6) を、(日0-土6) に変換する
    # (weekday + 1) % 7 で、日曜日が0、土曜日が6になる
    day_idx = (date_obj.weekday() + 1) % 7
    
    # 開始日（日曜日） = 指定日 - day_idx
    start_date = date_obj - datetime.timedelta(days=day_idx)
    # 終了日（土曜日） = 開始日 + 6日
    end_date = start_date + datetime.timedelta(days=6)
    
    return start_date, end_date

# --- 日次集計 ---
def update_daily_summary(user_id, date_str):
    conn = get_db_connection()
    try:
        _calculate_amounts_and_upsert(
            conn, user_id,
            time_filter_sql="AND purchase_date = ?",
            filter_params=(date_str,),
            target_table="daily_summaries",
            conflict_target="user_id, summary_date",
            extra_cols_dict={'summary_date': date_str}
        )
        conn.commit()
    finally:
        conn.close()

def get_daily_summary(user_id, date_str):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM daily_summaries WHERE user_id = ? AND summary_date = ?",
        (user_id, date_str)
    ).fetchone()
    conn.close()
    return row

# --- 週次集計 (修正箇所) ---
def update_weekly_summary(user_id, date_obj):
    """指定された日付が含まれる週(日〜土)の集計を更新"""
    
    start_date, end_date = _get_sunday_to_saturday_range(date_obj)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    conn = get_db_connection()
    try:
        # 期間指定で集計 (purchase_date BETWEEN start AND end)
        _calculate_amounts_and_upsert(
            conn, user_id,
            time_filter_sql="AND purchase_date >= ? AND purchase_date <= ?",
            filter_params=(start_str, end_str),
            target_table="weekly_summaries",
            conflict_target="user_id, start_date",
            extra_cols_dict={'start_date': start_str, 'end_date': end_str}
        )
        conn.commit()
    finally:
        conn.close()

def get_weekly_summaries(user_id):
    """全週のデータを取得 (開始日順)"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM weekly_summaries WHERE user_id = ? ORDER BY start_date",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows

# --- 月次集計 ---
def update_monthly_summary(user_id, date_obj):
    """指定された日付が含まれる月の集計を更新"""
    year = date_obj.year
    month = date_obj.month
    
    month_str = f"{month:02d}"
    year_str = str(year)

    conn = get_db_connection()
    try:
        _calculate_amounts_and_upsert(
            conn, user_id,
            time_filter_sql="AND strftime('%Y', purchase_date) = ? AND strftime('%m', purchase_date) = ?",
            filter_params=(year_str, month_str),
            target_table="monthly_summaries",
            conflict_target="user_id, year, month",
            extra_cols_dict={'year': year, 'month': month}
        )
        conn.commit()
    finally:
        conn.close()

def get_monthly_summaries(user_id):
    """全月のデータを取得"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM monthly_summaries WHERE user_id = ? ORDER BY year, month",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows

def get_daily_details_by_time_period(user_id, date_str):
    """
    指定した日付の購入データを時間帯(time_period)ごとに集計して返す。
    """
    conn = get_db_connection()
    try:
        # 修正ポイント:
        # 1. 'amount' カラムはないので、各カテゴリの金額を合計して集計します。
        # 2. 日付カラム名は 'purchase_date' です。
        query = """
            SELECT 
                time_period, 
                SUM(drink_amount + snack_amount + main_dish_amount + irregular_amount) as subtotal
            FROM purchases
            WHERE user_id = ? AND purchase_date = ?
            GROUP BY time_period
        """
        rows = conn.execute(query, (user_id, date_str)).fetchall()
        
        # 結果を辞書にまとめる
        result = {
            '朝': 0,
            '昼': 0,
            '晩': 0,
            'total': 0
        }
        
        for row in rows:
            time_period = row['time_period']
            amount = row['subtotal']
            
            # データベースに保存された time_period ('朝', '昼', '晩') をキーにする
            if time_period:
                result[time_period] = amount
            
            # 総合計も計算
            if amount:
                result['total'] += amount
                
        return result
        
    finally:
        conn.close()

def get_period_details_by_date_range(user_id, start_date_str, end_date_str):
    """
    指定した期間（開始日〜終了日）の購入データを時間帯(time_period)ごとに集計して返す。
    """
    conn = get_db_connection()
    try:
        # 期間指定(>= start AND <= end)で集計
        query = """
            SELECT 
                time_period, 
                SUM(drink_amount + snack_amount + main_dish_amount + irregular_amount) as subtotal
            FROM purchases
            WHERE user_id = ? AND purchase_date >= ? AND purchase_date <= ?
            GROUP BY time_period
        """
        rows = conn.execute(query, (user_id, start_date_str, end_date_str)).fetchall()
        
        result = {
            '朝': 0, '昼': 0, '晩': 0, 'total': 0
        }
        
        for row in rows:
            time_period = row['time_period']
            amount = row['subtotal']
            
            if time_period in result:
                result[time_period] = amount
            
            if amount:
                result['total'] += amount
                
        return result
        
    finally:
        conn.close()