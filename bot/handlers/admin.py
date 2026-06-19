import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters
from database import waifus as waifu_db
from database import users as user_db
from database import logs as log_db
from database import groups as grp_db
from database import collections as col_db
from utils.helpers import get_rarity_emoji, is_god_admin, RARITY_ORDER, generate_waifu_id

ADD_WAIFU_PHOTO, ADD_WAIFU_NAME, ADD_WAIFU_ANIME, ADD_WAIFU_RARITY = range(4)
pending_waifu = {}

async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not await log_db.is_admin(user.id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q.")
        return False
    return True

async def require_god(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not is_god_admin(user.id):
        await update.message.reply_text("❌ Bu buyruq faqat God Admin uchun.")
        return False
    return True

async def cmd_addwaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return ConversationHandler.END
    await update.message.reply_text("📸 Waifu rasmini yuboring:")
    return ADD_WAIFU_PHOTO

async def received_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message.photo:
        await update.message.reply_text("❌ Rasm yuboring.")
        return ADD_WAIFU_PHOTO
    file_id = update.message.photo[-1].file_id
    pending_waifu[user.id] = {"file_id": file_id}
    await update.message.reply_text("✅ Rasm qabul qilindi.\n\n📝 Waifu ismini kiriting:")
    return ADD_WAIFU_NAME

async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Ism juda qisqa.")
        return ADD_WAIFU_NAME
    pending_waifu[user.id]["name"] = name
    await update.message.reply_text("🎌 Anime nomini kiriting:")
    return ADD_WAIFU_ANIME

async def received_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    anime = update.message.text.strip()
    pending_waifu[user.id]["anime"] = anime
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"rarity_{r}")]
        for r in RARITY_ORDER
    ])
    await update.message.reply_text("⭐ Darajani tanlang:", reply_markup=keyboard)
    return ADD_WAIFU_RARITY

async def received_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    rarity = query.data.replace("rarity_", "")
    data = pending_waifu.get(user.id, {})
    data["rarity"] = rarity
    waifu_id = generate_waifu_id(rarity)
    success = await waifu_db.add_waifu(
        waifu_id=waifu_id, name=data["name"], anime=data["anime"],
        rarity=rarity, file_id=data["file_id"], added_by=user.id
    )
    pending_waifu.pop(user.id, None)
    if success:
        emoji = get_rarity_emoji(rarity)
        await query.edit_message_text(
            f"✅ <b>WAIFU QO'SHILDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{waifu_id}</code>\n"
            f"📛 Ism: <b>{data['name']}</b>\n"
            f"🎌 Anime: <b>{data['anime']}</b>\n"
            f"{emoji} Daraja: <b>{rarity}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❌ Xatolik yuz berdi.")
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_waifu.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

async def cmd_removewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /removewaifu [waifu_id]")
        return
    await waifu_db.remove_waifu(context.args[0])
    await update.message.reply_text(f"✅ {context.args[0]} o'chirildi.")

async def cmd_spawn_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Faqat guruhda ishlaydi.")
        return
    from handlers.spawn import do_spawn
    await do_spawn(context, chat.id, chat.title)

