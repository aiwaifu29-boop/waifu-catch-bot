import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import waifus as waifu_db
from database import collections as col_db
from database import users as user_db
from database import groups as grp_db
from database import logs as log_db
from utils.helpers import get_rarity_emoji, get_coin_reward, format_waifu_card

SPAWN_THRESHOLD = 100
SPAWN_TIMEOUT = 15 * 60  # 15 minutes

active_spawns = {}

async def handle_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    group_id = chat.id
    user = update.effective_user
    if not user:
        return

    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    from middlewares.flood import check_flood
    if await check_flood(user.id, group_id, context):
        return

    count = await grp_db.increment_message_count(group_id)

    if count >= SPAWN_THRESHOLD:
        await grp_db.reset_message_count(group_id)

        if group_id in active_spawns:
            return

        await do_spawn(context, group_id, chat.title)

async def do_spawn(context: ContextTypes.DEFAULT_TYPE, group_id: int, group_name: str = None):
    from database.logs import get_event_multiplier
    multiplier = await get_event_multiplier()

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
        "expires_at": expires_at,
        "coin_multiplier": multiplier,
    }

    await grp_db.set_spawn_state(group_id, waifu["waifu_id"], spawned_at.isoformat(), expires_at.isoformat())

    caption = (
        f"✨ <b>YANGI WAIFU PAYDO BO'LDI!</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} Daraja: <b>{waifu['rarity']}</b>\n"
        f"🎌 Anime: <b>{waifu['anime']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>Ushbu qahramon kimligini bilib, ismini yozing!</b>\n"
        f"⏰ Vaqt: <b>15 daqiqa</b>"
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
                text=f"⌛ Vaqt tugadi! Waifu yo'qoldi.\n"
                     f"👤 Bu <b>{waifu_name}</b> edi. Keyingisini qo'lga kiritishga harakat qiling!",
                parse_mode="HTML"
            )
        except:
            pass

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    group_id = chat.id
    if group_id not in active_spawns:
        return

    spawn = active_spawns[group_id]
    if datetime.now() > spawn["expires_at"]:
        active_spawns.pop(group_id, None)
        return

    user = update.effective_user
    text = update.message.text or ""

    correct_name = spawn["waifu_name"].lower().strip()
    guess = text.lower().strip()

    if correct_name in guess or guess in correct_name or guess == correct_name:
        active_spawns.pop(group_id, None)
        await grp_db.clear_spawn_state(group_id)

        waifu = await waifu_db.get_waifu(spawn["waifu_id"])
        if not waifu:
            return

        await user_db.get_or_create_user(user.id, user.username, user.full_name)

        coin_reward = int(get_coin_reward(spawn["rarity"]) * spawn.get("coin_multiplier", 1.0))
        collection_id = await col_db.add_to_collection(user.id, spawn["waifu_id"])
        await user_db.add_coins(user.id, coin_reward)

        emoji = get_rarity_emoji(spawn["rarity"])
        mention = f'<a href="tg://user?id={user.id}">{user.full_name or user.username}</a>'

        await log_db.add_log("catch", user_id=user.id, details=f"waifu_id={spawn['waifu_id']}", group_id=group_id)

        await update.message.reply_text(
            f"🎉 {mention} waifuni qo'lga kiritdi!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>{waifu['name']}</b>\n"
            f"🎌 {waifu['anime']}\n"
            f"⭐ {waifu['rarity']}\n"
            f"🆔 <code>{waifu['waifu_id']}</code>\n"
            f"💰 +{coin_reward} coin olindi!\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML"
        )
