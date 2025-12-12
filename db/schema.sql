-- 外部キー制約を有効化（SQLiteではデフォルトでOFFの場合があるため）
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------
-- 1. usersテーブル
-- -----------------------------------------------------
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (DATETIME('now', 'localtime'))
);

-- -----------------------------------------------------
-- 2. badge_settingsテーブル
-- -----------------------------------------------------
DROP TABLE IF EXISTS badge_settings;
CREATE TABLE badge_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    badge_price INTEGER DEFAULT 600,
    badges_per_bag INTEGER DEFAULT 35, -- 修正: server.pyに合わせてカラム名を変更
    itabag_total_price INTEGER DEFAULT 19250,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- 3. purchasesテーブル
-- -----------------------------------------------------
DROP TABLE IF EXISTS purchases;
CREATE TABLE purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    purchase_date TEXT NOT NULL, -- YYYY-MM-DD形式
    time_period TEXT NOT NULL CHECK (time_period IN ('朝', '昼', '晩')),
    drink_amount INTEGER DEFAULT 0,
    snack_amount INTEGER DEFAULT 0,
    main_dish_amount INTEGER DEFAULT 0,
    irregular_amount INTEGER DEFAULT 0,
    memo TEXT,
    created_at TEXT DEFAULT (DATETIME('now', 'localtime')),
    updated_at TEXT DEFAULT (DATETIME('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- 4. daily_summariesテーブル
-- -----------------------------------------------------
DROP TABLE IF EXISTS daily_summaries;
CREATE TABLE daily_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    summary_date TEXT NOT NULL, -- YYYY-MM-DD形式
    drink_total INTEGER DEFAULT 0,
    snack_total INTEGER DEFAULT 0,
    main_dish_total INTEGER DEFAULT 0,
    irregular_total INTEGER DEFAULT 0,
    daily_total INTEGER DEFAULT 0,
    badge_equivalent REAL DEFAULT 0,
    itabag_equivalent REAL DEFAULT 0,
    updated_at TEXT DEFAULT (DATETIME('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, summary_date) -- ユーザーと日付の組み合わせを一意に
);

-- -----------------------------------------------------
-- 5. weekly_summariesテーブル
-- -----------------------------------------------------

DROP TABLE IF EXISTS weekly_summaries;
CREATE TABLE weekly_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    start_date TEXT NOT NULL, -- 週の開始日 (日曜日)
    end_date TEXT NOT NULL,   -- 週の終了日 (土曜日)
    drink_total INTEGER DEFAULT 0,
    snack_total INTEGER DEFAULT 0,
    main_dish_total INTEGER DEFAULT 0,
    irregular_total INTEGER DEFAULT 0,
    weekly_total INTEGER DEFAULT 0,
    badge_equivalent REAL DEFAULT 0,
    itabag_equivalent REAL DEFAULT 0,
    updated_at TEXT DEFAULT (DATETIME('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, start_date) -- ユーザーと開始日の組み合わせを一意に
);

-- -----------------------------------------------------
-- 6. monthly_summariesテーブル
-- -----------------------------------------------------
DROP TABLE IF EXISTS monthly_summaries;
CREATE TABLE monthly_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    drink_total INTEGER DEFAULT 0,
    snack_total INTEGER DEFAULT 0,
    main_dish_total INTEGER DEFAULT 0,
    irregular_total INTEGER DEFAULT 0,
    monthly_total INTEGER DEFAULT 0,
    badge_equivalent REAL DEFAULT 0,
    itabag_equivalent REAL DEFAULT 0,
    updated_at TEXT DEFAULT (DATETIME('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, year, month)
);

-- -----------------------------------------------------
-- トリガー (updated_at の自動更新用)
-- -----------------------------------------------------

-- purchasesの更新時
CREATE TRIGGER trigger_purchases_updated_at
AFTER UPDATE ON purchases
BEGIN
    UPDATE purchases SET updated_at = DATETIME('now', 'localtime') WHERE purchase_id = OLD.purchase_id;
END;

-- daily_summariesの更新時
CREATE TRIGGER trigger_daily_summaries_updated_at
AFTER UPDATE ON daily_summaries
BEGIN
    UPDATE daily_summaries SET updated_at = DATETIME('now', 'localtime') WHERE summary_id = OLD.summary_id;
END;

-- weekly_summariesの更新時
CREATE TRIGGER trigger_weekly_summaries_updated_at
AFTER UPDATE ON weekly_summaries
BEGIN
    UPDATE weekly_summaries SET updated_at = DATETIME('now', 'localtime') WHERE summary_id = OLD.summary_id;
END;

-- monthly_summariesの更新時
CREATE TRIGGER trigger_monthly_summaries_updated_at
AFTER UPDATE ON monthly_summaries
BEGIN
    UPDATE monthly_summaries SET updated_at = DATETIME('now', 'localtime') WHERE summary_id = OLD.summary_id;
END;