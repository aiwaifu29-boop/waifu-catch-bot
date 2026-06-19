import aiosqlite
from typing import Optional
from .db import DB_PATH


async def set_title(user_id: int, title: str, given_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO user_titles (user_id, title, given_by)
               VALUES (?, ?, ?)""",
            (user_id, title, given_by)
        )
        await db.commit()


async def remove_title(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_titles WHERE user_id=?", (user_id,))
        await db.commit()


async def get_title(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT title FROM user_titles WHERE user_id=?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_all_titles():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT ut.*, u.full_name, u.username
               FROM user_titles ut
               LEFT JOIN users u ON ut.user_id = u.user_id
               ORDER BY ut.given_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
