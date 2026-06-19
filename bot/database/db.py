import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "waifu_bot.db")

async def get_db():
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                coins INTEGER DEFAULT 0,
                total_caught INTEGER DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                flood_until INTEGER DEFAULT 0,
                warn_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS waifus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waifu_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                anime TEXT NOT NULL,
                rarity TEXT NOT NULL,
                file_id TEXT NOT NULL,
                added_by INTEGER,
                added_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                waifu_id TEXT NOT NULL,
                caught_at TEXT DEFAULT (datetime('now')),
                is_favorite INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (waifu_id) REFERENCES waifus(waifu_id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                initiator_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                initiator_waifu TEXT NOT NULL,
                receiver_waifu TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                waifu_id TEXT NOT NULL,
                collection_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                collection_id INTEGER NOT NULL,
                waifu_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                listed_at TEXT DEFAULT (datetime('now')),
                sold_at TEXT,
                buyer_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER,
                added_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                user_id INTEGER,
                details TEXT,
                group_id INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                multiplier REAL DEFAULT 1.0,
                description TEXT,
                started_by INTEGER,
                started_at TEXT DEFAULT (datetime('now')),
                ends_at TEXT,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                message_count INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 1,
                approved_by INTEGER,
                approved_at TEXT,
                added_at TEXT DEFAULT (datetime('now')),
                spawn_threshold INTEGER DEFAULT 100,
                skip_member_check INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT,
                type TEXT DEFAULT 'channel',
                added_by INTEGER,
                added_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS spawn_state (
                group_id INTEGER PRIMARY KEY,
                waifu_id TEXT,
                spawned_at TEXT,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_rewards (
                user_id INTEGER PRIMARY KEY,
                last_daily TEXT,
                streak INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS user_titles (
                user_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                given_by INTEGER,
                given_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);
            CREATE INDEX IF NOT EXISTS idx_collections_waifu ON collections(waifu_id);
            CREATE INDEX IF NOT EXISTS idx_market_status ON market(status);
            CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(log_type);
        """)

        # Migrate existing tables safely
        for migration in [
            "ALTER TABLE groups ADD COLUMN spawn_threshold INTEGER DEFAULT 100",
            "ALTER TABLE groups ADD COLUMN skip_member_check INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(migration)
            except Exception:
                pass

        await db.commit()
        print("Database initialized successfully")
