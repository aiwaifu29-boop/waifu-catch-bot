import random
import os
from datetime import datetime

RARITY_CONFIG = {
    "Common":     {"weight": 5000,  "emoji": "⚪", "coin_reward": 10,   "color": "white"},
    "Rare":       {"weight": 2500,  "emoji": "🟢", "coin_reward": 25,   "color": "green"},
    "Super Rare": {"weight": 1250,  "emoji": "🔵", "coin_reward": 50,   "color": "blue"},
    "Epic":       {"weight": 650,   "emoji": "🟣", "coin_reward": 100,  "color": "purple"},
    "Mythic":     {"weight": 300,   "emoji": "🟠", "coin_reward": 200,  "color": "orange"},
    "Legendary":  {"weight": 200,   "emoji": "🟡", "coin_reward": 500,  "color": "gold"},
    "Premium":    {"weight": 90,    "emoji": "💎", "coin_reward": 1000, "color": "cyan"},
    "Exclusive":  {"weight": 1,     "emoji": "👑", "coin_reward": 5000, "color": "rainbow"},
}

RARITY_ORDER = list(RARITY_CONFIG.keys())

def get_rarity_emoji(rarity: str) -> str:
    return RARITY_CONFIG.get(rarity, {}).get("emoji", "❓")

def get_coin_reward(rarity: str) -> int:
    return RARITY_CONFIG.get(rarity, {}).get("coin_reward", 10)

def pick_random_rarity() -> str:
    rarities = list(RARITY_CONFIG.keys())
    weights = [RARITY_CONFIG[r]["weight"] for r in rarities]
    return random.choices(rarities, weights=weights, k=1)[0]

def format_profile(user: dict, collection_count: int, rank: int, title: str = None) -> str:
    full_name = user['full_name'] or "Noma'lum"
    title_line = f"🏅 Unvon: <b>{title}</b>\n" if title else ""
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>PROFIL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{full_name}</b>\n"
        f"{title_line}"
        f"💰 Coin: <b>{user['coins']:,}</b>\n"
        f"🎴 Kolleksiya: <b>{collection_count}</b> ta\n"
        f"🏆 Topilgan: <b>{user['total_caught']}</b> ta\n"
        f"🔄 Trade: <b>{user['trade_count']}</b> ta\n"
        f"📊 Reyting: <b>#{rank}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

def format_waifu_card(waifu: dict, collection_id: int = None) -> str:
    emoji = get_rarity_emoji(waifu['rarity'])
    lines = [
        f"━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} <b>{waifu['rarity'].upper()}</b> {emoji}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📛 Ism: <b>{waifu['name']}</b>",
        f"🎌 Anime: <b>{waifu['anime']}</b>",
        f"🆔 ID: <code>{waifu['waifu_id']}</code>",
    ]
    if collection_id:
        lines.append(f"🗂 Kolleksiya ID: <code>{collection_id}</code>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def generate_waifu_id(rarity: str) -> str:
    prefix_map = {
        "Common": "CM", "Rare": "RR", "Super Rare": "SR",
        "Epic": "EP", "Mythic": "MY", "Legendary": "LG",
        "Premium": "PR", "Exclusive": "EX"
    }
    prefix = prefix_map.get(rarity, "WF")
    number = random.randint(100000, 999999)
    return f"{prefix}-{number}"

def is_god_admin(user_id: int) -> bool:
    god_id = os.environ.get("GOD_ADMIN_ID", "")
    try:
        return int(god_id) == user_id
    except Exception:
        return False
