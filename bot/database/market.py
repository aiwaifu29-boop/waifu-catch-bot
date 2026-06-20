import asyncpg
  from .db import get_pool


  async def list_on_market(seller_id: int, collection_id: int, waifu_id: str, price: int) -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow(
              "INSERT INTO market (seller_id, collection_id, waifu_id, price) "
              "VALUES ($1,$2,$3,$4) RETURNING id",
              seller_id, collection_id, waifu_id, price
          )
          return row['id']


  async def get_market_listing(listing_id: int):
      pool = await get_pool()
      async with pool.acquire() as conn:
          row = await conn.fetchrow(
              "SELECT m.*, w.name, w.anime, w.rarity, w.file_id, u.username as seller_username "
              "FROM market m "
              "JOIN waifus w ON m.waifu_id=w.waifu_id "
              "JOIN users u ON m.seller_id=u.user_id "
              "WHERE m.id=$1 AND m.status='active'",
              listing_id
          )
          return dict(row) if row else None


  async def get_active_listings(limit: int = 10, offset: int = 0):
      pool = await get_pool()
      async with pool.acquire() as conn:
          rows = await conn.fetch(
              "SELECT m.*, w.name, w.anime, w.rarity, u.username as seller_username "
              "FROM market m "
              "JOIN waifus w ON m.waifu_id=w.waifu_id "
              "JOIN users u ON m.seller_id=u.user_id "
              "WHERE m.status='active' ORDER BY m.listed_at DESC LIMIT $1 OFFSET $2",
              limit, offset
          )
          return [dict(r) for r in rows]


  async def buy_from_market(listing_id: int, buyer_id: int) -> bool:
      pool = await get_pool()
      async with pool.acquire() as conn:
          res = await conn.execute(
              "UPDATE market SET status='sold', buyer_id=$1, sold_at=NOW() "
              "WHERE id=$2 AND status='active'",
              buyer_id, listing_id
          )
          return res.split()[-1] != '0'


  async def cancel_listing(listing_id: int, seller_id: int) -> bool:
      pool = await get_pool()
      async with pool.acquire() as conn:
          res = await conn.execute(
              "UPDATE market SET status='cancelled' WHERE id=$1 AND seller_id=$2 AND status='active'",
              listing_id, seller_id
          )
          return res.split()[-1] != '0'


  async def count_active_listings() -> int:
      pool = await get_pool()
      async with pool.acquire() as conn:
          return await conn.fetchval("SELECT COUNT(*) FROM market WHERE status='active'") or 0
  