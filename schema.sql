-- VIEWS TABLE: tracks which users have viewed which posts
CREATE TABLE IF NOT EXISTS views (
    user_id INTEGER,
    post_id INTEGER,
    date_viewed TEXT,
    PRIMARY KEY (user_id, post_id)
);
-- USERS TABLE: user profiles, roles, and posting credits
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, -- Telegram ID
    username TEXT,
    role TEXT DEFAULT 'free', -- 'free', 'premium'
    credits INTEGER DEFAULT 0, -- # of posts left
    points REAL DEFAULT 0, -- fractional points for news views
    last_active TEXT, -- ISO timestamp of last activity
    date_joined TEXT
);

-- PAYMENTS TABLE: tracks payments made by users
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL, -- paid in Stars
    posts_bought INTEGER, -- how many posts unlocked
    date_paid TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- POSTS TABLE: stores post references only (heavy data in files)
CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_path TEXT, -- path to external file/image/video
    status TEXT DEFAULT 'active', -- active, expired
    date_posted TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
