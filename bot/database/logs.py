import asyncpg
  from .db import get_pool


  async def add_log(log_type: str, user_id: int = None, details: str = None, group_id: int = None):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute(
              "INSERT INTO logs (log_type, user_id, details, group_id) VALUES ($1,$2,$3,$4)",
              log_type, user_id, details, group_id
          )


  async def get_logs(log_type: str = None, limit: int = 20):
      pool = await get_pool()
      async with pool.acquire() as conn:
          if log_type:
              rows = await conn.fetch(
                  "SELECT * FROM logs WHERE log_type=$1 ORDER BY created_at DESC LIMIT $2",
                  log_type, limit
              )
          else:
              rows = await conn.fetch(
                  "SELECT * FROM logs ORDER BY created_at DESC LIMIT $1", limit
              )
          return [dict(r) for r in rows]


  async def get_event_multiplier() -> float:
      pool = await get_pool()
      async with pool.acquire() as conn:
          val = await conn.fetchval(
              "SELECT multiplier FROM events WHERE is_active=1 ORDER BY started_at DESC LIMIT 1"
          )
          return float(val) if val else 1.0


  async def get_active_event():
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow(
              "SELECT * FROM events WHERE is_active=1 ORDER BY started_at DESC LIMIT 1"
          )
          return dict(row) if row else None


  async def start_event(event_type: str, multiplier: float, description: str,
                        started_by: int, hours: int = 2):
      from datetime import datetime, timedelta
      ends_at = datetime.now() + timedelta(hours=hours)
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute("UPDATE events SET is_active=0")
          await conn.execute(
              "INSERT INTO events (event_type, multiplier, description, started_by, ends_at) "
              "VALUES ($1,$2,$3,$4,$5)",
              event_type, multiplier, description, started_by, ends_at
          )


  async def stop_event():
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute("UPDATE events SET is_active=0")


  async def get_daily_reward(user_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow("SELECT * FROM daily_rewards WHERE user_id=$1", user_id)
          return dict(row) if row else None


  async def set_daily_reward(user_id: int, streak: int):
      from datetime import datetime
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute(
              "INSERT INTO daily_rewards (user_id, last_daily, streak) VALUES ($1, NOW(), $2) "
              "ON CONFLICT (user_id) DO UPDATE SET last_daily=NOW(), streak=$2",
              user_id, streak
          )


  async def get_admins():
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch("SELECT * FROM admins ORDER BY role, added_at")
          return [dict(r) for r in rows]


  async def add_admin(user_id: int, username: str, added_by: int, role: str = "admin"):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute(
              "INSERT INTO admins (user_id, username, added_by, role) VALUES ($1,$2,$3,$4) "
              "ON CONFLICT (user_id) DO UPDATE SET username=$2, added_by=$3, role=$4",
              user_id, username, added_by, role
          )


  async def remove_admin(user_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute("DELETE FROM admins WHERE user_id=$1", user_id)


  async def is_admin(user_id: int) -> bool:
      from utils.helpers import is_god_admin
      if is_god_admin(user_id):
          return True
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow("SELECT 1 FROM admins WHERE user_id=$1", user_id)
          return row is not None


  async def get_admin_role(user_id: int) -> str:
      from utils.helpers import is_god_admin
      if is_god_admin(user_id):
          return "god"
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow("SELECT role FROM admins WHERE user_id=$1", user_id)
          if row:
              return row['role'] or "admin"
          return None


  async def is_sub_admin_only(user_id: int) -> bool:
      role = await get_admin_role(user_id)
      return role == "sub"


  async def is_full_admin(user_id: int) -> bool:
      role = await get_admin_role(user_id)
      return role in ("god", "admin")


  async def get_required_channels_count() -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          return await conn.fetchval("SELECT COUNT(*) FROM required_channels") or 0


  async def register_god_admin(god_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute(
              "INSERT INTO admins (user_id, username, added_by, role) VALUES ($1,'god_admin',$1,'god') "
              "ON CONFLICT (user_id) DO UPDATE SET role='god'",
              god_id
          )
  