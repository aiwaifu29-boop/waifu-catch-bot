import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import users as user_db
from database import collections as col_db
from database import waifus as waifu_db
from database import market as market_db
from database import logs as log_db
from database.logs import get_active_event
from utils.helpers import get_rarity_emoji, format_profile, format_waifu_card, RARITY_ORDER

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        f"👋 Salom, <b>{user.full_name}</b>!\n\n"
        f"🎴 <b>Waifu Catch Bot</b> ga xush kelibsiz!\n\n"
        f"Anime qahramonlarini yig'ing, savdo qiling va kolleksiya yarating!\n\n"
        f"📋 /help — buyruqlar ro'yxati",
        parse_mode="HTML"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 <b>BUYRUQLAR RO'YXATI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>Profil</b>\n"
        "/profil — profilingiz\n"
        "/collection — kolleksiyangiz\n"
        "/daily — kunlik mukofot\n"
        "/favorite ID — sevimlilar\n"
        "\n"
        "🔄 <b>Savdo</b>\n"
        "/trade — savdo qilish\n"
        "/gift ID @user — sovg'a\n"
        "\n"
        "🛒 <b>Bozor</b>\n"
        "/market — bozor\n"
        "/sell ID NARX — sotish\n"
        "/buy ID — sotib olish\n"
        "\n"
        "🔍 <b>Qidiruv</b>\n"
        "/search ISMO — qidirish\n"
        "/anime NOMI — anime bo'yicha\n"
        "/top — reyting\n"
        "/stats — statistika\n"
        "/history — tarix\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await user_db.get_or_create_user(user.id, user.username, user.full_name)
    count = await col_db.count_collection(user.id)
    rank = await user_db.get_user_rank(user.id)
    text = format_profile(db_user, count, rank)
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args or []

    rarity = None
    anime = None
    page = 1

    for arg in args:
        if arg.isdigit():
            page = max(1, int(arg))
        elif arg.title() in RARITY_ORDER:
            rarity = arg.title()
        else:
            anime = arg

    offset = (page - 1) * 10
    items = await col_db.get_collection(user.id, rarity=rarity, anime=anime, limit=10, offset=offset)
    total = await col_db.count_collection(user.id)

    if not items:
        await update.message.reply_text(
            "📦 Kolleksiyangiz bo'sh yoki filtr bo'yicha waifu topilmadi."
        )
        return

    lines = [f"🎴 <b>KOLLEKSIYA</b> ({total} ta)\n━━━━━━━━━━━━━━━━━━━━"]
    for item in items:
        emoji = get_rarity_emoji(item["rarity"])
        fav = "⭐ " if item["is_favorite"] else ""
        lines.append(
            f"{fav}{emoji} <b>{item['name']}</b> — {item['anime']}\n"
            f"   🆔 <code>{item['collection_id']}</code> | {item['rarity']}"
        )

    total_pages = (total + 9) // 10
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━\nSahifa: {page}/{total_pages}")
    lines.append("Filtr: /collection [daraja] [anime] [sahifa]")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

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

    text = (
        f"🎁 <b>DAILY REWARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 +{coins} coin\n"
        f"🔥 Streak: {streak}/7\n"
    )
    if multiplier > 1:
        text += f"⚡ Event multiplier: x{multiplier}\n"
    if bonus_waifu:
        emoji = get_rarity_emoji(bonus_waifu["rarity"])
        text += f"\n🎉 Bonus: {emoji} <b>{bonus_waifu['name']}</b> oldingiz!\n"
    text += "━━━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    mode = args[0].lower() if args else "waifu"

    lines = ["🏆 <b>TOP REYTING</b>\n━━━━━━━━━━━━━━━━━━━━"]

    if mode in ("coin", "coins", "boy"):
        users = await user_db.get_top_users(10, "coins")
        lines[0] = "💰 <b>ENG BOY FOYDALANUVCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━"
        medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, u in enumerate(users):
            name = u.get("full_name") or u.get("username") or "Noma'lum"
            lines.append(f"{medals[i]} {name}: <b>{u['coins']:,}</b> coin")
    else:
        users = await user_db.get_top_users(10, "total_caught")
        medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, u in enumerate(users):
            name = u.get("full_name") or u.get("username") or "Noma'lum"
            lines.append(f"{medals[i]} {name}: <b>{u['total_caught']}</b> waifu")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("/top coin — coin reytingi")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Format: /search [ism]")
        return
    query = " ".join(context.args)
    results = await waifu_db.search_waifus(query)
    if not results:
        await update.message.reply_text(f"❌ '{query}' bo'yicha hech narsa topilmadi.")
        return
    lines = [f"🔍 <b>QIDIRUV: {query}</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for w in results:
        emoji = get_rarity_emoji(w["rarity"])
        lines.append(f"{emoji} <b>{w['name']}</b> — {w['anime']} ({w['rarity']})\n   ID: <code>{w['waifu_id']}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Format: /anime [nom]")
        return
    anime = " ".join(context.args)
    results = await waifu_db.get_waifus_by_anime(anime)
    if not results:
        await update.message.reply_text(f"❌ '{anime}' animesi topilmadi.")
        return
    lines = [f"🎌 <b>{anime.upper()}</b> waifulari\n━━━━━━━━━━━━━━━━━━━━"]
    for w in results:
        emoji = get_rarity_emoji(w["rarity"])
        lines.append(f"{emoji} <b>{w['name']}</b> ({w['rarity']})")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = await waifu_db.count_waifus_by_rarity()
    from database.market import count_active_listings
    from database.users import get_all_users
    total_waifus = sum(counts.values())
    market_count = await count_active_listings()
    users = await get_all_users()

    lines = [
        "📊 <b>BOT STATISTIKASI</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👥 Foydalanuvchilar: <b>{len(users)}</b>",
        f"🎴 Jami waifular: <b>{total_waifus}</b>",
        f"🛒 Bozorda: <b>{market_count}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>Darajalar bo'yicha:</b>"
    ]
    for rarity in RARITY_ORDER:
        cnt = counts.get(rarity, 0)
        emoji = get_rarity_emoji(rarity)
        lines.append(f"{emoji} {rarity}: <b>{cnt}</b>")

    event = await get_active_event()
    if event:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"⚡ <b>Aktiv event:</b> {event['description']}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Format: /favorite [kolleksiya_id]")
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
    status = "sevimlilarga qo'shildi ⭐" if new_state else "sevimlilardan olib tashlandi"
    await update.message.reply_text(f"✅ <b>{item['name']}</b> {status}!", parse_mode="HTML")

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logs = await log_db.get_logs(limit=10)
    user_logs = [l for l in logs if l.get("user_id") == user.id][:10]
    if not user_logs:
        await update.message.reply_text("📋 Tarixingiz bo'sh.")
        return
    lines = ["📋 <b>OXIRGI HARAKATLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for l in user_logs:
        lines.append(f"• {l['log_type']}: {l['details'] or ''} — {l['created_at'][:16]}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
