from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from utils.helpers import get_rarity_emoji, RARITY_ORDER

async def cmd_collection_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    items = await col_db.get_collection(user.id, limit=100)
    if not items:
        await update.message.reply_text(
            "📦 Kolleksiyangiz hali bo'sh!\n"
            "Guruhdagi waifularni qo'lga kiriting."
        )
        return

    total = len(items)
    await send_gallery_page(update, context, user.id, items, 0, total)

async def send_gallery_page(update, context, user_id: int, items: list, index: int, total: int):
    item = items[index]
    emoji = get_rarity_emoji(item["rarity"])
    fav = "⭐ " if item.get("is_favorite") else ""

    # Build waifu list (show nearby items)
    start = max(0, index - 2)
    end = min(total, index + 3)
    list_lines = []
    for i in range(start, end):
        it = items[i]
        e = get_rarity_emoji(it["rarity"])
        marker = "▶️" if i == index else "  "
        fv = "⭐" if it.get("is_favorite") else ""
        list_lines.append(f"{marker}{e} {fv}{it['name']}")

    caption = (
        f"🎴 <b>KOLLEKSIYA</b> [{index+1}/{total}]\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} {fav}<b>{item['name']}</b>\n"
        f"🎌 {item['anime']}\n"
        f"⭐ {item['rarity']}\n"
        f"🆔 <code>{item['collection_id']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Kolleksiya:</b>\n" + "\n".join(list_lines) +
        (f"\n..." if total > 5 else "")
    )

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"gal_{user_id}_{index-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {index+1}/{total}", callback_data="gal_noop"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"gal_{user_id}_{index+1}"))

    action_row = [
        InlineKeyboardButton(
            "⭐ Sevimli" if not item.get("is_favorite") else "💔 Olib tashlash",
            callback_data=f"gal_fav_{user_id}_{index}_{item['collection_id']}"
        ),
        InlineKeyboardButton("❌ Yopish", callback_data=f"gal_close"),
    ]

    keyboard = InlineKeyboardMarkup([nav_row, action_row])

    if hasattr(update, "message") and update.message:
        try:
            await update.message.reply_photo(
                photo=item["file_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Rasm yuborishda xato: {e}")
    else:
        try:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(
                    media=item["file_id"],
                    caption=caption,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard
            )
        except Exception as e:
            try:
                await update.callback_query.answer(f"Xato: {e}", show_alert=True)
            except:
                pass

async def handle_gallery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gal_noop":
        return

    if data == "gal_close":
        try:
            await query.message.delete()
        except:
            pass
        return

    if data.startswith("gal_fav_"):
        parts = data.split("_")
        owner_id = int(parts[2])
        index = int(parts[3])
        cid = int(parts[4])

        if query.from_user.id != owner_id:
            await query.answer("Bu sizning kolleksiyangiz emas!", show_alert=True)
            return

        item = await col_db.get_collection_item(cid)
        if item:
            new_fav = not bool(item.get("is_favorite"))
            await col_db.set_favorite(cid, owner_id, new_fav)

        items = await col_db.get_collection(owner_id, limit=100)
        if items:
            await send_gallery_page(update, context, owner_id, items, index, len(items))
        return

    if data.startswith("gal_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
        owner_id = int(parts[1])
        index = int(parts[2])

        if query.from_user.id != owner_id:
            await query.answer("Bu sizning kolleksiyangiz emas!", show_alert=True)
            return

        items = await col_db.get_collection(owner_id, limit=100)
        if not items:
            await query.answer("Kolleksiya bo'sh!", show_alert=True)
            return

        index = max(0, min(index, len(items) - 1))
        await send_gallery_page(update, context, owner_id, items, index, len(items))