async def cmd_setspawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set spawn threshold for current group. Min 100."""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Faqat guruhda ishlaydi.")
        return
    if not await require_admin(update, context): return
    if not context.args:
        current = await grp_db.get_spawn_threshold(chat.id)
        await update.message.reply_text(
            f"📊 Hozirgi spawn chegarasi: <b>{current}</b> ta xabar\n"
            f"Format: /setspawn [son] (minimum 100)",
            parse_mode="HTML"
        )
        return
    try:
        threshold = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Son kiriting.")
        return
    if threshold < 100:
        await update.message.reply_text("❌ Minimum 100 ta xabar bo'lishi kerak.")
        return
    await grp_db.set_spawn_threshold(chat.id, threshold)
    await update.message.reply_text(
        f"✅ Spawn chegarasi <b>{threshold}</b> ta xabarga o'rnatildi.",
        parse_mode="HTML"
    )

async def cmd_addgroup_bypass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """God admin adds a group bypassing member count check."""
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /addgroup [group_id]")
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Group ID raqam bo'lishi kerak.")
        return
    import aiosqlite
    from database.db import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO groups (group_id, is_approved, skip_member_check)
               VALUES (?, 1, 1)""",
            (gid,)
        )
        await db.commit()
    await update.message.reply_text(
        f"✅ Guruh <code>{gid}</code> ro'yxatga qo'shildi (limit chetlab o'tildi).",
        parse_mode="HTML"
    )

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /broadcast [xabar]")
        return
    message = " ".join(context.args)
    user_ids = await user_db.get_all_users()
    await update.message.reply_text(f"📢 {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")
    sent = failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, f"📢 <b>E'lon:</b>\n\n{message}", parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await update.message.reply_text(f"✅ Yuborildi: {sent} | ❌ Muvaffaqiyatsiz: {failed}")

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /addadmin [user_id] [username]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam bo'lishi kerak.")
        return
    username = context.args[1].lstrip("@") if len(context.args) > 1 else ""
    await log_db.add_admin(uid, username, update.effective_user.id)
    await update.message.reply_text(f"✅ {uid} admin qilindi.")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /removeadmin [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam bo'lishi kerak.")
        return
    await log_db.remove_admin(uid)
    await update.message.reply_text(f"✅ {uid} adminlikdan olib tashlandi.")

async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /banuser [user_id] [sabab]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam bo'lishi kerak.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Sabab ko'rsatilmagan"
    await user_db.ban_user(uid, reason)
    await log_db.add_log("ban", user_id=update.effective_user.id, details=f"banned={uid} reason={reason}")
    await update.message.reply_text(f"✅ {uid} bloklandi. Sabab: {reason}")

async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /unbanuser [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam bo'lishi kerak.")
        return
    await user_db.unban_user(uid)
    await update.message.reply_text(f"✅ {uid} blokdan chiqarildi.")

async def cmd_givecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /givecoins [user_id] [miqdor]")
        return
    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting.")
        return
    await user_db.add_coins(uid, amount)
    await log_db.add_log("give_coins", user_id=update.effective_user.id, details=f"to={uid} amount={amount}")
    await update.message.reply_text(f"✅ {uid} ga {amount:,} coin berildi.")

async def cmd_givewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /givewaifu [user_id] [waifu_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam bo'lishi kerak.")
        return
    waifu_id = context.args[1]
    waifu = await waifu_db.get_waifu(waifu_id)
    if not waifu:
        await update.message.reply_text(f"❌ {waifu_id} waifusi topilmadi.")
        return
    await col_db.add_to_collection(uid, waifu_id)
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_text(
        f"✅ {emoji} <b>{waifu['name']}</b> → {uid} ga berildi.", parse_mode="HTML"
    )

async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "📋 Event:\n/event start [tur] [multiplier] [soat] [tavsif]\n/event stop\n\n"
            "Turlar: double_spawn, double_coin, anime, seasonal"
        )
        return
    if args[0] == "start":
        if len(args) < 3:
            await update.message.reply_text("❌ Format: /event start [tur] [multiplier] [soat] [tavsif]")
            return
        event_type = args[1]
        try:
            multiplier = float(args[2])
            hours = int(args[3]) if len(args) > 3 else 2
        except ValueError:
            await update.message.reply_text("❌ Multiplikator raqam bo'lishi kerak.")
            return
        description = " ".join(args[4:]) if len(args) > 4 else event_type
        await log_db.start_event(event_type, multiplier, description, update.effective_user.id, hours)
        await update.message.reply_text(
            f"⚡ <b>EVENT BOSHLANDI!</b>\nTur: {event_type}\nx{multiplier} | {hours} soat",
            parse_mode="HTML"
        )
    elif args[0] == "stop":
        await log_db.stop_event()
        await update.message.reply_text("✅ Event to'xtatildi.")

async def cmd_approvegroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /approvegroup [group_id]")
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Group ID raqam bo'lishi kerak.")
        return
    await grp_db.approve_group(gid, update.effective_user.id)
    await update.message.reply_text(f"✅ Guruh {gid} tasdiqlandi.")

async def cmd_denygroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /denygroup [group_id]")
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Group ID raqam bo'lishi kerak.")
        return
    await grp_db.deny_group(gid)
    await update.message.reply_text(f"✅ Guruh {gid} rad etildi.")

async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /addchannel [channel_id] [nomi]\nMisol: /addchannel @mychannel Mening kanalim")
        return
    channel_id = context.args[0]
    name = " ".join(context.args[1:])
    await grp_db.add_required_channel(channel_id, name, "channel", update.effective_user.id)
    await update.message.reply_text(f"✅ Majburiy kanal qo'shildi: <b>{name}</b>", parse_mode="HTML")

async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /removechannel [channel_id]")
        return
    await grp_db.remove_required_channel(context.args[0])
    await update.message.reply_text("✅ Kanal olib tashlandi.")

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    user = update.effective_user
    god = is_god_admin(user.id)
    text = (
        f"🛡️ <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{'👑 God Admin' if god else '🔧 Admin'}\n\n"
        f"<b>Waifu:</b>\n"
        f"/addwaifu — qo'shish\n"
        f"/removewaifu [id] — o'chirish\n"
        f"/givewaifu [uid] [wid] — berish\n"
        f"/spawn — qo'lda chiqarish\n\n"
        f"<b>Guruh:</b>\n"
        f"/setspawn [son] — spawn chegarasi\n"
        f"/addgroup [id] — limitni chetlab qo'shish\n\n"
        f"<b>Foydalanuvchi:</b>\n"
        f"/banuser [id] — bloklash\n"
        f"/unbanuser [id] — blokdan chiqarish\n"
        f"/givecoins [id] [miqdor] — coin berish\n\n"
        f"<b>Event:</b>\n"
        f"/event start/stop\n"
    )
    if god:
        text += (
            f"\n<b>God Admin:</b>\n"
            f"/addadmin [id] — admin qo'shish\n"
            f"/removeadmin [id] — o'chirish\n"
            f"/broadcast [xabar] — e'lon\n"
            f"/addchannel [id] [nom] — majburiy kanal\n"
            f"/removechannel [id] — kanal o'chirish\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")

def get_addwaifu_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("addwaifu", cmd_addwaifu)],
        states={
            ADD_WAIFU_PHOTO: [MessageHandler(filters.PHOTO, received_photo)],
            ADD_WAIFU_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            ADD_WAIFU_ANIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_anime)],
            ADD_WAIFU_RARITY: [],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        per_user=True,
    )
