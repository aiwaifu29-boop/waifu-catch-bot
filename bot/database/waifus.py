import aiosqlite
from .db import DB_PATH
from utils.helpers import pick_random_rarity
import random


async def add_waifu(name: str, anime: str, rarity: str, file_id: str, added_by: int) -> tuple:
    """Waifu qo'shadi. Qaytaradi: (success: bool, waifu_id: str)"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO waifus (waifu_id, name, anime, rarity, file_id, added_by) VALUES ('__tmp__',?,?,?,?,?)",
                (name, anime, rarity, file_id, added_by)
            )
            new_id = cursor.lastrowid
            waifu_id = str(new_id)
            await db.execute("UPDATE waifus SET waifu_id=? WHERE id=?", (waifu_id, new_id))
            await db.commit()
            return True, waifu_id
        except Exception as e:
            print(f"add_waifu error: {e}")
            return False, ""


async def get_waifu(waifu_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM waifus WHERE waifu_id=? AND is_active=1", (waifu_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_waifu_by_db_id(db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM waifus WHERE id=? AND is_active=1", (db_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_random_waifu(rarity: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if rarity:
            cursor = await db.execute(
                "SELECT * FROM waifus WHERE rarity=? AND is_active=1 ORDER BY RANDOM() LIMIT 1", (rarity,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM waifus WHERE is_active=1 ORDER BY RANDOM() LIMIT 1"
            )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_random_waifu_by_rarity_weight():
    rarity = pick_random_rarity()
    waifu = await get_random_waifu(rarity)
    if not waifu:
        waifu = await get_random_waifu()
    return waifu


async def remove_waifu(waifu_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE waifus SET is_active=0 WHERE waifu_id=?", (waifu_id,))
        await db.commit()


async def remove_waifu_by_db_id(db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE waifus SET is_active=0 WHERE id=?", (db_id,))
        await db.commit()


async def get_all_waifus_paginated(limit: int = 8, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM waifus WHERE is_active=1 ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def count_all_active() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM waifus WHERE is_active=1")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def search_waifus(query: str, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM waifus WHERE is_active=1 AND (name LIKE ? OR anime LIKE ?) LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_waifus_by_anime(anime: str, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM waifus WHERE is_active=1 AND anime LIKE ? LIMIT ?",
            (f"%{anime}%", limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def count_waifus_by_rarity():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT rarity, COUNT(*) as cnt FROM waifus WHERE is_active=1 GROUP BY rarity"
        )
        rows = await cursor.fetchall()
        return {r["rarity"]: r["cnt"] for r in rows}


async def count_all_waifus() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM waifus WHERE is_active=1")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_all_waifus(limit: int = 50, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM waifus WHERE is_active=1 ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
