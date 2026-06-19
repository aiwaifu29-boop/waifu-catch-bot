from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from database import waifus as waifu_db
from utils.helpers import get_rarity_emoji, RARITY_ORDER


def _bot_username(context) -> str:
    try:
        return context.bot.username or ""
    except Exception:
        return ""


# ─────────────────────────────────────────────
#  /collection — faqat sevimli waifu + inline tugma
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

    # Sevimli waifuni topish
    favorite = next((it for it in items if it.get("is_favorite")), None)
    show_item = favorite or items[0]
    is_fav = bool(show_item.get("is_favorite"))

    emoji = get_rarity_emoji(show_item["rarity"])
    fav_mark = "⭐ " if is_fav else ""

    caption = (
        f"🎴 <b>KOLLEKSIYA</b> — jami {total} ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} {fav_mark}<b>{show_item['name']}</b>\n"
        f"🎌 {show_item['anime']}\n"
        f"⭐ {show_item['rarity']}\n"
        f"🆔 <code>{show_item['collection_id']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{'⭐ <i>Sevimli waifu</i>' if is_fav else '<i>Sevimli yo\'q — /favorite ID bilan belgilang</i>'}"
    )

    bot_username = _bot_username(context)
    # switch_inline_query_current_chat tugmasi: chat maydoniga "@Bot collection.user_id" yozadi
    inline_btn = InlineKeyboardButton(
        "📖 Kolleksiyamni ko'rish",
        switch_inline_query_current_chat=f"collection.{user.id}"
    )
    fav_label = "💔 Sevimlilikdan olib tashlash" if is_fav else "⭐ Sevimli qilish"
    fav_btn = InlineKeyboardButton(
        fav_label,
        callback_data=f"gal_fav_{user.id}_{show_item['collection_id']}"
    )
    keyboard = InlineKeyboardMarkup([
        [inline_btn],
        [fav_btn],
    ])

    try:
        await update.message.reply_photo(
            photo=show_item["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Rasm yuborishda xato: {e}")


# ─────────────────────────────────────────────
#  CALLBACK: sevimli toggle
# ─────────────────────────────────────────────

async def handle_gallery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gal_noop":
        return

    # gal_fav_{user_id}_{collection_id}
    if data.startswith("gal_fav_"):
        parts = data.split("_")
        try:
            owner_id = int(parts[2])
            cid = int(parts[3])
        except (IndexError, ValueError):
            return

        if query.from_user.id != owner_id:
            await query.answer("Bu sizning kolleksiyangiz emas!", show_alert=True)
            return

        item = await col_db.get_collection_item(cid)
        if item:
            new_fav = not bool(item.get("is_favorite"))
            await col_db.set_favorite(cid, owner_id, new_fav)
            status = "⭐ Sevimli sifatida belgilandi!" if new_fav else "💔 Sevimlilikdan olib tashlandi."
            await query.answer(status, show_alert=True)
        return
