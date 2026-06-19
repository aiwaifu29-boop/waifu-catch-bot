import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
        if update.message:
            await update.message.reply_text("❌ Ruxsatingiz yo'q.")
        return False
    return True


async def require_god(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not is_god_admin(user.id):
        if update.message:
            await update.message.reply_text("❌ Bu buyruq faqat God Admin uchun.")
        return False
    return True


# ──────────────────────────────────────
#  WAIFU QO'SHISH (ConversationHandler)
# ──────────────────────────────────────

async def cmd_addwaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return ConversationHandler.END
    await update.message.reply_text("📸 Waifu rasmini yuboring:", reply_markup=ReplyKeyboardRemove())
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
    if not data:
        await query.edit_message_text("❌ Ma'lumot topilmadi. /addwaifu qayta boshlang.")
        return ConversationHandler.END
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
        await query.edit_message_text("❌ Xatolik yuz berdi. Ehtimol bu ID allaqachon mavjud.")
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_waifu.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ──────────────────────────────────────
#  ADMIN BUYRUQLARI
# ──────────────────────────────────────

async def cmd_removewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    if not context.args:
        await update.message.reply_text("❌ Format: /removewaifu [waifu_id]")
        return
    wid = context.args[0]
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
        await update.message.reply_text(f"❌ {wid} topilmadi.")
        return
    await waifu_db.remove_waifu(wid)
    await update.message.reply_text(f"✅ <b>{waifu['name']}</b> ({wid}) o'chirildi.", parse_mode="HTML")


async def cmd_spawn_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Faqat guruhda ishlaydi.")
        return
    from handlers.spawn import do_spawn
    await do_spawn(context, chat.id, chat.title)


async def cmd_setspawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"✅ Guruh <code>{gid}</code> ro'yxatga qo'shildi.",
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
        except Exception:
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
        await update.message.reply_text(
            "❌ Format: /addchannel [channel_id] [nomi]\n"
            "Misol: /addchannel @mychannel Mening kanalim"
        )
        return
    channel_id = context.args[0]
    name = " ".join(context.args[1:])
    try:
        await context.bot.get_chat(channel_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Kanal topilmadi yoki bot kira olmadi: {e}")
        return
    await grp_db.add_required_channel(channel_id, name, "channel", update.effective_user.id)
    await update.message.reply_text(
        f"✅ Majburiy kanal qo'shildi: <b>{name}</b>\n"
        f"🆔 ID: <code>{channel_id}</code>",
        parse_mode="HTML"
    )


async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context): return
    if not context.args:
        channels = await grp_db.get_required_channels()
        if not channels:
            await update.message.reply_text("📋 Majburiy kanallar yo'q.")
            return
        lines = ["📋 <b>Majburiy kanallar:</b>\n"]
        for ch in channels:
            lines.append(f"• <code>{ch['channel_id']}</code> — {ch.get('channel_name', '')}")
        lines.append("\nO'chirish: /removechannel [channel_id]")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return
    await grp_db.remove_required_channel(context.args[0])
    await update.message.reply_text(f"✅ <code>{context.args[0]}</code> kanal olib tashlandi.", parse_mode="HTML")


# ──────────────────────────────────────
#  ADMIN PANEL  (pastki klaviatura)
# ──────────────────────────────────────

# Keyboard button labels
BTN_ADDWAIFU   = "➕ Waifu qo'shish"
BTN_RMWAIFU    = "🗑 Waifu o'chirish"
BTN_ADDCH      = "📢 Kanal qo'shish"
BTN_RMCH       = "❌ Kanal o'chirish"
BTN_COINS      = "💰 Coin berish"
BTN_GIVEW      = "🎴 Waifu berish"
BTN_BAN        = "🚫 Ban"
BTN_UNBAN      = "✅ Unban"
BTN_BROADCAST  = "📣 Broadcast"
BTN_EVENT      = "⚡ Event"
BTN_STATS      = "📊 Statistika"
BTN_SPAWN      = "🔧 Spawn"
BTN_ADDADMIN   = "👑 Admin qo'shish"
BTN_RMADMIN    = "🔴 Admin o'chirish"
BTN_CLOSE      = "🚪 Panelni yopish"

PANEL_HELP = {
    BTN_ADDWAIFU:  "➕ <b>Waifu qo'shish</b>\n\nBuyruq: /addwaifu\nBot bosqichma-bosqich rasm, ism, anime va darajani so'raydi.",
    BTN_RMWAIFU:   "🗑 <b>Waifu o'chirish</b>\n\nBuyruq: <code>/removewaifu [waifu_id]</code>\nMisol: <code>/removewaifu CM-123456</code>",
    BTN_ADDCH:     "📢 <b>Majburiy kanal qo'shish</b>\n\nBuyruq: <code>/addchannel [kanal_id] [nomi]</code>\nMisol: <code>/addchannel @mychannel Mening kanalim</code>",
    BTN_RMCH:      "❌ <b>Kanal o'chirish</b>\n\nBuyruq: <code>/removechannel [kanal_id]</code>\nRo'yxat: /removechannel (argumentsiz)",
    BTN_COINS:     "💰 <b>Coin berish</b>\n\nBuyruq: <code>/givecoins [user_id] [miqdor]</code>\nMisol: <code>/givecoins 123456789 1000</code>",
    BTN_GIVEW:     "🎴 <b>Waifu berish</b>\n\nBuyruq: <code>/givewaifu [user_id] [waifu_id]</code>\nMisol: <code>/givewaifu 123456789 LG-654321</code>",
    BTN_BAN:       "🚫 <b>Foydalanuvchini bloklash</b>\n\nBuyruq: <code>/banuser [user_id] [sabab]</code>\nMisol: <code>/banuser 123456789 Spam</code>",
    BTN_UNBAN:     "✅ <b>Blokdan chiqarish</b>\n\nBuyruq: <code>/unbanuser [user_id]</code>\nMisol: <code>/unbanuser 123456789</code>",
    BTN_BROADCAST: "📣 <b>Broadcast</b>\n\nBuyruq: <code>/broadcast [xabar]</code>\nMisol: <code>/broadcast Yangi event boshlandi!</code>\n\n⚠️ Faqat God Admin uchun.",
    BTN_EVENT:     "⚡ <b>Event boshqaruvi</b>\n\nBoshlash: <code>/event start [tur] [x] [soat] [tavsif]</code>\nTo'xtatish: <code>/event stop</code>\n\nTurlar: double_spawn, double_coin, anime, seasonal",
    BTN_STATS:     "📊 <b>Statistika</b>\n\nBuyruq: /stats",
    BTN_SPAWN:     "🔧 <b>Spawn sozlamalari</b>\n\nKo'rish: /setspawn\nO'zgartirish: <code>/setspawn [son]</code>\nQo'lda: /spawn\n\nMinimum: 100 xabar",
    BTN_ADDADMIN:  "👑 <b>Admin qo'shish</b>\n\nBuyruq: <code>/addadmin [user_id] [username]</code>\nMisol: <code>/addadmin 123456789 johndoe</code>",
    BTN_RMADMIN:   "🔴 <b>Admin o'chirish</b>\n\nBuyruq: <code>/removeadmin [user_id]</code>\nMisol: <code>/removeadmin 123456789</code>",
}

ALL_PANEL_BUTTONS = set(PANEL_HELP.keys()) | {BTN_CLOSE}


def build_panel_reply_keyboard(god: bool) -> ReplyKeyboardMarkup:
    rows = [
        [BTN_ADDWAIFU, BTN_RMWAIFU],
        [BTN_ADDCH, BTN_RMCH],
        [BTN_COINS, BTN_GIVEW],
        [BTN_BAN, BTN_UNBAN],
        [BTN_BROADCAST, BTN_EVENT],
        [BTN_STATS, BTN_SPAWN],
    ]
    if god:
        rows.append([BTN_ADDADMIN, BTN_RMADMIN])
    rows.append([BTN_CLOSE])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context): return
    user = update.effective_user
    god = is_god_admin(user.id)
    role = "👑 God Admin" if god else "🔧 Admin"

    await update.message.reply_text(
        f"🛡️ <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Salom, {role}!\n"
        f"Kerakli bo'limni tanlang 👇",
        parse_mode="HTML",
        reply_markup=build_panel_reply_keyboard(god)
    )


async def handle_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles ReplyKeyboard button taps for admin panel."""
    user = update.effective_user
    text = update.message.text

    if text not in ALL_PANEL_BUTTONS:
        return

    if not await log_db.is_admin(user.id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q.", reply_markup=ReplyKeyboardRemove())
        return

    if text == BTN_CLOSE:
        await update.message.reply_text(
            "✅ Panel yopildi.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    help_text = PANEL_HELP.get(text, "")
    if help_text:
        god = is_god_admin(user.id)
        await update.message.reply_text(
            help_text,
            parse_mode="HTML",
            reply_markup=build_panel_reply_keyboard(god)
        )


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
