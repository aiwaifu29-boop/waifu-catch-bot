import aiosqlite
from .db import DB_PATH


async def add_log(log_type: str, user_id: int = None, details: str = None, group_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (log_type, user_id, details, group_id) VALUES (?, ?, ?, ?)",
            (log_type, user_id, details, group_id)
        )
        await db.commit()


async def get_logs(log_type: str = None, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if log_type:
            cursor = await db.execute(
                "SELECT * FROM logs WHERE log_type=? ORDER BY created_at DESC LIMIT ?",
                (log_type, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_event_multiplier() -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT multiplier FROM events WHERE is_active=1 ORDER BY started_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return float(row["multiplier"]) if row else 1.0


async def get_active_event():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM events WHERE is_active=1 ORDER BY started_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def start_event(event_type: str, multiplier: float, description: str, started_by: int, hours: int = 2):
    from datetime import datetime, timedelta
    ends_at = (datetime.now() + timedelta(hours=hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE events SET is_active=0")
        await db.execute(
            """INSERT INTO events (event_type, multiplier, description, started_by, ends_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_type, multiplier, description, started_by, ends_at)
        )
        await db.commit()


async def stop_event():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE events SET is_active=0")
        await db.commit()


async def get_daily_reward(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM daily_rewards WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_daily_reward(user_id: int, streak: int):
    from datetime import datetime
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO daily_rewards (user_id, last_daily, streak)
               VALUES (?, ?, ?)""",
            (user_id, datetime.now().isoformat(), streak)
        )
        await db.commit()


async def get_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_admin(user_id: int, username: str, added_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
            (user_id, username, added_by)
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def is_admin(user_id: int) -> bool:
    from utils.helpers import is_god_admin
    if is_god_admin(user_id):
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return row is not None


async def get_group_top(group_id: int, limit: int = 10, mode: str = "waifu"):
    """Get top users in a specific group based on catch logs."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if mode in ("coin", "coins"):
            # For coin mode, show top coins globally but only for users who participated in this group
            cursor = await db.execute(
                """SELECT u.user_id, u.full_name, u.username, u.coins,
                          COUNT(l.id) as catch_count
                   FROM logs l
                   JOIN users u ON l.user_id = u.user_id
                   WHERE l.group_id=? AND l.log_type='catch' AND u.is_banned=0
                   GROUP BY l.user_id
                   ORDER BY u.coins DESC
                   LIMIT ?""",
                (group_id, limit)
            )
        else:
            cursor = await db.execute(
                """SELECT u.user_id, u.full_name, u.username, u.coins,
                          COUNT(l.id) as catch_count
                   FROM logs l
                   JOIN users u ON l.user_id = u.user_id
                   WHERE l.group_id=? AND l.log_type='catch' AND u.is_banned=0
                   GROUP BY l.user_id
                   ORDER BY catch_count DESC
                   LIMIT ?""",
                (group_id, limit)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_required_channels_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM required_channels")
        row = await cursor.fetchone()
        return row[0] if row else 0
