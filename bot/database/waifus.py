import asyncpg
  from .db import get_pool
  from utils.helpers import pick_random_rarity


  async def add_waifu(name: str, anime: str, rarity: str, file_id: str, added_by: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          try:
              row = await conn.fetchrow(
                  "INSERT INTO waifus (waifu_id, name, anime, rarity, file_id, added_by) "
                  "VALUES ('__tmp__', $1, $2, $3, $4, $5) RETURNING id",
                  name, anime, rarity, file_id, added_by
              )
              new_id = row['id']
              waifu_id = str(new_id)
              await conn.execute(
                  "UPDATE waifus SET waifu_id=$1 WHERE id=$2", waifu_id, new_id
              )
              return True, waifu_id
          except Exception as e:
              print("add_waifu error:", e)
              return False, ""


  async def get_waifu(waifu_id: str):
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow(
              "SELECT * FROM waifus WHERE waifu_id=$1 AND is_active=1", waifu_id
          )
          return dict(row) if row else None


  async def get_waifu_by_db_id(db_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow(
              "SELECT * FROM waifus WHERE id=$1 AND is_active=1", db_id
          )
          return dict(row) if row else None


  async def get_random_waifu(rarity: str = None):
      pool = await get_pool()
      async with pool.acquire() as conn:
          if rarity:
              row = await conn.fetchrow(
                  "SELECT * FROM waifus WHERE rarity=$1 AND is_active=1 ORDER BY RANDOM() LIMIT 1", rarity
              )
          else:
              row = await conn.fetchrow(
                  "SELECT * FROM waifus WHERE is_active=1 ORDER BY RANDOM() LIMIT 1"
              )
          return dict(row) if row else None


  async def get_random_waifu_by_rarity_weight():
      rarity = pick_random_rarity()
      waifu = await get_random_waifu(rarity)
      if not waifu:
          waifu = await get_random_waifu()
      return waifu


  async def remove_waifu(waifu_id: str):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute("UPDATE waifus SET is_active=0 WHERE waifu_id=$1", waifu_id)


  async def remove_waifu_by_db_id(db_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          await conn.execute("UPDATE waifus SET is_active=0 WHERE id=$1", db_id)


  async def get_all_waifus_paginated(limit: int = 8, offset: int = 0):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT * FROM waifus WHERE is_active=1 ORDER BY id ASC LIMIT $1 OFFSET $2",
              limit, offset
          )
          return [dict(r) for r in rows]


  async def get_waifus_by_admin(added_by: int, limit: int = 8, offset: int = 0):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT * FROM waifus WHERE is_active=1 AND added_by=$1 ORDER BY id ASC LIMIT $2 OFFSET $3",
              added_by, limit, offset
          )
          return [dict(r) for r in rows]


  async def count_waifus_by_admin(added_by: int) -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          return await conn.fetchval(
              "SELECT COUNT(*) FROM waifus WHERE is_active=1 AND added_by=$1", added_by
          ) or 0


  async def count_all_active() -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          return await conn.fetchval("SELECT COUNT(*) FROM waifus WHERE is_active=1") or 0


  async def search_waifus(query: str, limit: int = 10):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT * FROM waifus WHERE is_active=1 AND (name ILIKE $1 OR anime ILIKE $1) LIMIT $2",
              "%" + query + "%", limit
          )
          return [dict(r) for r in rows]


  async def get_waifus_by_anime(anime: str, limit: int = 20):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT * FROM waifus WHERE is_active=1 AND anime ILIKE $1 LIMIT $2",
              "%" + anime + "%", limit
          )
          return [dict(r) for r in rows]


  async def count_waifus_by_rarity():
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT rarity, COUNT(*) as cnt FROM waifus WHERE is_active=1 GROUP BY rarity"
          )
          return {r['rarity']: r['cnt'] for r in rows}


  async def count_all_waifus() -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          return await conn.fetchval("SELECT COUNT(*) FROM waifus WHERE is_active=1") or 0


  async def get_all_waifus(limit: int = 50, offset: int = 0):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT * FROM waifus WHERE is_active=1 ORDER BY id ASC LIMIT $1 OFFSET $2",
              limit, offset
          )
          return [dict(r) for r in rows]
  