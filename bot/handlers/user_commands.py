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
        "\n"
        "🏆 <b>Reyting</b>\n"
        "/top — global top (waifu)\n"
        "/top coin — global top (coin)\n"
        "/gtop — guruh top\n"
        "\n"
        "/stats — statistika\n"
        "/history — tarix\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )


async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await _check_sub(update, context): return
    db_user = await user_db.get_or_create_user(user.id, user.username, user.full_name)
    count = await col_db.count_collection(user.id)
    rank = await user_db.get_user_rank(user.id)
    title = await title_db.get_title(user.id)
    text = format_profile(db_user, count, rank, title=title)
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    if not await _check_sub(update, context): return
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
    if not await _check_sub(update, context): return
    args = context.args or []
    mode = args[0].lower() if args else "waifu"
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if mode in ("coin", "coins", "boy"):
        users = await user_db.get_top_users(10, "coins")
        lines = ["💰 <b>GLOBAL TOP — ENG BOY</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for i, u in enumerate(users):
            name = u.get("full_name") or u.get("username") or "Noma'lum"
            lines.append(f"{medals[i]} {name}: <b>{u['coins']:,}</b> coin")
    else:
        users = await user_db.get_top_users(10, "total_caught")
        lines = ["🏆 <b>GLOBAL TOP — ENG KO'P WAIFU</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for i, u in enumerate(users):
            name = u.get("full_name") or u.get("username") or "Noma'lum"
            lines.append(f"{medals[i]} {name}: <b>{u['total_caught']}</b> waifu")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("/top coin — coin reytingi\n/gtop — guruh reytingi")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_gtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Bu buyruq faqat guruhlarda ishlaydi.")
        return
    if not await _check_sub(update, context): return

    args = context.args or []
    mode = args[0].lower() if args else "waifu"
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    group_top = await log_db.get_group_top(chat.id, limit=10, mode=mode)
    if not group_top:
        await update.message.reply_text("📊 Bu guruhda hali hech kim waifu qo'lga kiritgani yo'q.")
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
            lines.append(f"{medals[i]} {name}: <b>{row.get('coins', 0):,}</b> coin")
        else:
            lines.append(f"{medals[i]} {name}: <b>{row['catch_count']}</b> waifu")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("/gtop coin — guruh coin top\n/top — global reyting")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context): return
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
        lines.append(
            f"{emoji} <b>{w['name']}</b> — {w['anime']} ({w['rarity']})\n"
            f"   🆔 <code>{w['waifu_id']}</code>"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context): return
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
        lines.append(f"{emoji} <b>{w['name']}</b> ({w['rarity']})\n   🆔 <code>{w['waifu_id']}</code>")
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
        lines.append(f"{emoji} {rarity}: <b>{cnt}</b>")

    event = await get_active_event()
    if event:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"⚡ <b>Aktiv event:</b> {event['description']}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_sub(update, context): return
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
    if not await _check_sub(update, context): return
    user = update.effective_user
    logs = await log_db.get_logs(limit=50)
    user_logs = [l for l in logs if l.get("user_id") == user.id][:10]
    if not user_logs:
        await update.message.reply_text("📋 Tarixingiz bo'sh.")
        return
    lines = ["📋 <b>OXIRGI HARAKATLAR</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for l in user_logs:
        lines.append(f"• {l['log_type']}: {l['details'] or ''} — {l['created_at'][:16]}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
