import asyncpg
from typing import Optional
from .db import get_pool


async def set_title(user_id: int, title: str, given_by: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_titles (user_id, title, given_by) VALUES ($1,$2,$3) "
            "ON CONFLICT (user_id) DO UPDATE SET title=$2, given_by=$3, given_at=NOW()",
            user_id, title, given_by
        )


async def remove_title(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_titles WHERE user_id=$1", user_id)


async def get_title(user_id: int) -> Optional[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT title FROM user_titles WHERE user_id=$1", user_id)


async def get_all_titles():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT ut.*, u.full_name, u.username "
            "FROM user_titles ut LEFT JOIN users u ON ut.user_id = u.user_id "
            "ORDER BY ut.given_at DESC"
        )
        return [dict(r) for r in rows]
