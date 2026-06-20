from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from database import logs as log_db
from utils.helpers import get_rarity_emoji

pending_gifts = {}

async def cmd_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args or []) < 2:
        await update.message.reply_text("\u274c Format: /gift [kolleksiya_id] @username")
        return

    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("\u274c ID raqam boʼishi kerak.")
        return

    target_username = context.args[1].lstrip("@")

    item = await col_db.get_collection_item(cid)
    if not item or item["user_id"] != user.id:
        await update.message.reply_text("\u274c Bu waifu sizda yoʼq.")
        return

    receiver = await user_db.get_user_by_username(target_username)
    if not receiver:
        await update.message.reply_text(f"\u274c @{target_username} topilmadi.")
        return

    if receiver["user_id"] == user.id:
        await update.message.reply_text("\u274c Oʼz\u0438ngizga sovgʼa qila olmaysiz.")
        return

    gift_id = f"gift_{user.id}_{cid}_{receiver['user_id']}"
    pending_gifts[gift_id] = {
        "sender_id": user.id,
        "sender_name": user.full_name,
        "receiver_id": receiver["user_id"],
        "collection_id": cid,
        "item": item,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\u2705 Qabul qilish", callback_data=f"gift_accept_{gift_id}"),
            InlineKeyboardButton("\u274c Rad etish", callback_data=f"gift_decline_{gift_id}"),
        ]
    ])

    emoji = get_rarity_emoji(item["rarity"])
    await update.message.reply_text(
        f"🎁 <b>SOVGʼA</b>\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"👤 <b>{user.full_name}</b> sovgʼa yubormoqda:\n"
        f"{emoji} <b>{item['name']}</b> \u2014 {item['anime']}\n"
        f"\u2b50 Daraja: {item['rarity']}\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"@{target_username} tasdiqlashi kerak!",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def handle_gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("gift_accept_"):
        gift_id = data[len("gift_accept_"):]
        gift = pending_gifts.get(gift_id)
        if not gift:
            await query.edit_message_text("\u274c Sovgʼa muddati oʼdi.")
            return
        if user.id != gift["receiver_id"]:
            await query.answer("\u274c Bu sovgʼa siz uchun emas!", show_alert=True)
            return

        success = await col_db.transfer_collection_item(gift["collection_id"], gift["sender_id"], gift["receiver_id"])
        if success:
            pending_gifts.pop(gift_id, None)
            await log_db.add_log("gift", user_id=gift["sender_id"],
                                 details=f"to={gift['receiver_id']} cid={gift['collection_id']}")
            emoji = get_rarity_emoji(gift["item"]["rarity"])
            await query.edit_message_text(
                f"🎁 <b>SOVGʼA QABUL QILINDI!</b>\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"{emoji} <b>{gift['item']['name']}</b> muvaffaqiyatli oʼkazildi!\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("\u274c Sovgʼa amalga oshmadi.")

    elif data.startswith("gift_decline_"):
        gift_id = data[len("gift_decline_"):]
        gift = pending_gifts.get(gift_id)
        if not gift:
            await query.edit_message_text("\u274c Sovgʼa topilmadi.")
            return
        if user.id not in (gift["sender_id"], gift["receiver_id"]):
            await query.answer("\u274c Ruxsatingiz yoʼq!", show_alert=True)
            return
        pending_gifts.pop(gift_id, None)
        await query.edit_message_text("\u274c Sovgʼa rad etildi.")
