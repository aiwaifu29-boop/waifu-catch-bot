import asyncpg
import random
from datetime import date
from typing import Optional
from .db import get_pool

SHOP_PRICES = {
    "Common":     (100,   400),
    "Rare":       (400,   1200),
    "Super Rare": (1200,  3500),
    "Epic":       (3500,  9000),
    "Mythic":     (15000, 60000),
    "Legendary":  (80000, 250000),
    "Premium":    (10000, 40000),
    "Exclusive":  (200000, 999999),
}

SLOT_RARITIES = [
    ["Common", "Common", "Common", "Common", "Rare"],
    ["Common", "Common", "Rare", "Rare", "Super Rare"],
    ["Rare", "Rare", "Super Rare", "Super Rare", "Epic"],
    ["Super Rare", "Epic", "Epic", "Mythic"],
    (
        ["Common"] * 40 + ["Rare"] * 25 + ["Super Rare"] * 15 +
        ["Epic"] * 10 + ["Mythic"] * 6 + ["Legendary"] * 3 + ["Premium"] * 1
    ),
]


def _today() -> str:
    return date.today().isoformat()


def _random_price(rarity: str) -> int:
    lo, hi = SHOP_PRICES.get(rarity, (100, 1000))
    return random.randint(lo, hi)


async def get_daily_shop(user_id: int) -> list:
    today = _today()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT ds.slot, ds.price, ds.is_sold, ds.waifu_id, "
            "w.name, w.anime, w.rarity, w.file_id "
            "FROM daily_shop ds JOIN waifus w ON ds.waifu_id = w.waifu_id "
            "WHERE ds.user_id=$1 AND ds.shop_date=$2 ORDER BY ds.slot",
            user_id, today
        )
        return [dict(r) for r in rows]


async def generate_daily_shop(user_id: int) -> list:
    today = _today()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM daily_shop WHERE user_id=$1 AND shop_date=$2", user_id, today
        )
        used_ids = set()
        items = []
        for slot_idx, rarity_pool in enumerate(SLOT_RARITIES, start=1):
            rarity = random.choice(rarity_pool)
            candidates = await conn.fetch(
                "SELECT waifu_id, name, anime, rarity, file_id FROM waifus "
                "WHERE rarity=$1 AND is_active=1 ORDER BY RANDOM() LIMIT 10",
                rarity
            )
            if not candidates:
                candidates = await conn.fetch(
                    "SELECT waifu_id, name, anime, rarity, file_id FROM waifus "
                    "WHERE is_active=1 ORDER BY RANDOM() LIMIT 10"
                )
            waifu = None
            for c in candidates:
                if c['waifu_id'] not in used_ids:
                    waifu = dict(c)
                    used_ids.add(c['waifu_id'])
                    break
            if not waifu:
                continue
            price = _random_price(waifu['rarity'])
            await conn.execute(
                "INSERT INTO daily_shop (user_id, shop_date, slot, waifu_id, price, is_sold) "
                "VALUES ($1,$2,$3,$4,$5,0)",
                user_id, today, slot_idx, waifu['waifu_id'], price
            )
            items.append({
                "slot": slot_idx,
                "waifu_id": waifu['waifu_id'],
                "name": waifu['name'],
                "anime": waifu['anime'],
                "rarity": waifu['rarity'],
                "file_id": waifu['file_id'],
                "price": price,
                "is_sold": 0,
            })
        return items


async def buy_shop_slot(user_id: int, slot: int) -> dict:
    today = _today()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT ds.*, w.name, w.anime, w.rarity, w.file_id "
            "FROM daily_shop ds JOIN waifus w ON ds.waifu_id=w.waifu_id "
            "WHERE ds.user_id=$1 AND ds.shop_date=$2 AND ds.slot=$3",
            user_id, today, slot
        )
        if not row:
            return {"error": "Slot topilmadi"}
        item = dict(row)
        if item['is_sold']:
            return {"error": "Bu slot allaqachon sotib olingan"}
        coins = await conn.fetchval("SELECT coins FROM users WHERE user_id=$1", user_id)
        if coins is None or coins < item['price']:
            return {"error": "Coiningiz yetarli emas. Kerak: " + str(item['price'])}
        await conn.execute("UPDATE users SET coins=coins-$1 WHERE user_id=$2", item['price'], user_id)
        await conn.execute(
            "UPDATE daily_shop SET is_sold=1 WHERE user_id=$1 AND shop_date=$2 AND slot=$3",
            user_id, today, slot
        )
        await conn.execute(
            "INSERT INTO collections (user_id, waifu_id) VALUES ($1,$2)", user_id, item['waifu_id']
        )
        await conn.execute(
            "UPDATE users SET total_caught=total_caught+1 WHERE user_id=$1", user_id
        )
        return {"ok": True, "item": item}


async def get_or_create_shop(user_id: int) -> list:
    items = await get_daily_shop(user_id)
    if not items:
        items = await generate_daily_shop(user_id)
    return items
