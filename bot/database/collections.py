import asyncpg
from .db import get_pool


async def add_to_collection(user_id: int, waifu_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO collections (user_id, waifu_id) VALUES ($1, $2) RETURNING id",
            user_id, waifu_id
        )
        await conn.execute(
            "UPDATE users SET total_caught = total_caught + 1 WHERE user_id=$1", user_id
        )
        return row['id']


async def get_collection(user_id: int, rarity: str = None, anime: str = None,
                         limit: int = 10, offset: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = ["c.user_id=$1", "w.is_active=1"]
        params = [user_id]
        if rarity:
            params.append(rarity)
            conditions.append("w.rarity=$" + str(len(params)))
        if anime:
            params.append("%" + anime + "%")
            conditions.append("w.anime ILIKE $" + str(len(params)))
        params.append(limit)
        lp = len(params)
        params.append(offset)
        op = len(params)
        where = " AND ".join(conditions)
        q = (
            "SELECT c.id as collection_id, c.caught_at, c.is_favorite, "
            "w.waifu_id, w.name, w.anime, w.rarity, w.file_id "
            "FROM collections c JOIN waifus w ON c.waifu_id = w.waifu_id "
            "WHERE " + where + " "
            "ORDER BY c.is_favorite DESC, w.rarity, w.name "
            "LIMIT $" + str(lp) + " OFFSET $" + str(op)
        )
        rows = await conn.fetch(q, *params)
        return [dict(r) for r in rows]


async def get_collection_item(collection_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT c.*, w.name, w.anime, w.rarity, w.file_id "
            "FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id "
            "WHERE c.id=$1",
            collection_id
        )
        return dict(row) if row else None


async def count_collection(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM collections WHERE user_id=$1", user_id) or 0


async def remove_from_collection(collection_id: int, user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            "DELETE FROM collections WHERE id=$1 AND user_id=$2", collection_id, user_id
        )
        return res.split()[-1] != '0'


async def transfer_collection_item(collection_id: int, from_user: int, to_user: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            "UPDATE collections SET user_id=$1 WHERE id=$2 AND user_id=$3",
            to_user, collection_id, from_user
        )
        return res.split()[-1] != '0'


async def set_favorite(collection_id: int, user_id: int, fav: bool):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE collections SET is_favorite=$1 WHERE id=$2 AND user_id=$3",
            1 if fav else 0, collection_id, user_id
        )


async def get_exclusive_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id "
            "WHERE c.user_id=$1 AND w.rarity='Exclusive'", user_id
        ) or 0


async def get_legendary_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM collections c JOIN waifus w ON c.waifu_id=w.waifu_id "
            "WHERE c.user_id=$1 AND w.rarity='Legendary'", user_id
        ) or 0
