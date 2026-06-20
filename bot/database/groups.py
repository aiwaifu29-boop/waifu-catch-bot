import asyncpg
from .db import get_pool
from datetime import datetime


async def get_or_create_group(group_id: int, group_name: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO groups (group_id, group_name) VALUES ($1, $2) "
            "ON CONFLICT (group_id) DO NOTHING",
            group_id, group_name
        )
        if group_name:
            await conn.execute(
                "UPDATE groups SET group_name=$1 WHERE group_id=$2", group_name, group_id
            )
        row = await conn.fetchrow("SELECT * FROM groups WHERE group_id=$1", group_id)
        return dict(row) if row else None


async def approve_group(group_id: int, approved_by: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE groups SET is_approved=1, approved_by=$1, approved_at=NOW() WHERE group_id=$2",
            approved_by, group_id
        )


async def deny_group(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE groups SET is_approved=0 WHERE group_id=$1", group_id)


async def is_group_approved(group_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT is_approved FROM groups WHERE group_id=$1", group_id)
        return bool(val) if val is not None else True


async def increment_message_count(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE groups SET message_count = message_count + 1 WHERE group_id=$1", group_id
        )
        val = await conn.fetchval("SELECT message_count FROM groups WHERE group_id=$1", group_id)
        return val or 0


async def reset_message_count(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE groups SET message_count=0 WHERE group_id=$1", group_id)


async def get_spawn_threshold(group_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            "SELECT spawn_threshold FROM groups WHERE group_id=$1", group_id
        )
        return int(val) if val else 100


async def set_spawn_threshold(group_id: int, threshold: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE groups SET spawn_threshold=$1 WHERE group_id=$2", threshold, group_id
        )


async def get_all_groups():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM groups ORDER BY added_at DESC")
        return [dict(r) for r in rows]


async def get_spawn_state(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM spawn_state WHERE group_id=$1", group_id)
        return dict(row) if row else None


async def set_spawn_state(group_id: int, waifu_id: str, spawned_at, expires_at):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO spawn_state (group_id, waifu_id, spawned_at, expires_at) "
            "VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (group_id) DO UPDATE "
            "SET waifu_id=$2, spawned_at=$3, expires_at=$4",
            group_id, waifu_id, spawned_at, expires_at
        )


async def clear_spawn_state(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM spawn_state WHERE group_id=$1", group_id)


async def add_required_channel(channel_id: str, channel_name: str, ch_type: str, added_by: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO required_channels (channel_id, channel_name, type, added_by) "
            "VALUES ($1, $2, $3, $4) ON CONFLICT (channel_id) DO NOTHING",
            channel_id, channel_name, ch_type, added_by
        )


async def remove_required_channel(channel_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM required_channels WHERE channel_id=$1", channel_id)


async def get_required_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM required_channels")
        return [dict(r) for r in rows]


async def bypass_group(group_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO groups (group_id, is_approved, skip_member_check) "
            "VALUES ($1, 1, 1) ON CONFLICT (group_id) DO UPDATE "
            "SET is_approved=1, skip_member_check=1",
            group_id
        )
