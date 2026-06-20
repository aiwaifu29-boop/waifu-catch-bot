import asyncpg
import os
import logging

logger = logging.getLogger(__name__)
_pool = None


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError('DB pool not initialized. Call init_db() first.')
    return _pool


async def init_db():
    global _pool
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError('DATABASE_URL environment variable is not set!')
    _pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                coins BIGINT DEFAULT 0,
                total_caught INTEGER DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                flood_until BIGINT DEFAULT 0,
                warn_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS waifus (
                id SERIAL PRIMARY KEY,
                waifu_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                anime TEXT NOT NULL,
                rarity TEXT NOT NULL,
                file_id TEXT NOT NULL,
                added_by BIGINT,
                added_at TIMESTAMP DEFAULT NOW(),
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS collections (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                waifu_id TEXT NOT NULL,
                caught_at TIMESTAMP DEFAULT NOW(),
                is_favorite INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                initiator_id BIGINT NOT NULL,
                receiver_id BIGINT NOT NULL,
                initiator_waifu TEXT NOT NULL,
                receiver_waifu TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS gifts (
                id SERIAL PRIMARY KEY,
                sender_id BIGINT NOT NULL,
                receiver_id BIGINT NOT NULL,
                waifu_id TEXT NOT NULL,
                collection_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS market (
                id SERIAL PRIMARY KEY,
                seller_id BIGINT NOT NULL,
                collection_id INTEGER NOT NULL,
                waifu_id TEXT NOT NULL,
                price BIGINT NOT NULL,
                status TEXT DEFAULT 'active',
                listed_at TIMESTAMP DEFAULT NOW(),
                sold_at TIMESTAMP,
                buyer_id BIGINT
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                added_by BIGINT,
                added_at TIMESTAMP DEFAULT NOW(),
                role TEXT DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                log_type TEXT NOT NULL,
                user_id BIGINT,
                details TEXT,
                group_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                event_type TEXT NOT NULL,
                multiplier DOUBLE PRECISION DEFAULT 1.0,
                description TEXT,
                started_by BIGINT,
                started_at TIMESTAMP DEFAULT NOW(),
                ends_at TIMESTAMP,
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS groups (
                group_id BIGINT PRIMARY KEY,
                group_name TEXT,
                message_count INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 1,
                approved_by BIGINT,
                approved_at TIMESTAMP,
                added_at TIMESTAMP DEFAULT NOW(),
                spawn_threshold INTEGER DEFAULT 100,
                skip_member_check INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS required_channels (
                id SERIAL PRIMARY KEY,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT,
                type TEXT DEFAULT 'channel',
                added_by BIGINT,
                added_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS spawn_state (
                group_id BIGINT PRIMARY KEY,
                waifu_id TEXT,
                spawned_at TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS daily_rewards (
                user_id BIGINT PRIMARY KEY,
                last_daily TIMESTAMP,
                streak INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS user_titles (
                user_id BIGINT PRIMARY KEY,
                title TEXT NOT NULL,
                given_by BIGINT,
                given_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS daily_shop (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                shop_date TEXT NOT NULL,
                slot INTEGER NOT NULL,
                waifu_id TEXT NOT NULL,
                price BIGINT NOT NULL,
                is_sold INTEGER DEFAULT 0,
                UNIQUE(user_id, shop_date, slot)
            );
            CREATE TABLE IF NOT EXISTS rarity_cards (
                user_id BIGINT NOT NULL,
                rarity TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, rarity)
            );
            CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);
            CREATE INDEX IF NOT EXISTS idx_collections_waifu ON collections(waifu_id);
            CREATE INDEX IF NOT EXISTS idx_market_status ON market(status);
            CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(log_type);
        ''')
    logger.info('PostgreSQL database initialized successfully')