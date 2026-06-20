import re
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, filters, CallbackQueryHandler
)
from database import waifus as waifu_db
from database import users as user_db
from database import logs as log_db
from database import groups as grp_db
from database import collections as col_db
from database import titles as title_db
from utils.helpers import get_rarity_emoji, is_god_admin, RARITY_ORDER

# ──────────────────────────────────────
#  PANEL BUTTON LABELS
# ──────────────────────────────────────
BTN_ADDWAIFU  = "➕ Waifu qo'shish"
BTN_RMWAIFU   = "🗑 Waifular ro'yxati"
BTN_ADDCH     = "📢 Kanal qo'shish"
BTN_RMCH      = "❌ Kanal o'chirish"
BTN_COINS     = "💰 Coin berish"
BTN_GIVEW     = "🎴 Waifu berish"
BTN_BAN       = "🚫 Ban"
BTN_UNBAN     = "✅ Unban"
BTN_BROADCAST = "📣 Broadcast"
BTN_EVENT     = "⚡ Event"
BTN_STATS     = "📊 Statistika"
BTN_SPAWN     = "🔧 Spawn"
BTN_TITLE     = "🏅 Unvon berish"
BTN_USERS     = "👥 A'zolar"
BTN_ADDADMIN  = "👑 Admin qo'shish"
BTN_RMADMIN   = "🔴 Admin o'chirish"
BTN_CLOSE     = "🚪 Panelni yopish"

ALL_PANEL_BUTTONS = {
    BTN_ADDWAIFU, BTN_RMWAIFU, BTN_ADDCH, BTN_RMCH,
    BTN_COINS, BTN_GIVEW, BTN_BAN, BTN_UNBAN,
    BTN_BROADCAST, BTN_EVENT, BTN_STATS, BTN_SPAWN,
    BTN_TITLE, BTN_USERS, BTN_ADDADMIN, BTN_RMADMIN, BTN_CLOSE,
}

# Admin state machine keys
ADM_STATE = "adm_state"
ADM_DATA  = "adm_data"

# State values
S_NONE         = None
S_PHOTO        = "addwaifu_photo"
S_NAME         = "addwaifu_name"
S_ANIME        = "addwaifu_anime"
S_BAN          = "ban"
S_UNBAN        = "unban"
S_COINS_UID    = "coins_uid"
S_COINS_AMT    = "coins_amt"
S_GIVEW_UID    = "givew_uid"
S_GIVEW_WID    = "givew_wid"
S_BROADCAST    = "broadcast"
S_ADDADMIN     = "addadmin"
S_RMADMIN      = "rmadmin"
S_ADDCH_ID     = "addch_id"
S_ADDCH_NAME   = "addch_name"
S_TITLE_UID    = "title_uid"
S_TITLE_TXT    = "title_txt"
S_EVENT        = "event"
S_SPAWN_SET    = "spawn_set"


def _panel_kb(god: bool) -> ReplyKeyboardMarkup:
    rows = [
        [BTN_ADDWAIFU, BTN_RMWAIFU],
        [BTN_ADDCH, BTN_RMCH],
        [BTN_COINS, BTN_GIVEW],
        [BTN_BAN, BTN_UNBAN],
        [BTN_BROADCAST, BTN_EVENT],
        [BTN_STATS, BTN_SPAWN],
        [BTN_TITLE, BTN_USERS],
    ]
    if god:
        rows.append([BTN_ADDADMIN, BTN_RMADMIN])
    rows.append([BTN_CLOSE])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _clear_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(ADM_STATE, None)
    context.user_data.pop(ADM_DATA, None)


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
            await update.message.reply_text("❌ Bu faqat God Admin uchun.")
        return False
    return True


# ──────────────────────────────────────
#  PANEL COMMAND
# ──────────────────────────────────────

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    _clear_state(context)
    user = update.effective_user
    god = is_god_admin(user.id)
    role = "👑 God Admin" if god else "🔧 Admin"
    await update.message.reply_text(
        f"🛡️ <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Salom, {role}! Kerakli bo'limni tanlang 👇",
        parse_mode="HTML",
        reply_markup=_panel_kb(god)
    )


