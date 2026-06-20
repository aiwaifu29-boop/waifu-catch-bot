import re
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import ContextTypes
from database import waifus as waifu_db
from database import users as user_db
from database import logs as log_db
from database import groups as grp_db
from database import collections as col_db
from database import titles as title_db
from utils.helpers import get_rarity_emoji, is_god_admin, RARITY_ORDER

# ──────────────────────────────────────
#  PANEL TUGMALARI
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
BTN_ADDSUBADM = "🟡 Sub-Admin qo'shish"
BTN_ADDGROUP  = "🔓 Guruh qo'shish"
BTN_CLOSE     = "🚪 Panelni yopish"

# Sub-admin faqat ko'ra oladigan tugmalar
SUB_ADMIN_BUTTONS = {BTN_ADDWAIFU, BTN_RMWAIFU, BTN_CLOSE}

ALL_PANEL_BUTTONS = {
    BTN_ADDWAIFU, BTN_RMWAIFU, BTN_ADDCH, BTN_RMCH,
    BTN_COINS, BTN_GIVEW, BTN_BAN, BTN_UNBAN,
    BTN_BROADCAST, BTN_EVENT, BTN_STATS, BTN_SPAWN,
    BTN_TITLE, BTN_USERS, BTN_ADDADMIN, BTN_RMADMIN,
    BTN_ADDSUBADM, BTN_ADDGROUP, BTN_CLOSE,
}

# Sub-admin uchun yopiq raritlar
SUB_ADMIN_BLOCKED_RARITY = {"Mythic", "Legendary", "Premium", "Exclusive"}

# Admin state machine
ADM_STATE = "adm_state"
ADM_DATA  = "adm_data"

S_NONE       = None
S_PHOTO      = "addwaifu_photo"
S_NAME       = "addwaifu_name"
S_ANIME      = "addwaifu_anime"
S_BAN        = "ban"
S_UNBAN      = "unban"
S_COINS_UID  = "coins_uid"
S_COINS_AMT  = "coins_amt"
S_GIVEW_UID  = "givew_uid"
S_GIVEW_WID  = "givew_wid"
S_BROADCAST  = "broadcast"
S_ADDADMIN   = "addadmin"
S_ADDSUBADM  = "addsubadm"
S_RMADMIN    = "rmadmin"
S_ADDCH_ID   = "addch_id"
S_ADDCH_NAME = "addch_name"
S_TITLE_UID  = "title_uid"
S_TITLE_TXT  = "title_txt"
S_EVENT      = "event"
S_SPAWN_SET  = "spawn_set"
S_ADDGROUP   = "addgroup_bypass"

PAGE_SIZE = 8


