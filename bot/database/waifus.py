import aiosqlite
from .db import DB_PATH
from utils.helpers import pick_random_rarity, generate_waifu_id
import random

async def add_waifu(waifu_id: str, name: str, anime: str, rarity: str, file_id: str, added_by: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO waifus (waifu_id, name, anime, rarity, file_id, added_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (waifu_id, name, anime, rarity, file_id, added_by)
            )
            await db.commit()
            return True
        except:
            return False

async def get_waifu(waifu_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM waifus WHERE waifu_id=? AND is_active=1", (waifu_id,))
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

async def edit_waifu(waifu_id: str, name: str = None, anime: str = None, rarity: str = None, file_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if name:
            await db.execute("UPDATE waifus SET name=? WHERE waifu_id=?", (name, waifu_id))
        if anime:
            await db.execute("UPDATE waifus SET anime=? WHERE waifu_id=?", (anime, waifu_id))
        if rarity:
            await db.execute("UPDATE waifus SET rarity=? WHERE waifu_id=?", (rarity, waifu_id))
        if file_id:
            await db.execute("UPDATE waifus SET file_id=? WHERE waifu_id=?", (file_id, waifu_id))
        await db.commit()

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

async def get_all_waifus(limit: int = 50, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM waifus WHERE is_active=1 ORDER BY rarity, name LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
