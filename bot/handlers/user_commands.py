import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import users as user_db
from database import collections as col_db
from database import waifus as waifu_db
from database import market as market_db
from database import logs as log_db
from database import titles as title_db
from database.logs import get_active_event
from utils.helpers import get_rarity_emoji, format_profile, format_waifu_card, RARITY_ORDER


async def _check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    from middlewares.subscription import check_subscription
    return await check_subscription(update, context)


async def _check_ban(user_id: int) -> bool:
    u = await user_db.get_user(user_id)
    return bool(u and u.get("is_banned"))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
      f"👋 Salom, <b>{user.full_name}</b>!\n\n"
      f"🎴 <b>Waifu Catch Bot</b> ga xush kelibsiz!\n\n"
      f"Anime qahramonlarini yig'ing, savdo qiling va kolleksiya yarating!\n\n"
      f"📋 /help — barcha buyruqlar ro'yxati\n"
      f"🃏 /collection — kolleksiyangiz\n"
      f"🎁 /daily — kunlik mukofot",
      parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    is_group = chat.type in ("group", "supergroup")

    is_group_admin = False
    if is_group and update.effective_user:
      try:
          member = await chat.get_member(update.effective_user.id)
          is_group_admin = member.status in ("administrator", "creator")
      except Exception:
          pass

    text = (
      "📋 <b>BUYRUQLAR RO'YXATI</b>\n"
      "━━━━━━━━━━━━━━━━━━━━\n"
      "\n"
      "👤 <b>Profil va kolleksiya</b>\n"
      "/profil — profilingiz va statistika\n"
      "/collection — kolleksiyangizni ko'rish\n"
      "/favorite [ID] — sevimli waifu belgilash\n"
      "/history — so'ngi harakatlar\n"
      "\n"
      "🎁 <b>Kunlik</b>\n"
      "/daily — kunlik mukofot (streak bonus!)\n"
      "/market — bugungi do'kon (5 ta waifu)\n"
      "\n"
      "🎯 <b>Waifu tutish (guruhda)</b>\n"
      "/waifu [ism] — paydo bo'lgan waifuni tutish\n"
      "<i>💡 Har 100 xabarda 1 ta waifu paydo bo'ladi</i>\n"
      "\n"
      "🔄 <b>Savdo va sovg'a</b>\n"
      "/trade — boshqa user bilan almashish\n"
      "/gift [ID] @user — waifu sovg'a qilish\n"
      "\n"
      "🛒 <b>Bozor</b>\n"
      "/sell [ID] [narx] — bozorga qo'yish\n"
      "/buy [ID] — bozordan sotib olish\n"
      "\n"
      "🔍 <b>Qidiruv</b>\n"
      "/search [ism] — waifu qidirish\n"
      "/anime [nom] — anime bo'yicha qidirish\n"
      "\n"
      "🏆 <b>Reyting</b>\n"
      "/top — eng ko'p waifu tutganlar\n"
      "/top coin — eng boy foydalanuvchilar\n"
      "/gtop — guruh ichidagi reyting\n"
      "/stats — bot statistikasi\n"
    )

    if is_group_admin:
      text += (
          "\n"
          "━━━━━━━━━━━━━━━━━━━━\n"
          "🔧 <b>GURUH ADMIN BUYRUQLARI</b>\n"
          "━━━━━━━━━━━━━━━━━━━━\n"
          "/setspawn [son] — spawn chegarasi\n"
          "   <i>Misol: /setspawn 80 → har 80 xabarda 1 spawn</i>\n"
          "/warn — [reply] ogohlantirish (3 warn = ban)\n"
          "/mute — [reply] jimlatish\n"
          "/unmute — [reply] jimlatishni bekor\n"
          "/kick — [reply] guruhdan chiqarish\n"
          "/ban — [reply] guruhdan bloklash\n"
          "/unban — [reply] blokni bekor qilish\n"
          "\n"
          "🛡 <b>Flood himoya (avtomatik)</b>\n"
          "<i>7 sek ichida 7+ xabar → 30 daq hisoblanmaydi</i>\n"
      )

    text += (
      "\n"
      "━━━━━━━━━━━━━━━━━━━━\n"
      "⭐ Common • Rare • Super Rare • Epic • Mythic • Legendary\n"
      "━━━━━━━━━━━━━━━━━━━━"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await _check_sub(update, context):
      return
    db_user = await user_db.get_or_create_user(user.id, user.username, user.full_name)
    count = await col_db.count_collection(user.id)
    rank = await user_db.get_user_rank(user.id)
    title = await title_db.get_title(user.id)
    text = format_profile(db_user, count, rank, title=title)
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if not await _check_sub(update, context):
      return
    if await _check_ban(user.id):
      await update.message.reply_text("🚫 Siz bloklanganlar ro'yxatasiz.")
      return

    daily = await log_db.get_daily_reward(user.id)
    now = datetime.now()

    if daily and daily.get("last_daily"):
      last = datetime.fromisoformat(daily["last_daily"])
      diff = now - last
      if diff.total_seconds() < 86400:
          remaining = timedelta(seconds=86400) - diff
          h = int(remaining.total_seconds() // 3600)
          m = int((remaining.total_seconds() % 3600) // 60)
          await update.message.reply_text(
              f"⏰ Keyingi daily: <b>{h}s {m}d</b> keyin",
              parse_mode="HTML"
          )
          return

    streak = (daily.get("streak", 0) + 1) if daily else 1
    if streak > 7:
      streak = 1

    base_coins = 100 + (streak * 20)
    multiplier = await log_db.get_event_multiplier()
    coins = int(base_coins * multiplier)

    bonus_waifu = None
    if random.random() < 0.05:
      bonus_waifu = await waifu_db.get_random_waifu("Common")
      if bonus_waifu:
          await col_db.add_to_collection(user.id, bonus_waifu["waifu_id"])

    await user_db.add_coins(user.id, coins)
    await log_db.set_daily_reward(user.id, streak)
    await log_db.add_log("daily", user_id=user.id, details=f"coins={coins} streak={streak}")

    streak_bar = "🔥" * streak + "⬜" * (7 - streak)
    text = (
      f"🎁 <b>DAILY REWARD</b>\n"
      f"━━━━━━━━━━━━━━━━━━━━\n"
      f"💰 +<b>{coins:,}</b> coin\n"
      f"🔥 Streak: <b>{streak}/7</b>  {streak_bar}\n"
    )
    if multiplier > 1:
      text += f"⚡ Event bonus: x{multiplier}!\n"
    if bonus_waifu:
      emoji = get_rarity_emoji(bonus_waifu["rarity"])
      text += f"\n🎉 Bonus waifu: {emoji} <b>{bonus_waifu['name']}</b>!\n"
    text += "━━━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
      return
    args = context.args or []
    mode = args[0].lower() if args else "waifu"
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if mode in ("coin", "coins", "boy"):
      users = await user_db.get_top_users(10, "coins")
      lines = ["💰 <b>GLOBAL TOP — ENG BOY</b>\n━━━━━━━━━━━━━━━━━━━━"]
      for i, u in enumerate(users):
          name = u.get("full_name") or u.get("username") or "Noma'lum"
          lines.append(f"{medals[i]} {name}: <b>{u['coins']:,}</b> 💰")
    else:
      users = await user_db.get_top_users(10, "total_caught")
      lines = ["🏆 <b>GLOBAL TOP — ENG KO'P WAIFU</b>\n━━━━━━━━━━━━━━━━━━━━"]
      for i, u in enumerate(users):
          name = u.get("full_name") or u.get("username") or "Noma'lum"
          lines.append(f"{medals[i]} {name}: <b>{u['total_caught']}</b> 🎴")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("/top coin — coin reyting | /gtop — guruh reytingi")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_gtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
      await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
      return
    if not await _check_sub(update, context):
      return

    args = context.args or []
    mode = args[0].lower() if args else "waifu"
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    group_top = await log_db.get_group_top(chat.id, limit=10, mode=mode)
    if not group_top:
      await update.message.reply_text(
          "📊 Bu guruhda hali hech kim waifu qo'lga kiritgani yo'q.\n"
          "Guruhda faol bo'ling — har 100 xabarda waifu paydo bo'ladi! 🎴"
      )
      return

    title_map = {
      "coin": f"💰 <b>GURUH TOP — ENG BOY</b>\n<i>{chat.title}</i>",
      "waifu": f"🏆 <b>GURUH TOP — ENG KO'P WAIFU</b>\n<i>{chat.title}</i>",
    }
    title = title_map.get(mode, title_map["waifu"])
    lines = [title + "\n━━━━━━━━━━━━━━━━━━━━"]

    for i, row in enumerate(group_top):
      name = row.get("full_name") or row.get("username") or f"ID:{row['user_id']}"
      if mode in ("coin", "coins"):
          lines.append(f"{medals[i]} {name}: <b>{row.get('coins', 0):,}</b> 💰")
      else:
          lines.append(f"{medals[i]} {name}: <b>{row['catch_count']}</b> 🎴")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("/gtop coin — guruh coin top | /top — global reyting")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /search [ism]\nMisol: /search Mikasa")
      return
    query = " ".join(context.args)
    results = await waifu_db.search_waifus(query)
    if not results:
      await update.message.reply_text(f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi.", parse_mode="HTML")
      return
    lines = [f"🔍 <b>QIDIRUV: {query}</b> ({len(results)} ta)\n━━━━━━━━━━━━━━━━━━━━"]
    for w in results[:15]:
      emoji = get_rarity_emoji(w["rarity"])
      lines.append(
          f"{emoji} <b>{w['name']}</b> — {w['anime']}\n"
          f"   ⭐ {w['rarity']} | 🆔 <code>#{w['waifu_id']}</code>"
      )
    if len(results) > 15:
      lines.append(f"\n<i>...va yana {len(results) - 15} ta natija</i>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
      return
    if not context.args:
      await update.message.reply_text("❌ Format: /anime [nom]\nMisol: /anime Naruto")
      return
    anime = " ".join(context.args)
    results = await waifu_db.get_waifus_by_anime(anime)
    if not results:
      await update.message.reply_text(f"❌ <b>'{anime}'</b> animesi topilmadi.", parse_mode="HTML")
      return
    lines = [f"🎌 <b>{anime.upper()}</b> — {len(results)} ta waifu\n━━━━━━━━━━━━━━━━━━━━"]
    for w in results:
      emoji = get_rarity_emoji(w["rarity"])
      lines.append(f"{emoji} <b>{w['name']}</b> ({w['rarity']}) 🆔 <code>#{w['waifu_id']}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = await waifu_db.count_waifus_by_rarity()
    from database.market import count_active_listings
    from database.users import get_all_users
    total_waifus = sum(counts.values())
    market_count = await count_active_listings()
    users = await get_all_users()
    channels = await log_db.get_required_channels_count()

    lines = [
      "📊 <b>BOT STATISTIKASI</b>",
      "━━━━━━━━━━━━━━━━━━━━",
      f"👥 Foydalanuvchilar: <b>{len(users)}</b>",
      f"🎴 Jami waifular: <b>{total_waifus}</b>",
      f"🛒 Bozorda: <b>{market_count}</b>",
      f"📢 Majburiy kanallar: <b>{channels}</b>",
      "━━━━━━━━━━━━━━━━━━━━",
      "<b>Darajalar bo'yicha:</b>"
    ]
    for rarity in RARITY_ORDER:
      cnt = counts.get(rarity, 0)
      emoji = get_rarity_emoji(rarity)
      lines.append(f"{emoji} {rarity}: <b>{cnt}</b> ta")

    event = await get_active_event()
    if event:
      lines.append("━━━━━━━━━━━━━━━━━━━━")
      lines.append(f"⚡ <b>Aktiv event:</b> {event['description']}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
      return
    if not context.args:
      await update.message.reply_text(
          "❌ Format: /favorite [kolleksiya_id]\n"
          "Misol: /favorite 42\n\n"
          "<i>Kolleksiya ID ni /collection dan topasiz</i>",
          parse_mode="HTML"
      )
      return
    try:
      cid = int(context.args[0])
    except ValueError:
      await update.message.reply_text("❌ ID raqam bo'lishi kerak.")
      return

    user = update.effective_user
    item = await col_db.get_collection_item(cid)
    if not item or item["user_id"] != user.id:
      await update.message.reply_text("❌ Bu waifu sizda yo'q.")
      return

    new_state = not bool(item["is_favorite"])
    await col_db.set_favorite(cid, user.id, new_state)
    emoji = get_rarity_emoji(item.get("rarity", "Common"))
    if new_state:
      await update.message.reply_text(
          f"⭐ {emoji} <b>{item['name']}</b> sevimlilarga qo'shildi!\n"
          f"Profilingizda asosiy waifu sifatida ko'rsatiladi.",
          parse_mode="HTML"
      )
    else:
      await update.message.reply_text(
          f"🗑 <b>{item['name']}</b> sevimlilardan olib tashlandi.",
          parse_mode="HTML"
      )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context):
      return
    user = update.effective_user
    logs = await log_db.get_logs(limit=50)
    user_logs = [l for l in logs if l.get("user_id") == user.id][:10]
    if not user_logs:
      await update.message.reply_text(
          "📋 Tarixingiz bo'sh.\n\n"
          "Guruhda waifu tuting yoki daily mukofot oling!"
      )
      return
    icons = {
      "catch": "🎴", "daily": "🎁", "sell": "💸",
      "buy": "🛒", "trade": "🔄", "gift": "🎀",
      "warn": "⚠️", "ban": "🚫"
    }
    lines = ["📋 <b>OXIRGI HARAKATLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for l in user_logs:
      icon = icons.get(l["log_type"], "•")
      lines.append(
          f"{icon} <b>{l['log_type'].upper()}</b>: {l.get('details', '') or ''}\n"
          f"   🕐 {l['created_at'][:16]}"
      )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
