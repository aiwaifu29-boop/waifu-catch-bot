import aiosqlite
from .db import DB_PATH

async def list_on_market(seller_id: int, collection_id: int, waifu_id: str, price: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO market (seller_id, collection_id, waifu_id, price)
               VALUES (?, ?, ?, ?)""",
            (seller_id, collection_id, waifu_id, price)
        )
        await db.commit()
        return cursor.lastrowid

async def get_market_listing(listing_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT m.*, w.name, w.anime, w.rarity, w.file_id,
                      u.username as seller_username
               FROM market m
               JOIN waifus w ON m.waifu_id=w.waifu_id
               JOIN users u ON m.seller_id=u.user_id
               WHERE m.id=? AND m.status='active'""",
            (listing_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_active_listings(limit: int = 10, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT m.*, w.name, w.anime, w.rarity,
                      u.username as seller_username
               FROM market m
               JOIN waifus w ON m.waifu_id=w.waifu_id
               JOIN users u ON m.seller_id=u.user_id
               WHERE m.status='active'
               ORDER BY m.listed_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def buy_from_market(listing_id: int, buyer_id: int) -> bool:
    from datetime import datetime
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE market SET status='sold', buyer_id=?, sold_at=? WHERE id=? AND status='active'",
            (buyer_id, datetime.now().isoformat(), listing_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def cancel_listing(listing_id: int, seller_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE market SET status='cancelled' WHERE id=? AND seller_id=? AND status='active'",
            (listing_id, seller_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def count_active_listings() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM market WHERE status='active'")
        row = await cursor.fetchone()
        return row[0] if row else 0
