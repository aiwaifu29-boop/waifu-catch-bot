import aiosqlite
from .db import DB_PATH

async def add_to_collection(user_id: int, waifu_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO collections (user_id, waifu_id) VALUES (?, ?)",
            (user_id, waifu_id)
        )
        await db.execute("UPDATE users SET total_caught = total_caught + 1 WHERE user_id=?", (user_id,))
        await db.commit()
        return cursor.lastrowid

async def get_collection(user_id: int, rarity: str = None, anime: str = None, limit: int = 10, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT c.id as collection_id, c.caught_at, c.is_favorite,
                   w.waifu_id, w.name, w.anime, w.rarity, w.file_id
            FROM collections c JOIN waifus w ON c.waifu_id = w.waifu_id
            WHERE c.user_id=? AND w.is_active=1
        """
        params = [user_id]
        if rarity:
            query += " AND w.rarity=?"
            params.append(rarity)
        if anime:
            query += " AND w.anime LIKE ?"
            params.append(f"%{anime}%")
        query += " ORDER BY c.is_favorite DESC, w.rarity, w.name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_collection_item(collection_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT c.*, w.name, w.anime, w.rarity, w.file_id
               FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id
               WHERE c.id=?""",
            (collection_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def count_collection(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM collections WHERE user_id=?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def remove_from_collection(collection_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM collections WHERE id=? AND user_id=?", (collection_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def transfer_collection_item(collection_id: int, from_user: int, to_user: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE collections SET user_id=? WHERE id=? AND user_id=?",
            (to_user, collection_id, from_user)
        )
        await db.commit()
        return cursor.rowcount > 0

async def set_favorite(collection_id: int, user_id: int, fav: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE collections SET is_favorite=? WHERE id=? AND user_id=?",
            (1 if fav else 0, collection_id, user_id)
        )
        await db.commit()

async def get_exclusive_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id
               WHERE c.user_id=? AND w.rarity='Exclusive'""",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_legendary_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id
               WHERE c.user_id=? AND w.rarity='Legendary'""",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
