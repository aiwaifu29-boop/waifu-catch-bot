import asyncio
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database import waifus as waifu_db
from database import collections as col_db
from database import users as user_db
from database import groups as grp_db
from database import logs as log_db
from utils.helpers import get_rarity_emoji, get_coin_reward

SPAWN_TIMEOUT = 15 * 60  # 15 minutes

active_spawns = {}

# Catch rate limiting: user_id -> list of attempt timestamps
_catch_attempts: dict[int, list[float]] = {}
CATCH_LIMIT = 3       # max attempts
CATCH_WINDOW = 60     # seconds


def _is_catch_flooded(user_id: int) -> bool:
    now = time.time()
    attempts = _catch_attempts.get(user_id, [])
    attempts = [t for t in attempts if now - t < CATCH_WINDOW]
    if len(attempts) >= CATCH_LIMIT:
        _catch_attempts[user_id] = attempts
        return True
    attempts.append(now)
    _catch_attempts[user_id] = attempts
    return False


async def handle_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    group_id = chat.id
    user = update.effective_user
    if not user or user.is_bot:
        return

    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    # Check if bot has admin rights
    try:
        bot_member = await context.bot.get_chat_member(group_id, context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return
    except Exception:
        return

    # Flood check
    from middlewares.flood import check_flood
    is_flooded = await check_flood(user.id, group_id, context)
    if is_flooded:
        return

    threshold = await grp_db.get_spawn_threshold(group_id)
    count = await grp_db.increment_message_count(group_id)

    if count >= threshold:
        await grp_db.reset_message_count(group_id)
        if group_id not in active_spawns:
            await do_spawn(context, group_id, chat.title)


async def do_spawn(context: ContextTypes.DEFAULT_TYPE, group_id: int, group_name: str = None):
    multiplier = await log_db.get_event_multiplier()
    waifu = await waifu_db.get_random_waifu_by_rarity_weight()
    if not waifu:
        return

    emoji = get_rarity_emoji(waifu["rarity"])
    spawned_at = datetime.now()
    expires_at = spawned_at + timedelta(seconds=SPAWN_TIMEOUT)

    active_spawns[group_id] = {
        "waifu_id": waifu["waifu_id"],
        "waifu_name": waifu["name"],
        "file_id": waifu["file_id"],
        "rarity": waifu["rarity"],
        "anime": waifu["anime"],
        "expires_at": expires_at,
        "coin_multiplier": multiplier,
    }

    await grp_db.set_spawn_state(group_id, waifu["waifu_id"], spawned_at.isoformat(), expires_at.isoformat())

    caption = (
        f"✨ <b>Yangi waifu paydo bo'ldi!</b>\n"
        f"{emoji} {waifu['rarity']} • {waifu['anime']}\n\n"
        f"Tutish uchun /waifu buyrug'i bilan nomini yuboring"
    )

    await log_db.add_log("spawn", details=f"waifu_id={waifu['waifu_id']} rarity={waifu['rarity']}", group_id=group_id)

    try:
        await context.bot.send_photo(
            chat_id=group_id,
            photo=waifu["file_id"],
            caption=caption,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Spawn error: {e}")
        active_spawns.pop(group_id, None)
        return

    asyncio.create_task(expire_spawn(context, group_id, SPAWN_TIMEOUT))


async def expire_spawn(context: ContextTypes.DEFAULT_TYPE, group_id: int, timeout: int):
    await asyncio.sleep(timeout)
    if group_id in active_spawns:
        waifu_name = active_spawns[group_id]["waifu_name"]
        active_spawns.pop(group_id, None)
        await grp_db.clear_spawn_state(group_id)
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"⌛ Vaqt tugadi! <b>{waifu_name}</b> yo'qoldi.",
                parse_mode="HTML"
            )
        except Exception:
            pass


def _name_matches(guess: str, correct: str) -> bool:
    """
    Returns True if guess matches the waifu name or part of it.
    - Exact match (case-insensitive)
    - Any word of the name (min 2 chars)
    - Guess is contained in the name
    - Name starts with guess
    """
    guess = guess.lower().strip()
    correct = correct.lower().strip()
    if not guess:
        return False
    if guess == correct:
        return True
    if correct.startswith(guess) and len(guess) >= 2:
        return True
    if guess in correct and len(guess) >= 3:
        return True
    # Match any single word from the name
    name_words = [w for w in correct.split() if len(w) >= 2]
    guess_words = guess.split()
    for gw in guess_words:
        if len(gw) >= 2 and any(gw == nw or nw.startswith(gw) for nw in name_words):
            return True
    return False


async def cmd_waifu_catch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /waifu [name] command for catching waifus in groups."""
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    group_id = chat.id
    user = update.effective_user

    if group_id not in active_spawns:
        await update.message.reply_text("⚠️ Hozirda hech qanday waifu paydo bo'lmagan.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Format: <code>/waifu [ism]</code>\nMisol: <code>/waifu Rukia</code>",
            parse_mode="HTML"
        )
        return

    spawn = active_spawns[group_id]
    if datetime.now() > spawn["expires_at"]:
        active_spawns.pop(group_id, None)
        await update.message.reply_text("⌛ Bu waifu allaqachon yo'qolgan!")
        return

    # Flood/rate limit check for catch attempts
    if _is_catch_flooded(user.id):
        await update.message.reply_text(
            f"⏳ Juda tez! {CATCH_WINDOW} soniya ichida {CATCH_LIMIT} tadan ko'p urinish mumkin emas."
        )
        return

    guess = " ".join(context.args)

    if not _name_matches(guess, spawn["waifu_name"]):
        await update.message.reply_text("❌ Noto'g'ri! Yana urinib ko'ring.")
        return

    # Correct! Remove spawn
    active_spawns.pop(group_id, None)
    await grp_db.clear_spawn_state(group_id)

    waifu = await waifu_db.get_waifu(spawn["waifu_id"])
    if not waifu:
        return

    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    coin_reward = int(get_coin_reward(spawn["rarity"]) * spawn.get("coin_multiplier", 1.0))
    await col_db.add_to_collection(user.id, spawn["waifu_id"])
    await user_db.add_coins(user.id, coin_reward)

    emoji = get_rarity_emoji(spawn["rarity"])
    mention = f'<a href="tg://user?id={user.id}">{user.full_name or user.username}</a>'

    await log_db.add_log("catch", user_id=user.id, details=f"waifu_id={spawn['waifu_id']}", group_id=group_id)

    await update.message.reply_text(
        f"🎉 {mention} waifuni qo'lga kiritdi!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>{waifu['name']}</b>\n"
        f"🎌 {waifu['anime']} • ⭐ {waifu['rarity']}\n"
        f"🆔 <code>{waifu['waifu_id']}</code>\n"
        f"💰 +{coin_reward} coin!\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
