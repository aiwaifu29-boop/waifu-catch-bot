from database.db import get_pool
from typing import Optional

RARITY_ORDER = ['Common', 'Rare', 'Super Rare', 'Epic', 'Mythic', 'Legendary', 'Premium', 'Exclusive']
RARITY_EMOJI = {
    'Common':    '⚪',
    'Rare':      '🟢',
    'Super Rare':'🔵',
    'Epic':      '🟣',
    'Mythic':    '🟠',
    'Legendary': '🟡',
    'Premium':   '💎',
    'Exclusive': '👑',
}
DUPES_PER_CARD = 10
CARDS_PER_UPGRADE = 10


async def get_duplicate_stats(user_id: int) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT w.rarity, SUM(sub.cnt - 1) AS dupes
            FROM (
                SELECT c.waifu_id, COUNT(*) AS cnt
                FROM collections c
                WHERE c.user_id = $1
                GROUP BY c.waifu_id
                HAVING COUNT(*) > 1
            ) sub
            JOIN waifus w ON w.waifu_id = sub.waifu_id
            GROUP BY w.rarity
        ''', user_id)
    return {r['rarity']: int(r['dupes']) for r in rows}


async def get_card_counts(user_id: int) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            'SELECT rarity, count FROM rarity_cards WHERE user_id = $1', user_id
        )
    return {r['rarity']: r['count'] for r in rows if r['count'] > 0}


async def _set_card_count(conn, user_id: int, rarity: str, delta: int):
    await conn.execute('''
        INSERT INTO rarity_cards (user_id, rarity, count) VALUES ($1, $2, $3)
        ON CONFLICT (user_id, rarity)
        DO UPDATE SET count = GREATEST(0, rarity_cards.count + $3)
    ''', user_id, rarity, delta)


async def exchange_duplicates(user_id: int, rarity: str):
    stats = await get_duplicate_stats(user_id)
    dupes = stats.get(rarity, 0)
    if dupes < DUPES_PER_CARD:
        return False, f'Yetarli duplicate yoq: {dupes}/{DUPES_PER_CARD}'
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            removed = await conn.fetch('''
                SELECT c.id FROM collections c
                JOIN waifus w ON w.waifu_id = c.waifu_id
                WHERE c.user_id = $1 AND w.rarity = $2
                  AND c.waifu_id IN (
                      SELECT waifu_id FROM collections WHERE user_id=$1
                      GROUP BY waifu_id HAVING COUNT(*) > 1
                  )
                  AND c.id NOT IN (
                      SELECT MIN(id) FROM collections WHERE user_id=$1 GROUP BY waifu_id
                  )
                ORDER BY c.id LIMIT $3
            ''', user_id, rarity, DUPES_PER_CARD)
            if len(removed) < DUPES_PER_CARD:
                return False, 'Tranzaksiya xatosi: yetarli duplicate topilmadi'
            ids = [r['id'] for r in removed]
            await conn.execute('DELETE FROM collections WHERE id = ANY($1::int[])', ids)
            await _set_card_count(conn, user_id, rarity, 1)
    emoji = RARITY_EMOJI.get(rarity, '🃏')
    return True, f'{emoji} <b>{rarity}</b> kartasi olindi!'


async def use_card(user_id: int, rarity: str):
    cards = await get_card_counts(user_id)
    if cards.get(rarity, 0) < 1:
        return False, f'{rarity} kartangiz yoq', None
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            waifu = await conn.fetchrow('''
                SELECT w.* FROM waifus w
                WHERE w.rarity = $1 AND w.is_active = 1
                  AND w.waifu_id NOT IN (
                      SELECT DISTINCT waifu_id FROM collections WHERE user_id=$2
                  )
                ORDER BY RANDOM() LIMIT 1
            ''', rarity, user_id)
            if not waifu:
                waifu = await conn.fetchrow(
                    'SELECT * FROM waifus WHERE rarity=$1 AND is_active=1 ORDER BY RANDOM() LIMIT 1',
                    rarity
                )
            if not waifu:
                return False, f'{rarity} raritydagi waifu topilmadi', None
            await _set_card_count(conn, user_id, rarity, -1)
            await conn.execute(
                'INSERT INTO collections (user_id, waifu_id) VALUES ($1, $2)',
                user_id, waifu['waifu_id']
            )
    return True, 'Yangi waifu qoshildi!', dict(waifu)


async def upgrade_cards(user_id: int, rarity: str):
    if rarity not in RARITY_ORDER:
        return False, 'Noma lum rarity'
    idx = RARITY_ORDER.index(rarity)
    if idx >= len(RARITY_ORDER) - 1:
        return False, f'{rarity} eng yuqori daraja!'
    next_rarity = RARITY_ORDER[idx + 1]
    cards = await get_card_counts(user_id)
    if cards.get(rarity, 0) < CARDS_PER_UPGRADE:
        return False, f'Yetarli karta yoq: {cards.get(rarity,0)}/{CARDS_PER_UPGRADE}'
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_card_count(conn, user_id, rarity, -CARDS_PER_UPGRADE)
            await _set_card_count(conn, user_id, next_rarity, 1)
    e1 = RARITY_EMOJI.get(rarity, '🃏')
    e2 = RARITY_EMOJI.get(next_rarity, '🃏')
    return True, f'{e1} 10x {rarity} → {e2} <b>{next_rarity}</b> kartasi!'