# ──────────────────────────────────────
#  WAIFU LIST (inline pagination)
# ──────────────────────────────────────

PAGE_SIZE = 8

async def _show_waifu_list(message, page: int = 0, edit: bool = False):
    total = await waifu_db.count_all_active()
    if total == 0:
        text = "📦 Bazada hali waifu yo'q."
        if edit:
            await message.edit_text(text)
        else:
            await message.reply_text(text)
        return

    items = await waifu_db.get_all_waifus_paginated(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    lines = [f"🎴 <b>WAIFULAR RO'YXATI</b> — jami {total} ta\nSahifa {page+1}/{total_pages}\n━━━━━━━━━━━━━━━━━━━━"]
    for w in items:
        emoji = get_rarity_emoji(w["rarity"])
        lines.append(f"<b>#{w['id']}</b> {emoji} {w['name']} — {w['anime']} [{w['rarity']}]")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # Inline tugmalar
    del_buttons = []
    row = []
    for w in items:
        emoji = get_rarity_emoji(w["rarity"])
        row.append(InlineKeyboardButton(
            f"🗑#{w['id']} {w['name'][:10]}",
            callback_data=f"adm_wdel_{w['id']}"
        ))
        if len(row) == 2:
            del_buttons.append(row)
            row = []
    if row:
        del_buttons.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_wlist_{page-1}"))
    if (page + 1) < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_wlist_{page+1}"))
    if nav:
        del_buttons.append(nav)

    keyboard = InlineKeyboardMarkup(del_buttons)
    text = "\n".join(lines)

    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


# ──────────────────────────────────────
#  USERS LIST
# ──────────────────────────────────────

async def _show_users(message):
    all_ids = await user_db.get_all_users()
    top = await user_db.get_top_users(10, "total_caught")
    lines = [
        f"👥 <b>BOT A'ZOLARI</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Jami: <b>{len(all_ids)}</b> foydalanuvchi",
        "",
        "🏆 <b>Top 10 (waifular bo'yicha):</b>",
    ]
    medals = ["🥇","🥈","🥉"] + [str(i)+"." for i in range(4,11)]
    for i, u in enumerate(top):
        name = u.get("full_name") or u.get("username") or str(u["user_id"])
        lines.append(f"{medals[i]} <code>{u['user_id']}</code> {name} — {u['total_caught']} waifu")
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────
#  STATS
# ──────────────────────────────────────

async def _show_stats(message):
    counts = await waifu_db.count_waifus_by_rarity()
    total = sum(counts.values())
    all_users = await user_db.get_all_users()
    from database.market import count_active_listings
    market_count = await count_active_listings()
    channels = await log_db.get_required_channels_count()
    event = await log_db.get_active_event()

    lines = [
        "📊 <b>BOT STATISTIKASI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 Foydalanuvchilar: <b>{len(all_users)}</b>",
        f"🎴 Jami waifular: <b>{total}</b>",
        f"🛒 Bozorda: <b>{market_count}</b>",
        f"📢 Majburiy kanallar: <b>{channels}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in RARITY_ORDER:
        cnt = counts.get(r, 0)
        emoji = get_rarity_emoji(r)
        lines.append(f"{emoji} {r}: <b>{cnt}</b>")
    if event:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"⚡ Aktiv event: {event['description']}")
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────
#  HANDLE PANEL BUTTON
# ──────────────────────────────────────

async def handle_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if text not in ALL_PANEL_BUTTONS:
        return

    if not await log_db.is_admin(user.id):
        await update.message.reply_text("❌ Ruxsatingiz yo'q.", reply_markup=ReplyKeyboardRemove())
        return

    god = is_god_admin(user.id)
    kb = _panel_kb(god)

    # ── Panelni yopish ──
    if text == BTN_CLOSE:
        _clear_state(context)
        await update.message.reply_text("✅ Panel yopildi.", reply_markup=ReplyKeyboardRemove())
        return

    # ── To'g'ridan ko'rsatadigan bo'limlar ──
    if text == BTN_STATS:
        _clear_state(context)
        await _show_stats(update.message)
        return

    if text == BTN_USERS:
        _clear_state(context)
        await _show_users(update.message)
        return

    if text == BTN_RMWAIFU:
        _clear_state(context)
        await _show_waifu_list(update.message, page=0)
        return

    if text == BTN_SPAWN:
        _clear_state(context)
        chat = update.effective_chat
        if chat.type in ("group", "supergroup"):
            threshold = await grp_db.get_spawn_threshold(chat.id)
            await update.message.reply_text(
                f"🔧 <b>Spawn sozlamalari</b>\n"
                f"Hozirgi chegara: <b>{threshold}</b> xabar\n\n"
                f"O'zgartirish uchun miqsodni kiriting (min 100):",
                parse_mode="HTML", reply_markup=kb
            )
            context.user_data[ADM_STATE] = S_SPAWN_SET
        else:
            await update.message.reply_text(
                "🔧 <b>Spawn sozlamalari</b>\n\n"
                "Guruhda /setspawn [son] buyrug'ini yuboring.\n"
                "Min: 100 xabar.",
                parse_mode="HTML", reply_markup=kb
            )
        return

    if text == BTN_RMCH:
        _clear_state(context)
        channels = await grp_db.get_required_channels()
        if not channels:
            await update.message.reply_text("📋 Majburiy kanallar yo'q.", reply_markup=kb)
            return
        rows = []
        for ch in channels:
            name = ch.get("channel_name") or ch["channel_id"]
            rows.append([InlineKeyboardButton(
                f"❌ {name}", callback_data=f"adm_rmch_{ch['channel_id']}"
            )])
        await update.message.reply_text(
            "📋 O'chirish uchun kanalni tanlang:",
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    # ── Waifu qo'shish (state machine) ──
    if text == BTN_ADDWAIFU:
        _clear_state(context)
        context.user_data[ADM_STATE] = S_PHOTO
        await update.message.reply_text(
            "📸 <b>WAIFU QO'SHISH</b>\n\nWaifu rasmini yuboring:\n\n"
            "Bekor qilish: <code>/cancel</code>",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Ko'p qadam talab qiluvchi amallar ──
    prompts = {
        BTN_BAN:       (S_BAN,       "🚫 <b>Ban</b>\n\nBanlanadigan foydalanuvchi ID sini kiriting:"),
        BTN_UNBAN:     (S_UNBAN,     "✅ <b>Unban</b>\n\nBlokdan chiqariladigan User ID:"),
        BTN_COINS:     (S_COINS_UID, "💰 <b>Coin berish</b>\n\nUser ID kiriting:"),
        BTN_GIVEW:     (S_GIVEW_UID, "🎴 <b>Waifu berish</b>\n\nUser ID kiriting:"),
        BTN_BROADCAST: (S_BROADCAST, "📣 <b>Broadcast</b>\n\nBarcha foydalanuvchilarga yuboriladigan xabarni kiriting:"),
        BTN_ADDADMIN:  (S_ADDADMIN,  "👑 <b>Admin qo'shish</b>\n\nYangi admin User ID sini kiriting:"),
        BTN_RMADMIN:   (S_RMADMIN,   "🔴 <b>Admin o'chirish</b>\n\nAdmin User ID sini kiriting:"),
        BTN_ADDCH:     (S_ADDCH_ID,  "📢 <b>Kanal qo'shish</b>\n\nKanal ID sini kiriting\n(masalan: @mychannel):"),
        BTN_TITLE:     (S_TITLE_UID, "🏅 <b>Unvon berish</b>\n\nFoydalanuvchi ID sini kiriting:"),
        BTN_EVENT:     (S_EVENT,     "⚡ <b>Event</b>\n\nKomanda kiriting:\n• <code>start [tur] [x] [soat] [tavsif]</code>\n• <code>stop</code>\n\nTurlar: double_spawn, double_coin, anime, seasonal"),
    }

    if text in prompts:
        state, prompt = prompts[text]
        _clear_state(context)
        context.user_data[ADM_STATE] = state
        await update.message.reply_text(prompt, parse_mode="HTML", reply_markup=kb)


# ──────────────────────────────────────
#  HANDLE ADMIN TEXT INPUT (state machine)
# ──────────────────────────────────────

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get(ADM_STATE)
    if state is None:
        return
    if not await log_db.is_admin(user.id):
        _clear_state(context)
        return

    god = is_god_admin(user.id)
    kb = _panel_kb(god)
    text = update.message.text.strip()

    # ── Bekor qilish ──
    if text.lower() in ("/cancel", "bekor"):
        _clear_state(context)
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=kb)
        return

    # ── Waifu qo'shish: ism ──
    if state == S_NAME:
        if len(text) < 2:
            await update.message.reply_text("❌ Ism juda qisqa. Qaytadan kiriting:")
            return
        context.user_data[ADM_DATA]["name"] = text
        context.user_data[ADM_STATE] = S_ANIME
        await update.message.reply_text("🎌 Anime nomini kiriting:", reply_markup=kb)
        return

    # ── Waifu qo'shish: anime ──
    if state == S_ANIME:
        context.user_data[ADM_DATA]["anime"] = text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"rarity_{r}")]
            for r in RARITY_ORDER
        ])
        context.user_data[ADM_STATE] = S_NONE
        await update.message.reply_text("⭐ Darajani tanlang:", reply_markup=keyboard)
        return

    # ── Ban ──
    if state == S_BAN:
        try:
            uid = int(text.split()[0])
            reason = " ".join(text.split()[1:]) or "Sabab ko'rsatilmagan"
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        await user_db.ban_user(uid, reason)
        await log_db.add_log("ban", user_id=user.id, details=f"banned={uid} reason={reason}")
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code> bloklandi!\nSabab: {reason}", parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Unban ──
    if state == S_UNBAN:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        await user_db.unban_user(uid)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi!", parse_mode="HTML", reply_markup=kb)
        return

    # ── Coin berish: user ID ──
    if state == S_COINS_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_COINS_AMT
        await update.message.reply_text(f"💰 <code>{uid}</code> ga necha coin berish?", parse_mode="HTML", reply_markup=kb)
        return

    # ── Coin berish: miqdor ──
    if state == S_COINS_AMT:
        try:
            amount = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam kiriting:")
            return
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        if not uid:
            _clear_state(context)
            return
        await user_db.add_coins(uid, amount)
        await log_db.add_log("give_coins", user_id=user.id, details=f"to={uid} amount={amount}")
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <code>{uid}</code> ga <b>{amount:,}</b> coin berildi!", parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Waifu berish: user ID ──
    if state == S_GIVEW_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_GIVEW_WID
        await update.message.reply_text(
            f"🎴 <code>{uid}</code> ga qaysi waifu?\n\nWaifu ID sini kiriting (#raqam):",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Waifu berish: waifu ID ──
    if state == S_GIVEW_WID:
        wid = text.lstrip("#").strip()
        waifu = await waifu_db.get_waifu(wid)
        if not waifu:
            await update.message.reply_text(f"❌ #{wid} waifusi topilmadi. Qaytadan kiriting:")
            return
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        await col_db.add_to_collection(uid, waifu["waifu_id"])
        emoji = get_rarity_emoji(waifu["rarity"])
        _clear_state(context)
        await update.message.reply_text(
            f"✅ {emoji} <b>{waifu['name']}</b> → <code>{uid}</code> ga berildi!",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Broadcast ──
    if state == S_BROADCAST:
        if not is_god_admin(user.id):
            _clear_state(context)
            await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
            return
        user_ids = await user_db.get_all_users()
        await update.message.reply_text(f"📢 {len(user_ids)} ta foydalanuvchiga yuborilmoqda...", reply_markup=kb)
        sent = failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(uid, f"📢 <b>E'lon:</b>\n\n{text}", parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        _clear_state(context)
        await update.message.reply_text(
            f"✅ <b>Broadcast tugadi!</b>\nYuborildi: {sent} | Muvaffaqiyatsiz: {failed}",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Admin qo'shish ──
    if state == S_ADDADMIN:
        if not is_god_admin(user.id):
            _clear_state(context)
            return
        try:
            parts = text.split()
            uid = int(parts[0])
            username = parts[1].lstrip("@") if len(parts) > 1 else ""
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        await log_db.add_admin(uid, username, user.id)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> admin qilindi!", parse_mode="HTML", reply_markup=kb)
        return

    # ── Admin o'chirish ──
    if state == S_RMADMIN:
        if not is_god_admin(user.id):
            _clear_state(context)
            return
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam kiriting:")
            return
        await log_db.remove_admin(uid)
        _clear_state(context)
        await update.message.reply_text(f"✅ <code>{uid}</code> adminlikdan olib tashlandi!", parse_mode="HTML", reply_markup=kb)
        return

    # ── Kanal qo'shish: ID ──
    if state == S_ADDCH_ID:
        if not is_god_admin(user.id):
            _clear_state(context)
            return
        try:
            await context.bot.get_chat(text)
        except Exception as e:
            await update.message.reply_text(f"❌ Kanal topilmadi: {e}\nQaytadan kiriting:")
            return
        context.user_data[ADM_DATA] = {"ch_id": text}
        context.user_data[ADM_STATE] = S_ADDCH_NAME
        await update.message.reply_text(f"📢 Kanal nomi kiriting:", reply_markup=kb)
        return

    # ── Kanal qo'shish: nom ──
    if state == S_ADDCH_NAME:
        if not is_god_admin(user.id):
            _clear_state(context)
            return
        ch_id = context.user_data.get(ADM_DATA, {}).get("ch_id")
        if not ch_id:
            _clear_state(context)
            return
        await grp_db.add_required_channel(ch_id, text, "channel", user.id)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ Majburiy kanal qo'shildi!\n"
            f"🆔 <code>{ch_id}</code>\n📛 {text}",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Unvon: user ID ──
    if state == S_TITLE_UID:
        try:
            uid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam (User ID) kiriting:")
            return
        context.user_data[ADM_DATA] = {"uid": uid}
        context.user_data[ADM_STATE] = S_TITLE_TXT
        await update.message.reply_text(
            f"🏅 <code>{uid}</code> ga qanday unvon berish?\n\n"
            f"Unvon matnini kiriting (emoji ham qo'shishingiz mumkin):",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Unvon: matn ──
    if state == S_TITLE_TXT:
        uid = context.user_data.get(ADM_DATA, {}).get("uid")
        if not uid:
            _clear_state(context)
            return
        await title_db.set_title(uid, text, user.id)
        _clear_state(context)
        await update.message.reply_text(
            f"✅ Unvon berildi!\n👤 <code>{uid}</code>\n🏅 <b>{text}</b>",
            parse_mode="HTML", reply_markup=kb
        )
        return

    # ── Event ──
    if state == S_EVENT:
        args = text.split()
        if not args:
            return
        if args[0] == "stop":
            await log_db.stop_event()
            _clear_state(context)
            await update.message.reply_text("✅ Event to'xtatildi.", reply_markup=kb)
            return
        if args[0] == "start" and len(args) >= 3:
            event_type = args[1]
            try:
                multiplier = float(args[2])
                hours = int(args[3]) if len(args) > 3 else 2
            except ValueError:
                await update.message.reply_text("❌ Format: start [tur] [x] [soat] [tavsif]")
                return
            description = " ".join(args[4:]) if len(args) > 4 else event_type
            await log_db.start_event(event_type, multiplier, description, user.id, hours)
            _clear_state(context)
            await update.message.reply_text(
                f"⚡ <b>EVENT BOSHLANDI!</b>\nTur: {event_type} | x{multiplier} | {hours} soat",
                parse_mode="HTML", reply_markup=kb
            )
            return
        await update.message.reply_text("❌ Noto'g'ri format. start [tur] [x] [soat] yoki stop")
        return

    # ── Spawn chegarasi ──
    if state == S_SPAWN_SET:
        try:
            val = int(text)
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam kiriting:")
            return
        if val < 100:
            await update.message.reply_text("❌ Minimum 100. Qaytadan:")
            return
        chat = update.effective_chat
        if chat.type in ("group", "supergroup"):
            await grp_db.set_spawn_threshold(chat.id, val)
            _clear_state(context)
            await update.message.reply_text(
                f"✅ Spawn chegarasi <b>{val}</b> ga o'rnatildi!", parse_mode="HTML", reply_markup=kb
            )
        else:
            _clear_state(context)
            await update.message.reply_text(
                "❌ Spawn faqat guruhlarda ishlaydi. Bu buyruqni guruhda ishlating.", reply_markup=kb
            )
        return


# ──────────────────────────────────────
#  HANDLE ADMIN PHOTO (addwaifu flow)
# ──────────────────────────────────────

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get(ADM_STATE)
    if state != S_PHOTO:
        return
    if not await log_db.is_admin(user.id):
        _clear_state(context)
        return

    if not update.message.photo:
        await update.message.reply_text("❌ Rasm yuboring.")
        return

    file_id = update.message.photo[-1].file_id
    context.user_data[ADM_DATA] = {"file_id": file_id}
    context.user_data[ADM_STATE] = S_NAME

    god = is_god_admin(user.id)
    await update.message.reply_text(
        "✅ Rasm qabul qilindi!\n\n📝 Waifu ismini kiriting:",
        reply_markup=_panel_kb(god)
    )


# ──────────────────────────────────────
#  RARITY CALLBACK (addwaifu tugallash)
# ──────────────────────────────────────

async def received_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    rarity = query.data.replace("rarity_", "")

    data = context.user_data.get(ADM_DATA) or {}
    if not data.get("file_id") or not data.get("name") or not data.get("anime"):
        await query.edit_message_text("❌ Ma'lumot topilmadi. Panel dan qayta boshlang.")
        return

    success, waifu_id = await waifu_db.add_waifu(
        name=data["name"],
        anime=data["anime"],
        rarity=rarity,
        file_id=data["file_id"],
        added_by=user.id
    )
    _clear_state(context)

    if success:
        emoji = get_rarity_emoji(rarity)
        await query.edit_message_text(
            f"✅ <b>WAIFU QO'SHILDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>#{waifu_id}</code>\n"
            f"📛 Ism: <b>{data['name']}</b>\n"
            f"🎌 Anime: <b>{data['anime']}</b>\n"
            f"{emoji} Daraja: <b>{rarity}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")


# ──────────────────────────────────────
#  ADMIN INLINE CALLBACKS  (adm_*)
# ──────────────────────────────────────

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if not await log_db.is_admin(user.id):
        await query.answer("❌ Ruxsatingiz yo'q.", show_alert=True)
        return

    # Waifu list pagination
    if data.startswith("adm_wlist_"):
        try:
            page = int(data[len("adm_wlist_"):])
        except ValueError:
            return
        await _show_waifu_list(query.message, page=page, edit=True)
        return

    # Waifu delete confirm
    if data.startswith("adm_wdel_") and not data.startswith("adm_wdel_ok_") and not data.startswith("adm_wdel_cancel"):
        try:
            db_id = int(data[len("adm_wdel_"):])
        except ValueError:
            return
        waifu = await waifu_db.get_waifu_by_db_id(db_id)
        if not waifu:
            await query.answer("Waifu topilmadi!", show_alert=True)
            return
        emoji = get_rarity_emoji(waifu["rarity"])
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"adm_wdel_ok_{db_id}"),
            InlineKeyboardButton("❌ Bekor", callback_data="adm_wdel_cancel"),
        ]])
        await query.message.reply_text(
            f"⚠️ <b>Haqiqatan o'chirasizmi?</b>\n\n"
            f"{emoji} <b>{waifu['name']}</b> — {waifu['anime']}\n"
            f"Daraja: {waifu['rarity']}\n"
            f"🆔 #{waifu['id']}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # Waifu delete confirmed
    if data.startswith("adm_wdel_ok_"):
        try:
            db_id = int(data[len("adm_wdel_ok_"):])
        except ValueError:
            return
        waifu = await waifu_db.get_waifu_by_db_id(db_id)
        if not waifu:
            await query.edit_message_text("❌ Waifu allaqachon o'chirilgan.")
            return
        await waifu_db.remove_waifu_by_db_id(db_id)
        await query.edit_message_text(
            f"✅ <b>{waifu['name']}</b> (#{db_id}) o'chirildi!", parse_mode="HTML"
        )
        return

    # Waifu delete cancel
    if data == "adm_wdel_cancel":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    # Remove channel
    if data.startswith("adm_rmch_"):
        if not is_god_admin(user.id):
            await query.answer("❌ Faqat God Admin.", show_alert=True)
            return
        ch_id = data[len("adm_rmch_"):]
        await grp_db.remove_required_channel(ch_id)
        await query.edit_message_text(f"✅ <code>{ch_id}</code> kanal o'chirildi.", parse_mode="HTML")
        return


# ──────────────────────────────────────
#  STANDALONE ADMIN COMMANDS
# ──────────────────────────────────────

async def cmd_removewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /removewaifu [#id yoki waifu_id]")
        return
    wid = context.args[0].lstrip("#")
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
        # Try by DB id
        try:
            waifu = await waifu_db.get_waifu_by_db_id(int(wid))
        except ValueError:
            pass
    if not waifu:
        await update.message.reply_text(f"❌ #{wid} topilmadi.")
        return
    await waifu_db.remove_waifu(waifu["waifu_id"])
    await update.message.reply_text(
        f"✅ <b>{waifu['name']}</b> (#{waifu['id']}) o'chirildi.", parse_mode="HTML"
    )


async def cmd_spawn_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
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
    if not await require_admin(update, context):
        return
    if not context.args:
        current = await grp_db.get_spawn_threshold(chat.id)
        await update.message.reply_text(
            f"📊 Hozirgi spawn chegarasi: <b>{current}</b>\nFormat: /setspawn [son]",
            parse_mode="HTML"
        )
        return
    try:
        threshold = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Son kiriting.")
        return
    if threshold < 100:
        await update.message.reply_text("❌ Minimum 100.")
        return
    await grp_db.set_spawn_threshold(chat.id, threshold)
    await update.message.reply_text(
        f"✅ Spawn chegarasi <b>{threshold}</b> ga o'rnatildi.", parse_mode="HTML"
    )


async def cmd_addgroup_bypass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
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
            "INSERT OR REPLACE INTO groups (group_id, is_approved, skip_member_check) VALUES (?,1,1)", (gid,)
        )
        await db.commit()
    await update.message.reply_text(f"✅ Guruh <code>{gid}</code> qo'shildi.", parse_mode="HTML")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
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
    if not await require_god(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /addadmin [user_id] [username]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    username = context.args[1].lstrip("@") if len(context.args) > 1 else ""
    await log_db.add_admin(uid, username, update.effective_user.id)
    await update.message.reply_text(f"✅ {uid} admin qilindi.")


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /removeadmin [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    await log_db.remove_admin(uid)
    await update.message.reply_text(f"✅ {uid} adminlikdan olib tashlandi.")


async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /banuser [user_id] [sabab]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Sabab ko'rsatilmagan"
    await user_db.ban_user(uid, reason)
    await update.message.reply_text(f"✅ {uid} bloklandi.")


async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /unbanuser [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    await user_db.unban_user(uid)
    await update.message.reply_text(f"✅ {uid} blokdan chiqarildi.")


async def cmd_givecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
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
    await update.message.reply_text(f"✅ {uid} ga {amount:,} coin berildi.")


async def cmd_givewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /givewaifu [user_id] [waifu_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    wid = context.args[1].lstrip("#")
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
        await update.message.reply_text(f"❌ #{wid} topilmadi.")
        return
    await col_db.add_to_collection(uid, waifu["waifu_id"])
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_text(
        f"✅ {emoji} <b>{waifu['name']}</b> → {uid} ga berildi.", parse_mode="HTML"
    )


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "📋 Event:\n/event start [tur] [x] [soat] [tavsif]\n/event stop"
        )
        return
    if args[0] == "start":
        if len(args) < 3:
            await update.message.reply_text("❌ Format: /event start [tur] [x] [soat]")
            return
        try:
            multiplier = float(args[2])
            hours = int(args[3]) if len(args) > 3 else 2
        except ValueError:
            await update.message.reply_text("❌ Multiplikator raqam.")
            return
        description = " ".join(args[4:]) if len(args) > 4 else args[1]
        await log_db.start_event(args[1], multiplier, description, update.effective_user.id, hours)
        await update.message.reply_text(
            f"⚡ Event boshlandi! {args[1]} x{multiplier} {hours}s", parse_mode="HTML"
        )
    elif args[0] == "stop":
        await log_db.stop_event()
        await update.message.reply_text("✅ Event to'xtatildi.")


async def cmd_approvegroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /approvegroup [group_id]")
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Group ID raqam.")
        return
    await grp_db.approve_group(gid, update.effective_user.id)
    await update.message.reply_text(f"✅ Guruh {gid} tasdiqlandi.")


async def cmd_denygroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /denygroup [group_id]")
        return
    try:
        gid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Group ID raqam.")
        return
    await grp_db.deny_group(gid)
    await update.message.reply_text(f"✅ Guruh {gid} rad etildi.")


async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /addchannel [channel_id] [nomi]")
        return
    channel_id = context.args[0]
    name = " ".join(context.args[1:])
    try:
        await context.bot.get_chat(channel_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Kanal topilmadi: {e}")
        return
    await grp_db.add_required_channel(channel_id, name, "channel", update.effective_user.id)
    await update.message.reply_text(
        f"✅ Majburiy kanal: <b>{name}</b>\n🆔 <code>{channel_id}</code>", parse_mode="HTML"
    )


async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
        return
    if not context.args:
        channels = await grp_db.get_required_channels()
        if not channels:
            await update.message.reply_text("📋 Kanallar yo'q.")
            return
        lines = ["📋 <b>Majburiy kanallar:</b>\n"]
        for ch in channels:
            lines.append(f"• <code>{ch['channel_id']}</code> — {ch.get('channel_name','')}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return
    await grp_db.remove_required_channel(context.args[0])
    await update.message.reply_text(f"✅ <code>{context.args[0]}</code> o'chirildi.", parse_mode="HTML")


async def cmd_settitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /settitle [user_id] [unvon]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    title_text = " ".join(context.args[1:]).strip()
    await title_db.set_title(uid, title_text, update.effective_user.id)
    await update.message.reply_text(
        f"✅ Unvon berildi!\n👤 <code>{uid}</code>\n🏅 <b>{title_text}</b>", parse_mode="HTML"
    )


async def cmd_removetitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("❌ Format: /removetitle [user_id]")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ User ID raqam.")
        return
    await title_db.remove_title(uid)
    await update.message.reply_text(f"✅ {uid} ning unvoni o'chirildi.")


async def cmd_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    all_titles = await title_db.get_all_titles()
    if not all_titles:
        await update.message.reply_text("📋 Hech kimga unvon berilmagan.")
        return
    lines = ["🏅 <b>UNVONLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for t in all_titles:
        name = t.get("full_name") or t.get("username") or str(t["user_id"])
        lines.append(f"• <code>{t['user_id']}</code> {name}\n  🏅 <b>{t['title']}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
