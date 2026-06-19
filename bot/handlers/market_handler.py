from telegram import Update
from telegram.ext import ContextTypes
from database import market as market_db
from database import collections as col_db
from database import users as user_db
from database import logs as log_db
from utils.helpers import get_rarity_emoji

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
        f"🆔 Listing ID: <code>{listing_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    page = int(args[0]) if args and args[0].isdigit() else 1
    offset = (page - 1) * 10

    listings = await market_db.get_active_listings(limit=10, offset=offset)
    total = await market_db.count_active_listings()

    if not listings:
        await update.message.reply_text("🛒 Bozor hozircha bo'sh.")
        return

    lines = [f"🛒 <b>BOZOR</b> ({total} ta)\n━━━━━━━━━━━━━━━━━━━━"]
    for l in listings:
        emoji = get_rarity_emoji(l["rarity"])
        seller = l.get("seller_username") or f"ID:{l['seller_id']}"
        lines.append(
            f"{emoji} <b>{l['name']}</b> — {l['anime']}\n"
            f"   💰 {l['price']:,} coin | 👤 @{seller}\n"
            f"   /buy {l['id']}"
        )

    total_pages = (total + 9) // 10
    lines.append(f"━━━━━━━━━━━━━━━━━━━━\nSahifa: {page}/{total_pages}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("❌ Format: /buy [listing_id]")
        return

    try:
        lid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak.")
        return

    listing = await market_db.get_market_listing(lid)
    if not listing:
        await update.message.reply_text("❌ Bu listing topilmadi yoki sotilgan.")
        return

    if listing["seller_id"] == user.id:
        await update.message.reply_text("❌ O'z waifungizni o'zingiz soto olmaysiz.")
        return

    db_user = await user_db.get_user(user.id)
    if not db_user or db_user["coins"] < listing["price"]:
        await update.message.reply_text(
            f"❌ Coiningiz yetarli emas.\n"
            f"Kerak: {listing['price']:,} | Sizda: {db_user.get('coins', 0):,}"
        )
        return

    success = await market_db.buy_from_market(lid, user.id)
    if not success:
        await update.message.reply_text("❌ Xarid amalga oshmadi.")
        return

    await user_db.remove_coins(user.id, listing["price"])
    await user_db.add_coins(listing["seller_id"], listing["price"])
    await col_db.transfer_collection_item(listing["collection_id"], listing["seller_id"], user.id)

    await log_db.add_log("market_buy", user_id=user.id,
                         details=f"lid={lid} price={listing['price']} seller={listing['seller_id']}")

    emoji = get_rarity_emoji(listing["rarity"])
    await update.message.reply_text(
        f"✅ <b>Xarid muvaffaqiyatli!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>{listing['name']}</b>\n"
        f"💰 To'landi: <b>{listing['price']:,}</b> coin\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
