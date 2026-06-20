import asyncpg
from .db import get_pool
from datetime import datetime


async def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES ($1,$2,$3) "
            "ON CONFLICT (user_id) DO NOTHING",
            user_id, username, full_name
        )
        if username or full_name:
            await conn.execute(
                "UPDATE users SET username=$1, full_name=$2 WHERE user_id=$3",
                username, full_name, user_id
            )
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None


async def get_user(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None


async def get_user_by_username(username: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE username=$1", username)
        return dict(row) if row else None


async def add_coins(user_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET coins = coins + $1 WHERE user_id=$2", amount, user_id)


async def remove_coins(user_id: int, amount: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT coins FROM users WHERE user_id=$1", user_id)
        if not row or row['coins'] < amount:
            return False
        await conn.execute("UPDATE users SET coins = coins - $1 WHERE user_id=$2", amount, user_id)
        return True


async def get_user_rank(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            "SELECT COUNT(*)+1 FROM users "
            "WHERE total_caught > (SELECT total_caught FROM users WHERE user_id=$1)",
            user_id
        )
        return val or 1


async def ban_user(user_id: int, reason: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_banned=1, ban_reason=$1 WHERE user_id=$2", reason, user_id
        )


async def unban_user(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=$1", user_id
        )


async def set_flood_until(user_id: int, until_ts: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET flood_until=$1 WHERE user_id=$2", until_ts, user_id
        )


async def get_top_users(limit: int = 10, by: str = "total_caught"):
    allowed = {"total_caught", "coins"}
    col = by if by in allowed else "total_caught"
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM users WHERE is_banned=0 ORDER BY " + col + " DESC LIMIT $1", limit
        )
        return [dict(r) for r in rows]


async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=0")
        return [r['user_id'] for r in rows]


async def update_total_caught(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET total_caught = total_caught + 1 WHERE user_id=$1", user_id
        )


async def add_warn(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET warn_count = warn_count + 1 WHERE user_id=$1", user_id
        )
        val = await conn.fetchval("SELECT warn_count FROM users WHERE user_id=$1", user_id)
        return val or 0


async def reset_warns(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET warn_count=0 WHERE user_id=$1", user_id)


async def get_group_top(group_user_ids: list, limit: int = 10):
    if not group_user_ids:
        return []
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM users WHERE user_id = ANY($1) AND is_banned=0 "
            "ORDER BY total_caught DESC LIMIT $2",
            group_user_ids, limit
        )
        return [dict(r) for r in rows]


async def increment_trade_count(user_id1: int, user_id2: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET trade_count=trade_count+1 WHERE user_id=$1 OR user_id=$2",
            user_id1, user_id2
        )
