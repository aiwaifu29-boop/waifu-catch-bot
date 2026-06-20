from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import users as user_db
from database import logs as log_db
from database import shop as shop_db
from database import market as market_db
from database import collections as col_db
from utils.helpers import get_rarity_emoji
from datetime import date


def _build_shop_text(items: list, owner_name: str) -> str:
    lines = [
        "🛒 <b>BUGUNGI MAXSUS DO'KON</b>",
        f"👤 {owner_name}  📅 {date.today().isoformat()}",
        "━━━━━━━━━━━━━━━━━━━━",
        "<i>Do'kon har kuni yangilanadi. Har foydalanuvchi o'ziga xos taklif oladi!</i>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for item in items:
        emoji = get_rarity_emoji(item["rarity"])
        if item["is_sold"]:
            sold_mark = "✅ <i>Sotib olindi</i>"
        else:
            sold_mark = f"💰 <b>{item['price']:,}</b> coin"
        lines.append(
            f"<b>#{item['slot']}</b> {emoji} <b>{item['name']}</b>\n"
            f"    🎌 {item['anime']} | {item['rarity']}\n"
            f"    {sold_mark}"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("Tugmani bosing yoki: /buy [1-5]")
    return "\n".join(lines)


def _build_shop_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for item in items:
        if not item["is_sold"]:
            emoji = get_rarity_emoji(item["rarity"])
            row.append(InlineKeyboardButton(
                f"#{item['slot']} {emoji} {item['price']:,}c",
                callback_data=f"shop_buy_{item['slot']}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔄 Yangilash", callback_data="shop_refresh")])
    return InlineKeyboardMarkup(buttons)


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    from middlewares.subscription import check_subscription
    if not await check_subscription(update, context):
        return

    items = await shop_db.get_or_create_shop(user.id)
    if not items:
        await update.message.reply_text(
            "❌ Do'konda hozircha waifu yo'q.\n"
            "Admin botga waifu qo'shishi kerak!"
        )
        return

    text = _build_shop_text(items, user.full_name)
    keyboard = _build_shop_keyboard(items)

    first_with_photo = next((it for it in items if it.get("file_id") and not it["is_sold"]), None)
    if not first_with_photo:
        first_with_photo = next((it for it in items if it.get("file_id")), None)

    try:
        if first_with_photo:
            await update.message.reply_photo(
                photo=first_with_photo["file_id"],
                caption=text, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def handle_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data == "shop_refresh":
        items = await shop_db.get_or_create_shop(user.id)
        text = _build_shop_text(items, user.full_name)
        keyboard = _build_shop_keyboard(items)
        try:
            await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                pass
        return

    if not data.startswith("shop_buy_"):
        return

    try:
        slot = int(data[len("shop_buy_"):])
    except ValueError:
        return

    result = await shop_db.buy_shop_slot(user.id, slot)
    if "error" in result:
        await query.answer(result["error"], show_alert=True)
        return

    item = result["item"]
    emoji = get_rarity_emoji(item["rarity"])
    await log_db.add_log("shop_buy", user_id=user.id,
                         details=f"slot={slot} waifu={item['waifu_id']} price={item['price']}")

    # Xabarni yangilaymiz
    items = await shop_db.get_daily_shop(user.id)
    text = _build_shop_text(items, user.full_name)
    keyboard = _build_shop_keyboard(items)
    try:
        await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            pass

    await query.answer(f"✅ {item['name']} sotib olindi!", show_alert=True)


async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args or []) < 2:
        await update.message.reply_text("❌ Format: /sell [kolleksiya_id] [narx]")
        return
    try:
        cid = int(context.args[0])
        price = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ID va narx raqam bo'lishi kerak.")
        return
    if price < 1:
        await update.message.reply_text("❌ Narx 1 coindan kam bo'lmasin.")
        return
    item = await col_db.get_collection_item(cid)
    if not item or item["user_id"] != user.id:
        await update.message.reply_text("❌ Bu waifu sizda yo'q.")
        return
    listing_id = await market_db.list_on_market(user.id, cid, item["waifu_id"], price)
    emoji = get_rarity_emoji(item["rarity"])
    await log_db.add_log("market_sell", user_id=user.id, details=f"cid={cid} price={price}")
    await update.message.reply_text(
        f"✅ <b>Bozorga qo'yildi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>{item['name']}</b>\n"
        f"💰 Narx: <b>{price:,}</b> coin\n"
        f"🆔 Listing: <code>{listing_id}</code>",
        parse_mode="HTML"
    )


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "❌ Format:\n"
            "/buy [1-5] — do'kondan sotib olish\n"
            "/buy [listing_id] — bozordan sotib olish"
        )
        return
    arg = context.args[0]
    if not arg.isdigit():
        await update.message.reply_text("❌ Raqam kiriting.")
        return
    num = int(arg)

    if 1 <= num <= 5:
        # Do'kondan sotib olish
        result = await shop_db.buy_shop_slot(user.id, num)
        if "error" in result:
            await update.message.reply_text(f"❌ {result['error']}")
            return
        item = result["item"]
        emoji = get_rarity_emoji(item["rarity"])
        await log_db.add_log("shop_buy", user_id=user.id,
                             details=f"slot={num} waifu={item['waifu_id']} price={item['price']}")
        await update.message.reply_text(
            f"✅ <b>Xarid muvaffaqiyatli!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>{item['name']}</b>\n"
            f"🎌 {item['anime']} • {item['rarity']}\n"
            f"💰 Sarflandi: <b>{item['price']:,}</b> coin",
            parse_mode="HTML"
        )
    else:
        # Bozor listingdan sotib olish
        listing = await market_db.get_market_listing(num)
        if not listing:
            await update.message.reply_text("❌ Listing topilmadi yoki sotilgan.")
            return
        if listing["seller_id"] == user.id:
            await update.message.reply_text("❌ O'z waifungizni o'zingiz soto olmaysiz.")
            return
        db_user = await user_db.get_user(user.id)
        if not db_user or db_user["coins"] < listing["price"]:
            await update.message.reply_text(
                f"❌ Coin yetarli emas.\nKerak: {listing['price']:,} | Sizda: {db_user.get('coins', 0):,}"
            )
            return
        ok = await market_db.buy_from_market(num, user.id)
        if not ok:
            await update.message.reply_text("❌ Xarid amalga oshmadi.")
            return
        await user_db.remove_coins(user.id, listing["price"])
        await user_db.add_coins(listing["seller_id"], listing["price"])
        await col_db.transfer_collection_item(listing["collection_id"], listing["seller_id"], user.id)
        emoji = get_rarity_emoji(listing["rarity"])
        await update.message.reply_text(
            f"✅ <b>Xarid!</b>\n{emoji} <b>{listing['name']}</b>\n💰 {listing['price']:,} coin",
            parse_mode="HTML"
        )
