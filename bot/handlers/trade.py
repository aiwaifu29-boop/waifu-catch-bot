from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from database import logs as log_db
from database.logs import add_log
from utils.helpers import get_rarity_emoji

pending_trades = {}

async def cmd_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "❌ Format: /trade [sizning_kolleksiya_id] [raqib_kolleksiya_id] @username"
        )
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Format: /trade [sizning_id] [raqib_id] @username\n"
            "Misol: /trade 123 456 @friend"
        )
        return

    try:
        my_cid = int(args[0])
        their_cid = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ ID lar raqam bo'lishi kerak.")
        return

    target_username = args[2].lstrip("@")

    my_item = await col_db.get_collection_item(my_cid)
    if not my_item or my_item["user_id"] != user.id:
        await update.message.reply_text("❌ Bu waifu sizda yo'q.")
        return

    their_item = await col_db.get_collection_item(their_cid)
    if not their_item:
        await update.message.reply_text("❌ Raqib waifusi topilmadi.")
        return

    emoji1 = get_rarity_emoji(my_item["rarity"])
    emoji2 = get_rarity_emoji(their_item["rarity"])

    trade_id = f"{user.id}_{their_item['user_id']}_{my_cid}_{their_cid}"
    pending_trades[trade_id] = {
        "initiator_id": user.id,
        "initiator_name": user.full_name,
        "receiver_id": their_item["user_id"],
        "my_cid": my_cid,
        "their_cid": their_cid,
        "my_waifu": my_item,
        "their_waifu": their_item,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Qabul qilish", callback_data=f"trade_accept_{trade_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"trade_decline_{trade_id}"),
        ]
    ])

    mention = f'<a href="tg://user?id={their_item["user_id"]}">{their_item["user_id"]}</a>'

    await update.message.reply_text(
        f"🔄 <b>SAVDO TAKLIFI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 <b>{user.full_name}</b> beradi:\n"
        f"  {emoji1} {my_item['name']} ({my_item['rarity']})\n\n"
        f"📥 Evaziga oladi:\n"
        f"  {emoji2} {their_item['name']} ({their_item['rarity']})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Raqib tasdiqlashi kerak!",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def handle_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    if data.startswith("trade_accept_"):
        trade_id = data[len("trade_accept_"):]
        trade = pending_trades.get(trade_id)

        if not trade:
            await query.edit_message_text("❌ Savdo muddati o'tdi.")
            return

        if user.id != trade["receiver_id"]:
            await query.answer("❌ Bu savdo siz uchun emas!", show_alert=True)
            return

        my_cid = trade["my_cid"]
        their_cid = trade["their_cid"]

        success1 = await col_db.transfer_collection_item(my_cid, trade["initiator_id"], trade["receiver_id"])
        success2 = await col_db.transfer_collection_item(their_cid, trade["receiver_id"], trade["initiator_id"])

        if success1 and success2:
            pending_trades.pop(trade_id, None)

            await col_db.add_to_collection.__module__
            import aiosqlite
            from database.db import DB_PATH
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET trade_count=trade_count+1 WHERE user_id IN (?,?)",
                                 (trade["initiator_id"], trade["receiver_id"]))
                await db.commit()

            await log_db.add_log("trade", user_id=trade["initiator_id"],
                                 details=f"with={trade['receiver_id']} my={my_cid} their={their_cid}")

            emoji1 = get_rarity_emoji(trade["my_waifu"]["rarity"])
            emoji2 = get_rarity_emoji(trade["their_waifu"]["rarity"])

            await query.edit_message_text(
                f"✅ <b>SAVDO MUVAFFAQIYATLI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emoji1} {trade['my_waifu']['name']} ↔️ {emoji2} {trade['their_waifu']['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("❌ Savdo amalga oshmadi. Waifu'lar o'zgargan bo'lishi mumkin.")

    elif data.startswith("trade_decline_"):
        trade_id = data[len("trade_decline_"):]
        trade = pending_trades.get(trade_id)

        if not trade:
            await query.edit_message_text("❌ Savdo topilmadi.")
            return

        if user.id not in (trade["initiator_id"], trade["receiver_id"]):
            await query.answer("❌ Ruxsatingiz yo'q!", show_alert=True)
            return

        pending_trades.pop(trade_id, None)
        await query.edit_message_text("❌ Savdo rad etildi.")
