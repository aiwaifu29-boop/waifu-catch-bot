from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from database import waifus as waifu_db
from utils.helpers import get_rarity_emoji, RARITY_ORDER


# ─────────────────────────────────────────────
#  USER COLLECTION
# ─────────────────────────────────────────────

async def cmd_collection_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    from middlewares.subscription import check_subscription
    if not await check_subscription(update, context):
        return

    items = await col_db.get_collection(user.id, limit=200)
    if not items:
        await update.message.reply_text(
            "📦 Kolleksiyangiz hali bo'sh!\n"
            "Guruhdagi waifularni qo'lga kiriting."
        )
        return

    total = len(items)
    # Start from favorite waifu if exists, else index 0
    start_index = 0
    for i, it in enumerate(items):
        if it.get("is_favorite"):
            start_index = i
            break

    await send_collection_page(update, context, user.id, items, start_index, total)


async def send_collection_page(update, context, user_id: int, items: list, index: int, total: int):
    item = items[index]
    emoji = get_rarity_emoji(item["rarity"])
    fav = "⭐ " if item.get("is_favorite") else ""

    # Build compact waifu list (nearby items)
    start = max(0, index - 2)
    end = min(total, index + 4)
    list_lines = []
    for i in range(start, end):
        it = items[i]
        e = get_rarity_emoji(it["rarity"])
        marker = "▶️" if i == index else "   "
        fv = "⭐" if it.get("is_favorite") else ""
        list_lines.append(f"{marker}{e}{fv} {it['name']}")
    if total > 6:
        list_lines.append("   ...")

    caption = (
        f"🎴 <b>KOLLEKSIYA</b> [{index+1}/{total}]\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} {fav}<b>{item['name']}</b>\n"
        f"🎌 {item['anime']}\n"
        f"⭐ {item['rarity']}\n"
        f"🆔 <code>{item['collection_id']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Ro'yxat:</b>\n" + "\n".join(list_lines)
    )

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"gal_{user_id}_{index-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {index+1}/{total}", callback_data="gal_noop"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"gal_{user_id}_{index+1}"))

    fav_label = "⭐ Sevimli" if not item.get("is_favorite") else "💔 Olib tashlash"
    action_row = [
        InlineKeyboardButton(fav_label, callback_data=f"gal_fav_{user_id}_{index}_{item['collection_id']}"),
        InlineKeyboardButton("❌ Yopish", callback_data="gal_close"),
    ]
    gallery_row = [
        InlineKeyboardButton("🗂 Bot Galereyasi", callback_data="gal_pub_0"),
    ]

    keyboard = InlineKeyboardMarkup([nav_row, action_row, gallery_row])

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
            except Exception:
                pass


# ─────────────────────────────────────────────
#  PUBLIC BOT GALLERY  (barcha waifular)
# ─────────────────────────────────────────────

async def send_public_gallery_page(update, context, offset: int):
    total_count = await waifu_db.count_all_waifus()
    if total_count == 0:
        try:
            await update.callback_query.answer("Bot galereyasi bo'sh!", show_alert=True)
        except Exception:
            pass
        return

    offset = max(0, min(offset, total_count - 1))
    waifus = await waifu_db.get_all_waifus(limit=1, offset=offset)
    if not waifus:
        try:
            await update.callback_query.answer("Waifu topilmadi!", show_alert=True)
        except Exception:
            pass
        return

    w = waifus[0]
    emoji = get_rarity_emoji(w["rarity"])

    caption = (
        f"🗂 <b>BOT GALEREYASI</b> [{offset+1}/{total_count}]\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>{w['name']}</b>\n"
        f"🎌 Anime: <b>{w['anime']}</b>\n"
        f"⭐ Tur: <b>{w['rarity']}</b>\n"
        f"🆔 ID: <code>{w['waifu_id']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Har kim ko'rishi mumkin</i>"
    )

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"gal_pub_{offset-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {offset+1}/{total_count}", callback_data="gal_noop"))
    if offset < total_count - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"gal_pub_{offset+1}"))

    close_row = [InlineKeyboardButton("❌ Yopish", callback_data="gal_close")]
    keyboard = InlineKeyboardMarkup([nav_row, close_row])

    try:
        await update.callback_query.edit_message_media(
            media=InputMediaPhoto(
                media=w["file_id"],
                caption=caption,
                parse_mode="HTML"
            ),
            reply_markup=keyboard
        )
    except Exception:
        try:
            await update.callback_query.message.reply_photo(
                photo=w["file_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            await update.callback_query.answer(f"Xato: {e}", show_alert=True)


# ─────────────────────────────────────────────
#  CALLBACK HANDLER
# ─────────────────────────────────────────────

async def handle_gallery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gal_noop":
        return

    if data == "gal_close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # Public bot gallery
    if data.startswith("gal_pub_"):
        try:
            offset = int(data.split("_")[2])
        except (IndexError, ValueError):
            offset = 0
        await send_public_gallery_page(update, context, offset)
        return

    # User collection favorite toggle
    if data.startswith("gal_fav_"):
        parts = data.split("_")
        # gal_fav_{user_id}_{index}_{cid}
        try:
            owner_id = int(parts[2])
            index = int(parts[3])
            cid = int(parts[4])
        except (IndexError, ValueError):
            return

        if query.from_user.id != owner_id:
            await query.answer("Bu sizning kolleksiyangiz emas!", show_alert=True)
            return

        item = await col_db.get_collection_item(cid)
        if item:
            new_fav = not bool(item.get("is_favorite"))
            await col_db.set_favorite(cid, owner_id, new_fav)

        items = await col_db.get_collection(owner_id, limit=200)
        if items:
            index = max(0, min(index, len(items) - 1))
            await send_collection_page(update, context, owner_id, items, index, len(items))
        return

    # User collection navigation: gal_{user_id}_{index}
    if data.startswith("gal_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
        try:
            owner_id = int(parts[1])
            index = int(parts[2])
        except (IndexError, ValueError):
            return

        if query.from_user.id != owner_id:
            await query.answer("Bu sizning kolleksiyangiz emas!", show_alert=True)
            return

        items = await col_db.get_collection(owner_id, limit=200)
        if not items:
            await query.answer("Kolleksiya bo'sh!", show_alert=True)
            return

        index = max(0, min(index, len(items) - 1))
        await send_collection_page(update, context, owner_id, items, index, len(items))
