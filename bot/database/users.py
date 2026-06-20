import aiosqlite
from .db import DB_PATH
from datetime import datetime

async def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, full_name)
               VALUES (?, ?, ?)""",
            (user_id, username, full_name)
        )
        if username or full_name:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username, full_name, user_id)
            )
        await db.commit()
        cursor = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def remove_coins(user_id: int, amount: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if not row or row["coins"] < amount:
            return False
        await db.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, user_id))
        await db.commit()
        return True

async def get_user_rank(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*)+1 as rank FROM users WHERE total_caught > (SELECT total_caught FROM users WHERE user_id=?)",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 1

async def ban_user(user_id: int, reason: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, user_id))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (user_id,))
        await db.commit()

async def set_flood_until(user_id: int, until_ts: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET flood_until=? WHERE user_id=?", (until_ts, user_id))
        await db.commit()

async def get_top_users(limit: int = 10, by: str = "total_caught"):
    allowed = {"total_caught", "coins"}
    col = by if by in allowed else "total_caught"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT * FROM users WHERE is_banned=0 ORDER BY {col} DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
        rows = await cursor.fetchall()
        return [r["user_id"] for r in rows]

async def update_total_caught(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET total_caught = total_caught + 1 WHERE user_id=?", (user_id,))
        await db.commit()


async def add_warn(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET warn_count = warn_count + 1 WHERE user_id=?", (user_id,))
        await db.commit()
        cursor = await db.execute("SELECT warn_count FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 1
