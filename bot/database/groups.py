import aiosqlite
from .db import DB_PATH
from datetime import datetime

async def get_or_create_group(group_id: int, group_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """INSERT OR IGNORE INTO groups (group_id, group_name, is_approved)
               VALUES (?, ?, 1)""",
            (group_id, group_name)
        )
        if group_name:
            await db.execute(
                "UPDATE groups SET group_name=? WHERE group_id=?", (group_name, group_id)
            )
        await db.commit()
        cursor = await db.execute("SELECT * FROM groups WHERE group_id=?", (group_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def approve_group(group_id: int, approved_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE groups SET is_approved=1, approved_by=?, approved_at=? WHERE group_id=?",
            (approved_by, datetime.now().isoformat(), group_id)
        )
        await db.commit()

async def deny_group(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET is_approved=0 WHERE group_id=?", (group_id,))
        await db.commit()

async def is_group_approved(group_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_approved FROM groups WHERE group_id=?", (group_id,))
        row = await cursor.fetchone()
        return bool(row[0]) if row else True

async def increment_message_count(group_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE groups SET message_count = message_count + 1 WHERE group_id=?", (group_id,)
        )
        await db.commit()
        cursor = await db.execute("SELECT message_count FROM groups WHERE group_id=?", (group_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def reset_message_count(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET message_count=0 WHERE group_id=?", (group_id,))
        await db.commit()

async def get_spawn_threshold(group_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT spawn_threshold FROM groups WHERE group_id=?", (group_id,)
        )
        row = await cursor.fetchone()
        if row and row[0]:
            return int(row[0])
        return 100

async def set_spawn_threshold(group_id: int, threshold: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE groups SET spawn_threshold=? WHERE group_id=?", (threshold, group_id)
        )
        await db.commit()

async def get_all_groups():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM groups ORDER BY added_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_spawn_state(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM spawn_state WHERE group_id=?", (group_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def set_spawn_state(group_id: int, waifu_id: str, spawned_at: str, expires_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO spawn_state (group_id, waifu_id, spawned_at, expires_at)
               VALUES (?, ?, ?, ?)""",
            (group_id, waifu_id, spawned_at, expires_at)
        )
        await db.commit()

async def clear_spawn_state(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM spawn_state WHERE group_id=?", (group_id,))
        await db.commit()

async def add_required_channel(channel_id: str, channel_name: str, ch_type: str, added_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO required_channels (channel_id, channel_name, type, added_by) VALUES (?, ?, ?, ?)",
            (channel_id, channel_name, ch_type, added_by)
        )
        await db.commit()

async def remove_required_channel(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM required_channels WHERE channel_id=?", (channel_id,))
        await db.commit()

async def get_required_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM required_channels")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