def _panel_kb(role: str) -> ReplyKeyboardMarkup:
    if role == "sub":
      rows = [
          [BTN_ADDWAIFU],
          [BTN_RMWAIFU],
          [BTN_CLOSE],
      ]
    elif role in ("god",):
      rows = [
          [BTN_ADDWAIFU, BTN_RMWAIFU],
          [BTN_ADDCH, BTN_RMCH],
          [BTN_COINS, BTN_GIVEW],
          [BTN_BAN, BTN_UNBAN],
          [BTN_BROADCAST, BTN_EVENT],
          [BTN_STATS, BTN_SPAWN],
          [BTN_TITLE, BTN_USERS],
          [BTN_ADDADMIN, BTN_ADDSUBADM],
          [BTN_RMADMIN, BTN_ADDGROUP],
          [BTN_CLOSE],
      ]
    else:  # admin
      rows = [
          [BTN_ADDWAIFU, BTN_RMWAIFU],
          [BTN_COINS, BTN_GIVEW],
          [BTN_BAN, BTN_UNBAN],
          [BTN_BROADCAST, BTN_EVENT],
          [BTN_STATS, BTN_SPAWN],
          [BTN_TITLE, BTN_USERS],
          [BTN_CLOSE],
      ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def _clear_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop(ADM_STATE, None)
    context.user_data.pop(ADM_DATA, None)


async def _get_role(user_id: int) -> str:
    """god | admin | sub | None"""
    role = await log_db.get_admin_role(user_id)
    return role or ""


async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not await log_db.is_admin(user.id):
      if update.message:
          await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return False
    return True


async def require_full_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sub-admin uchun ruxsat bermaydi"""
    user = update.effective_user
    if not await log_db.is_full_admin(user.id):
      if update.message:
          await update.message.reply_text("❌ Bu amal faqat to'liq admin uchun.")
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
#  PANEL BUYRUG'I
# ──────────────────────────────────────

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
      return
    _clear_state(context)
    user = update.effective_user
    role = await _get_role(user.id)
    role_label = {"god": "👑 God Admin", "admin": "🔧 Admin", "sub": "🟡 Sub-Admin"}.get(role, "Admin")

    await update.message.reply_text(
      f"🛡️ <b>ADMIN PANEL</b>\n"
      f"━━━━━━━━━━━━━━━━━━━━\n"
      f"Salom, <b>{role_label}</b>!\n"
      f"Kerakli bo'limni tanlang 👇",
      parse_mode="HTML",
      reply_markup=_panel_kb(role)
    )


# ──────────────────────────────────────
#  WAIFU RO'YXATI (inline pagination)
# ──────────────────────────────────────

async def _show_waifu_list(message, page: int = 0, edit: bool = False, owner_id: int = None):
    """owner_id berilsa — faqat o'sha admin qo'shgan waifular"""
    if owner_id:
        total = await waifu_db.count_waifus_by_admin(owner_id)
        items = await waifu_db.get_waifus_by_admin(owner_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    else:
      total = await waifu_db.count_all_active()
      items = await waifu_db.get_all_waifus_paginated(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    if total == 0:
      text = "📦 Hali waifu qo'shilmagan." if owner_id else "📦 Bazada hali waifu yo'q."
      if edit:
          try:
              await message.edit_text(text)
          except Exception:
              pass
      else:
          await message.reply_text(text)
      return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    scope = "Mening waifularim" if owner_id else "Jami waifular"
    lines = [
      f"🎴 <b>{scope}</b> — {total} ta\n📄 Sahifa {page+1}/{total_pages}\n━━━━━━━━━━━━━━━━━━━━"
    ]
    for w in items:
      emoji = get_rarity_emoji(w["rarity"])
      lines.append(f"<b>#{w['id']}</b> {emoji} {w['name']} — <i>{w['anime']}</i> [{w['rarity']}]")
    lines.append("━━━━━━━━━━━━━━━━━━━━\n🗑 O'chirish uchun tugmani bosing:")

    del_buttons = []
    row = []
    for w in items:
      emoji = get_rarity_emoji(w["rarity"])
      row.append(InlineKeyboardButton(
          f"🗑#{w['id']} {w['name'][:9]}",
          callback_data=f"adm_wdel_{w['id']}"
      ))
      if len(row) == 2:
          del_buttons.append(row)
          row = []
    if row:
      del_buttons.append(row)

    nav = []
    page_key = f"adm_wlist_sub_{page}" if owner_id else f"adm_wlist_{page}"
    prev_key = f"adm_wlist_sub_{page-1}" if owner_id else f"adm_wlist_{page-1}"
    next_key = f"adm_wlist_sub_{page+1}" if owner_id else f"adm_wlist_{page+1}"

    if page > 0:
      nav.append(InlineKeyboardButton("⬅️", callback_data=prev_key))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="adm_noop"))
    if (page + 1) < total_pages:
      nav.append(InlineKeyboardButton("➡️", callback_data=next_key))
    del_buttons.append(nav)

    keyboard = InlineKeyboardMarkup(del_buttons)
    text = "\n".join(lines)

    if edit:
      try:
          await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
      except Exception:
          pass
    else:
      await message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


# ──────────────────────────────────────
#  A'ZOLAR RO'YXATI
# ──────────────────────────────────────

async def _show_users(message):
    all_ids = await user_db.get_all_users()
    top = await user_db.get_top_users(10, "total_caught")
    admins = await log_db.get_admins()

    role_mark = {"god": "👑", "admin": "🔧", "sub": "🟡"}

    lines = [
      "👥 <b>BOT A'ZOLARI</b>",
      "━━━━━━━━━━━━━━━━━━━━",
      f"Jami: <b>{len(all_ids)}</b> foydalanuvchi",
      "",
      "🛡️ <b>Adminlar:</b>",
    ]
    for a in admins:
      r = a.get("role") or "admin"
      mark = role_mark.get(r, "🔧")
      uname = f"@{a['username']}" if a.get("username") else ""
      lines.append(f"{mark} <code>{a['user_id']}</code> {uname}")

    lines += ["", "🏆 <b>Top 10 (waifular):</b>"]
    medals = ["🥇","🥈","🥉"] + [f"{i}." for i in range(4,11)]
    for i, u in enumerate(top):
      name = u.get("full_name") or u.get("username") or str(u["user_id"])
      lines.append(f"{medals[i]} <code>{u['user_id']}</code> {name} — {u['total_caught']} waifu")
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────
#  STATISTIKA
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
      lines += [
          "━━━━━━━━━━━━━━━━━━━━",
          f"⚡ Aktiv event: <b>{event['event_type']}</b> x{event['multiplier']}",
          f"📋 {event.get('description','')}",
      ]
    await message.reply_text("\n".join(lines), parse_mode="HTML")


# ──────────────────────────────────────
#  PANEL TUGMA HANDLER
# ──────────────────────────────────────

async def handle_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if text not in ALL_PANEL_BUTTONS:
      return

    if not await log_db.is_admin(user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.", reply_markup=ReplyKeyboardRemove())
      return

    role = await _get_role(user.id)
    kb = _panel_kb(role)
    is_sub = (role == "sub")

    # Waifu qo'shish jarayonida panel tugmalarini bloklash
    current_state = context.user_data.get(ADM_STATE)
    if current_state in (S_PHOTO, S_NAME, S_ANIME):
        state_hints = {
            S_PHOTO: '📸 Waifu rasmini yuboring (yoki /cancel deb yozing).',
            S_NAME:  '📝 Waifu ismini yozing (yoki /cancel).',
            S_ANIME: '🎌 Anime nomini yozing (yoki /cancel).',
        }
        await update.message.reply_text(state_hints[current_state], reply_markup=kb)
        return

    # ── Sub-admin faqat o'z tugmalarini ── 
    if is_sub and text not in SUB_ADMIN_BUTTONS:
      await update.message.reply_text(
          "🚫 Sub-admin ushbu amalni bajara olmaydi.", reply_markup=kb
      )
      return

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
      # Sub-admin faqat o'ziniki ko'radi
      owner = user.id if is_sub else None
      await _show_waifu_list(update.message, page=0, owner_id=owner)
      return

    if text == BTN_SPAWN:
      _clear_state(context)
      await update.message.reply_text(
          "🔧 <b>Spawn</b>\nGuruhda: /setspawn [son]\nYoki miqsodni kiriting:",
          parse_mode="HTML", reply_markup=kb
      )
      context.user_data[ADM_STATE] = S_SPAWN_SET
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
          rows.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"adm_rmch_{ch['channel_id']}")])
      await update.message.reply_text("📋 O'chirish uchun kanalni tanlang:",
                                      reply_markup=InlineKeyboardMarkup(rows))
      return

    # ── Waifu qo'shish ──
    if text == BTN_ADDWAIFU:
      _clear_state(context)
      context.user_data[ADM_STATE] = S_PHOTO
      await update.message.reply_text(
          "📸 <b>WAIFU QO'SHISH</b>\n\n"
          "Waifu rasmini yuboring:\n\n"
          "Bekor qilish: /cancel",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Guruh qo'shish bypass (faqat god admin) ──
    if text == BTN_ADDGROUP:
      if not is_god_admin(user.id):
          await update.message.reply_text("❌ Faqat God Admin.", reply_markup=kb)
          return
      _clear_state(context)
      context.user_data[ADM_STATE] = S_ADDGROUP
      await update.message.reply_text(
          "🔓 <b>Guruh qo'shish (Bypass)</b>\n\n"
          "20 ta a'zo cheklovini chetlab o'tish uchun quyidagilardan birini yuboring:\n\n"
          "\u2022 <code>-1001234567890</code> \u2014 to'g'ridan guruh ID\n"
          "\u2022 <code>@groupusername</code> \u2014 ommaviy guruh\n"
          "\u2022 <code>https://t.me/groupname</code> \u2014 havola\n\n"
          "📌 Private guruh uchun guruh ID kerak.",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Ko'p qadam talab qiladigan amallar ──
    prompts = {
      BTN_BAN:       (S_BAN,       "🚫 <b>Ban</b>\n\nUser ID va sabab kiriting:\n<code>12345678 spam</code>"),
      BTN_UNBAN:     (S_UNBAN,     "✅ <b>Unban</b>\n\nUser ID kiriting:"),
      BTN_COINS:     (S_COINS_UID, "💰 <b>Coin berish</b>\n\nUser ID kiriting:"),
      BTN_GIVEW:     (S_GIVEW_UID, "🎴 <b>Waifu berish</b>\n\nUser ID kiriting:"),
      BTN_BROADCAST: (S_BROADCAST, "📣 <b>Broadcast</b>\n\nBarcha foydalanuvchilarga xabar:"),
      BTN_ADDADMIN:  (S_ADDADMIN,  "👑 <b>Admin qo'shish</b>\n\nUser ID kiriting:"),
      BTN_ADDSUBADM: (S_ADDSUBADM, "🟡 <b>Sub-Admin qo'shish</b>\n\nUser ID kiriting:"),
      BTN_RMADMIN:   (S_RMADMIN,   "🔴 <b>Admin o'chirish</b>\n\nUser ID kiriting:"),
      BTN_ADDCH:     (S_ADDCH_ID,  "📢 <b>Kanal qo'shish</b>\n\nKanal ID kiriting (@mychannel):"),
      BTN_TITLE:     (S_TITLE_UID, "🏅 <b>Unvon berish</b>\n\nUser ID kiriting:"),
      BTN_EVENT:     (S_EVENT,
                      "⚡ <b>Event</b>\n\nKomanda:\n"
                      "• <code>start double_spawn 2 3 Ikki marta</code>\n"
                      "• <code>start double_coin 2 2</code>\n"
                      "• <code>stop</code>\n\n"
                      "Turlar: double_spawn, double_coin, anime, seasonal"),
    }

    if text in prompts:
      state, prompt = prompts[text]
      _clear_state(context)
      context.user_data[ADM_STATE] = state
      await update.message.reply_text(prompt, parse_mode="HTML", reply_markup=kb)


# ──────────────────────────────────────
#  ADMIN MATN KIRITISH (state machine)
# ──────────────────────────────────────

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get(ADM_STATE)
    if state is None:
      return
    if not await log_db.is_admin(user.id):
      _clear_state(context)
      return

    role = await _get_role(user.id)
    kb = _panel_kb(role)
    # Rasm yoki boshqa media kelsa — text handler ishlamaydi
    if not update.message.text:
        return
    text = update.message.text.strip()

    if text.lower() in ("/cancel", "bekor", "❌"):
      _clear_state(context)
      await update.message.reply_text("❌ Bekor qilindi.", reply_markup=kb)
      return

    # ── Waifu ism ──
    if state == S_NAME:
      if len(text) < 2:
          await update.message.reply_text("❌ Juda qisqa. Qaytadan:")
          return
      context.user_data[ADM_DATA]["name"] = text
      context.user_data[ADM_STATE] = S_ANIME
      await update.message.reply_text("🎌 Anime nomini kiriting:", reply_markup=kb)
      return

    # ── Waifu anime ──
    if state == S_ANIME:
      context.user_data[ADM_DATA]["anime"] = text
      is_sub = (role == "sub")
      # Sub-admin uchun Mythic/Legendary ko'rsatilmaydi
      available_rarities = [r for r in RARITY_ORDER if not (is_sub and r in SUB_ADMIN_BLOCKED_RARITY)]
      keyboard = InlineKeyboardMarkup([
          [InlineKeyboardButton(f"{get_rarity_emoji(r)} {r}", callback_data=f"rarity_{r}")]
          for r in available_rarities
      ])
      context.user_data[ADM_STATE] = S_NONE
      await update.message.reply_text("⭐ Darajani tanlang:", reply_markup=keyboard)
      return

    # ── Ban ──
    if state == S_BAN:
      parts = text.split(None, 1)
      try:
          uid = int(parts[0])
      except ValueError:
          await update.message.reply_text("❌ Avval User ID, keyin sabab kiriting:")
          return
      reason = parts[1] if len(parts) > 1 else "Sabab ko'rsatilmagan"
      await user_db.ban_user(uid, reason)
      from middlewares.ban_middleware import clear_ban_cache
      clear_ban_cache(uid)
      await log_db.add_log("ban", user_id=user.id, details=f"banned={uid} reason={reason}")
      _clear_state(context)
      await update.message.reply_text(
          f"✅ <code>{uid}</code> bloklandi!\n📋 Sabab: {reason}",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Unban ──
    if state == S_UNBAN:
      try:
          uid = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      await user_db.unban_user(uid)
      from middlewares.ban_middleware import clear_ban_cache
      clear_ban_cache(uid)
      _clear_state(context)
      await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi!", parse_mode="HTML", reply_markup=kb)
      return

    # ── Coin: User ID ──
    if state == S_COINS_UID:
      try:
          uid = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      context.user_data[ADM_DATA] = {"uid": uid}
      context.user_data[ADM_STATE] = S_COINS_AMT
      u = await user_db.get_user(uid)
      current = u["coins"] if u else "?"
      await update.message.reply_text(
          f"💰 <code>{uid}</code>\nHozirgi coin: <b>{current}</b>\n\nNecha coin berish?",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Coin: miqdor ──
    if state == S_COINS_AMT:
      try:
          amount = int(text.replace(",", "").replace(" ", ""))
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      uid = context.user_data.get(ADM_DATA, {}).get("uid")
      if not uid:
          _clear_state(context)
          return
      await user_db.add_coins(uid, amount)
      await log_db.add_log("give_coins", user_id=user.id, details=f"to={uid} amount={amount}")
      _clear_state(context)
      await update.message.reply_text(
          f"✅ <code>{uid}</code> ga <b>{amount:,}</b> coin berildi!",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Waifu berish: User ID ──
    if state == S_GIVEW_UID:
      try:
          uid = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      context.user_data[ADM_DATA] = {"uid": uid}
      context.user_data[ADM_STATE] = S_GIVEW_WID
      await update.message.reply_text(
          f"🎴 <code>{uid}</code> ga qaysi waifu?\nWaifu ID (#raqam) kiriting:",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Waifu berish: Waifu ID ──
    if state == S_GIVEW_WID:
      wid = text.lstrip("#").strip()
      waifu = await waifu_db.get_waifu(wid)
      if not waifu:
          await update.message.reply_text(f"❌ #{wid} topilmadi:")
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
      if not await log_db.is_full_admin(user.id):
          _clear_state(context)
          await update.message.reply_text("❌ Faqat to'liq admin.", reply_markup=kb)
          return
      user_ids = await user_db.get_all_users()
      await update.message.reply_text(f"📢 {len(user_ids)} foydalanuvchiga yuborilmoqda...", reply_markup=kb)
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
          f"✅ <b>Broadcast!</b>\n✔ Yuborildi: {sent}\n✖ Muvaffaqiyatsiz: {failed}",
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
          uname = parts[1].lstrip("@") if len(parts) > 1 else ""
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      await log_db.add_admin(uid, uname, user.id, role="admin")
      _clear_state(context)
      await update.message.reply_text(
          f"✅ <code>{uid}</code> → 🔧 <b>Admin</b> qilindi!",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Sub-Admin qo'shish ──
    if state == S_ADDSUBADM:
      if not is_god_admin(user.id):
          _clear_state(context)
          return
      try:
          parts = text.split()
          uid = int(parts[0])
          uname = parts[1].lstrip("@") if len(parts) > 1 else ""
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      await log_db.add_admin(uid, uname, user.id, role="sub")
      _clear_state(context)
      await update.message.reply_text(
          f"✅ <code>{uid}</code> → 🟡 <b>Sub-Admin</b> qilindi!\n"
          f"<i>Faqat waifu qo'shish (Common-Epic) va ko'rish imkoniyati berildi.</i>",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Admin o'chirish ──
    if state == S_RMADMIN:
      if not is_god_admin(user.id):
          _clear_state(context)
          return
      try:
          uid = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      await log_db.remove_admin(uid)
      _clear_state(context)
      await update.message.reply_text(
          f"✅ <code>{uid}</code> adminlikdan olib tashlandi!", parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Kanal: ID ──
    if state == S_ADDCH_ID:
      if not is_god_admin(user.id):
          _clear_state(context)
          return
      try:
          await context.bot.get_chat(text)
      except Exception as e:
          await update.message.reply_text(f"❌ Kanal topilmadi: {e}\nQaytadan:")
          return
      context.user_data[ADM_DATA] = {"ch_id": text}
      context.user_data[ADM_STATE] = S_ADDCH_NAME
      await update.message.reply_text("📢 Kanal ko'rsatma nomini kiriting:", reply_markup=kb)
      return

    # ── Kanal: nom ──
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
          f"✅ Majburiy kanal qo'shildi!\n🆔 <code>{ch_id}</code>\n📛 {text}",
          parse_mode="HTML", reply_markup=kb
      )
      return

    # ── Unvon: User ID ──
    if state == S_TITLE_UID:
      try:
          uid = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      context.user_data[ADM_DATA] = {"uid": uid}
      context.user_data[ADM_STATE] = S_TITLE_TXT
      await update.message.reply_text(
          f"🏅 <code>{uid}</code> ga unvon matnini kiriting:",
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
              await update.message.reply_text("❌ Format: start [tur] [x] [soat]")
              return
          description = " ".join(args[4:]) if len(args) > 4 else event_type
          await log_db.start_event(event_type, multiplier, description, user.id, hours)
          _clear_state(context)
          await update.message.reply_text(
              f"⚡ <b>EVENT BOSHLANDI!</b>\n"
              f"Tur: {event_type} | x{multiplier} | {hours} soat",
              parse_mode="HTML", reply_markup=kb
          )
          return
      await update.message.reply_text("❌ Format: start [tur] [x] [soat] yoki stop")
      return

    # ── Spawn chegarasi ──
    if state == S_SPAWN_SET:
      try:
          val = int(text)
      except ValueError:
          await update.message.reply_text("❌ Faqat raqam:")
          return
      if val < 100:
          await update.message.reply_text("❌ Minimum 100:")
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
              "❌ Spawn faqat guruhlarda ishlaydi.", reply_markup=kb
          )
      return

    # ── Guruh qo'shish bypass ──
    if state == S_ADDGROUP:
      if not is_god_admin(user.id):
          _clear_state(context)
          return
      gid, info = await _resolve_group_id(context, text.strip())
      if gid is None:
          await update.message.reply_text(
              f"❌ Guruh topilmadi: {info}\n"
              "ID, @username yoki havola kiriting:",
              parse_mode="HTML"
          )
          return
      await grp_db.bypass_group(gid)
      _clear_state(context)
      title_info = info or str(gid)
      await update.message.reply_text(
          f"✅ <b>Guruh qo'shildi!</b>\n"
          f"🆔 <code>{gid}</code>\n"
          f"📌 {title_info}\n"
          f"🔓 20 ta a'zo cheklovi <b>chetlab o'tildi</b>.\n"
          f"ℹ️ Endi botni guruhga qo'shing yoki bot allaqachon guruhda bo'lsa tayyor.",
          parse_mode="HTML", reply_markup=kb
      )
      return


# ──────────────────────────────────────
#  ADMIN RASM HANDLER (addwaifu)
# ──────────────────────────────────────

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get(ADM_STATE) != S_PHOTO:
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
    role = await _get_role(user.id)
    await update.message.reply_text(
      "✅ Rasm qabul qilindi!\n\n📝 Waifu ismini kiriting:",
      reply_markup=_panel_kb(role)
    )


# ──────────────────────────────────────
#  RARITY CALLBACK (waifu qo'shish)
# ──────────────────────────────────────

async def received_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    rarity = query.data.replace("rarity_", "")

    # Sub-admin Mythic+ larni tanlaya olmaydi
    role = await _get_role(user.id)
    if role == "sub" and rarity in SUB_ADMIN_BLOCKED_RARITY:
      await query.answer(
          f"🚫 Sub-Admin {rarity} daraja qo'sha olmaydi!\n"
          f"Faqat Common-Epic gacha.",
          show_alert=True
      )
      return

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
      await query.edit_message_text("❌ Xatolik. Qayta urinib ko'ring.")


# ──────────────────────────────────────
#  ADMIN INLINE CALLBACK HANDLER
# ──────────────────────────────────────

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if not await log_db.is_admin(user.id):
      await query.answer("❌ Ruxsatingiz yo'q.", show_alert=True)
      return

    role = await _get_role(user.id)
    is_sub = (role == "sub")

    # noop
    if data == "adm_noop":
      return

    # ── God/Admin: Waifu list pagination ──
    if data.startswith("adm_wlist_sub_"):
      try:
          page = int(data[len("adm_wlist_sub_"):])
      except ValueError:
          return
      await _show_waifu_list(query.message, page=page, edit=True, owner_id=user.id)
      return

    if data.startswith("adm_wlist_"):
      if is_sub:
          await query.answer("❌ Ruxsat yo'q.", show_alert=True)
          return
      try:
          page = int(data[len("adm_wlist_"):])
      except ValueError:
          return
      await _show_waifu_list(query.message, page=page, edit=True)
      return

    # ── Waifu o'chirish: confirm so'rash ──
    if data.startswith("adm_wdel_") and not data.startswith("adm_wdel_ok_") and data != "adm_wdel_cancel":
      try:
          db_id = int(data[len("adm_wdel_"):])
      except ValueError:
          return
      waifu = await waifu_db.get_waifu_by_db_id(db_id)
      if not waifu:
          await query.answer("Waifu topilmadi!", show_alert=True)
          return
      # Sub-admin faqat o'ziniki
      if is_sub and waifu.get("added_by") != user.id:
          await query.answer("❌ Bu waifu siz qo'shmagan.", show_alert=True)
          return
      emoji = get_rarity_emoji(waifu["rarity"])
      keyboard = InlineKeyboardMarkup([[
          InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"adm_wdel_ok_{db_id}"),
          InlineKeyboardButton("❌ Bekor", callback_data="adm_wdel_cancel"),
      ]])
      await query.message.reply_text(
          f"⚠️ <b>O'chirasizmi?</b>\n\n"
          f"{emoji} <b>{waifu['name']}</b> — {waifu['anime']}\n"
          f"Daraja: {waifu['rarity']} | 🆔 #{waifu['id']}",
          parse_mode="HTML",
          reply_markup=keyboard
      )
      return

    # ── Waifu o'chirish: tasdiqlandi ──
    if data.startswith("adm_wdel_ok_"):
      try:
          db_id = int(data[len("adm_wdel_ok_"):])
      except ValueError:
          return
      waifu = await waifu_db.get_waifu_by_db_id(db_id)
      if not waifu:
          await query.edit_message_text("❌ Waifu allaqachon o'chirilgan.")
          return
      if is_sub and waifu.get("added_by") != user.id:
          await query.answer("❌ Bu waifu siz qo'shmagan.", show_alert=True)
          return
      await waifu_db.remove_waifu_by_db_id(db_id)
      await log_db.add_log("remove_waifu", user_id=user.id, details=f"id={db_id} name={waifu['name']}")
      await query.edit_message_text(
          f"✅ <b>{waifu['name']}</b> (#{db_id}) o'chirildi!", parse_mode="HTML"
      )
      return

    # ── Waifu o'chirish: bekor ──
    if data == "adm_wdel_cancel":
      await query.edit_message_text("❌ Bekor qilindi.")
      return

    # ── Kanal o'chirish ──
    if data.startswith("adm_rmch_"):
      if not is_god_admin(user.id):
          await query.answer("❌ Faqat God Admin.", show_alert=True)
          return
      ch_id = data[len("adm_rmch_"):]
      await grp_db.remove_required_channel(ch_id)
      await query.edit_message_text(f"✅ <code>{ch_id}</code> kanal o'chirildi.", parse_mode="HTML")
      return


# ──────────────────────────────────────
#  ALOHIDA ADMIN BUYRUQLARI
# ──────────────────────────────────────

async def cmd_removewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /removewaifu [#id]")
      return
    wid = context.args[0].lstrip("#")
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
      try:
          waifu = await waifu_db.get_waifu_by_db_id(int(wid))
      except ValueError:
          pass
    if not waifu:
      await update.message.reply_text(f"❌ #{wid} topilmadi.")
      return
    # Sub-admin faqat o'ziniki
    role = await _get_role(update.effective_user.id)
    if role == "sub" and waifu.get("added_by") != update.effective_user.id:
      await update.message.reply_text("❌ Siz qo'shmagan waifuni o'chirishingiz mumkin emas.")
      return
    await waifu_db.remove_waifu(waifu["waifu_id"])
    await update.message.reply_text(
      f"✅ <b>{waifu['name']}</b> (#{waifu['id']}) o'chirildi.", parse_mode="HTML"
    )


async def cmd_addwaifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyruq orqali waifu qo'shish"""
    if not await require_admin(update, context):
      return
    await update.message.reply_text(
      "📸 Waifu rasmini yuboring.\n"
      "Paneldan ham foydalanishingiz mumkin: /panel"
    )
    role = await _get_role(update.effective_user.id)
    context.user_data[ADM_DATA] = {}
    context.user_data[ADM_STATE] = S_PHOTO


async def cmd_spawn_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
      await update.message.reply_text("❌ Faqat guruhda ishlaydi.")
      return
    from handlers.spawn import do_spawn
    await do_spawn(context, chat.id, chat.title)


async def _is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Guruh Telegram admini yoki bot admini ekanini tekshiradi."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
      return False
    # Bot admini har doim ruxsatli
    if await log_db.is_admin(user.id):
      return True
    # Guruhda Telegram admin huquqini tekshir
    try:
      member = await context.bot.get_chat_member(chat.id, user.id)
      return member.status in ("administrator", "creator")
    except Exception:
      return False


async def cmd_setspawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
      await update.message.reply_text("❌ Faqat guruhda.")
      return
    user = update.effective_user
    if not await _is_group_admin(update, context):
      await update.message.reply_text("❌ Bu buyruq faqat guruh adminlari uchun.")
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


async def _resolve_group_id(context, text: str):
    text = text.strip()
    if text.lstrip('-').isdigit():
        return int(text), None
    username = text
    if text.startswith('https://t.me/') or text.startswith('http://t.me/'):
        path = text.split('t.me/', 1)[1].rstrip('/')
        if path.startswith('+') or 'joinchat' in path:
            username = text
        else:
            username = '@' + path
    elif text.startswith('t.me/'):
        username = '@' + text.split('t.me/', 1)[1].rstrip('/')
    elif not text.startswith('@'):
        username = '@' + text
    try:
        chat = await context.bot.get_chat(username)
        return chat.id, chat.title
    except Exception as e:
        return None, str(e)


async def cmd_addgroup_bypass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if not context.args:
      await update.message.reply_text(
          "❌ Format: /addgroup [guruh_id yoki havola]\n\n"
          "Misol: /addgroup -1001234567890\n"
          "Misol: /addgroup @groupname\n"
          "Misol: /addgroup https://t.me/groupname",
          parse_mode="HTML"
      )
      return
    raw = " ".join(context.args)
    gid, info = await _resolve_group_id(context, raw)
    if gid is None:
        await update.message.reply_text(
            f"❌ Guruh topilmadi: {info}\n"
            "ID, @username yoki havola kiriting.",
            parse_mode="HTML"
        )
        return
    await grp_db.bypass_group(gid)
    title = info or str(gid)
    await update.message.reply_text(
        f"✅ <b>Guruh qo'shildi!</b>\n"
        f"🆔 <code>{gid}</code>\n"
        f"📌 {title}\n"
        f"🔓 20 ta a'zo cheklovi <b>chetlab o'tildi</b>.\n"
        f"ℹ️ Endi botni guruhga qo'shing yoki bot allaqachon guruhda bo'lsa tayyor.",
        parse_mode="HTML"
    )


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
    await update.message.reply_text(f"✅ Yuborildi: {sent} | ❌ Xato: {failed}")


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /addadmin [user_id] [@username]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    username = context.args[1].lstrip("@") if len(context.args) > 1 else ""
    await log_db.add_admin(uid, username, update.effective_user.id, role="admin")
    await update.message.reply_text(f"✅ <code>{uid}</code> → 🔧 Admin", parse_mode="HTML")


async def cmd_addsubadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /addsubadmin [user_id] [@username]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    username = context.args[1].lstrip("@") if len(context.args) > 1 else ""
    await log_db.add_admin(uid, username, update.effective_user.id, role="sub")
    await update.message.reply_text(
      f"✅ <code>{uid}</code> → 🟡 Sub-Admin\n"
      f"<i>Common-Epic waifu qo'sha oladi.</i>",
      parse_mode="HTML"
    )


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /removeadmin [user_id]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    await log_db.remove_admin(uid)
    await update.message.reply_text(f"✅ <code>{uid}</code> o'chirildi.", parse_mode="HTML")


async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /banuser [user_id] [sabab]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Sabab ko'rsatilmagan"
    await user_db.ban_user(uid, reason)
    from middlewares.ban_middleware import clear_ban_cache
    clear_ban_cache(uid)
    await update.message.reply_text(f"✅ <code>{uid}</code> bloklandi.", parse_mode="HTML")


async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /unbanuser [user_id]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    await user_db.unban_user(uid)
    from middlewares.ban_middleware import clear_ban_cache
    clear_ban_cache(uid)
    await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi.", parse_mode="HTML")


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
      await update.message.reply_text("❌ Raqam.")
      return
    await user_db.add_coins(uid, amount)
    await update.message.reply_text(f"✅ <code>{uid}</code> ga {amount:,} coin.", parse_mode="HTML")


async def cmd_givewaifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if len(context.args or []) < 2:
      await update.message.reply_text("❌ Format: /givewaifu [user_id] [waifu_id]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    wid = context.args[1].lstrip("#")
    waifu = await waifu_db.get_waifu(wid)
    if not waifu:
      await update.message.reply_text(f"❌ #{wid} topilmadi.")
      return
    await col_db.add_to_collection(uid, waifu["waifu_id"])
    emoji = get_rarity_emoji(waifu["rarity"])
    await update.message.reply_text(
      f"✅ {emoji} <b>{waifu['name']}</b> → <code>{uid}</code>", parse_mode="HTML"
    )


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    args = context.args or []
    if not args:
      await update.message.reply_text("📋 /event start [tur] [x] [soat]\n/event stop")
      return
    if args[0] == "start":
      if len(args) < 3:
          await update.message.reply_text("❌ Format: /event start [tur] [x] [soat]")
          return
      try:
          multiplier = float(args[2])
          hours = int(args[3]) if len(args) > 3 else 2
      except ValueError:
          await update.message.reply_text("❌ Raqam.")
          return
      description = " ".join(args[4:]) if len(args) > 4 else args[1]
      await log_db.start_event(args[1], multiplier, description, update.effective_user.id, hours)
      await update.message.reply_text(
          f"⚡ Event: {args[1]} x{multiplier} {hours}s", parse_mode="HTML"
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
      await update.message.reply_text("❌ Raqam.")
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
      await update.message.reply_text("❌ Raqam.")
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
      f"✅ Kanal qo'shildi!\n🆔 <code>{channel_id}</code>\n📛 {name}", parse_mode="HTML"
    )


async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_god(update, context):
      return
    if not context.args:
      channels = await grp_db.get_required_channels()
      if not channels:
          await update.message.reply_text("📋 Kanallar yo'q.")
          return
      lines = ["📋 <b>Kanallar:</b>"]
      for ch in channels:
          lines.append(f"• <code>{ch['channel_id']}</code> — {ch.get('channel_name','')}")
      await update.message.reply_text("\n".join(lines), parse_mode="HTML")
      return
    await grp_db.remove_required_channel(context.args[0])
    await update.message.reply_text(f"✅ O'chirildi.", parse_mode="HTML")


async def cmd_settitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    if len(context.args or []) < 2:
      await update.message.reply_text("❌ Format: /settitle [user_id] [unvon]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    title_text = " ".join(context.args[1:]).strip()
    await title_db.set_title(uid, title_text, update.effective_user.id)
    await update.message.reply_text(
      f"✅ <code>{uid}</code>\n🏅 <b>{title_text}</b>", parse_mode="HTML"
    )


async def cmd_removetitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ /removetitle [user_id]")
      return
    try:
      uid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ Raqam.")
      return
    await title_db.remove_title(uid)
    await update.message.reply_text(f"✅ {uid} unvoni o'chirildi.")


async def cmd_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_full_admin(update, context):
      return
    all_titles = await title_db.get_all_titles()
    if not all_titles:
      await update.message.reply_text("📋 Unvonlar yo'q.")
      return
    lines = ["🏅 <b>UNVONLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for t in all_titles:
      name = t.get("full_name") or t.get("username") or str(t["user_id"])
      lines.append(f"• <code>{t['user_id']}</code> {name} — 🏅 <b>{t['title']}</b>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
      return
    admins = await log_db.get_admins()
    role_mark = {"god": "👑 God Admin", "admin": "🔧 Admin", "sub": "🟡 Sub-Admin"}
    lines = ["🛡️ <b>ADMINLAR RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for a in admins:
      r = a.get("role") or "admin"
      mark = role_mark.get(r, "🔧 Admin")
      uname = f"@{a['username']}" if a.get("username") else ""
      lines.append(f"{mark}: <code>{a['user_id']}</code> {uname}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
