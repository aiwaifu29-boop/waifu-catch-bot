import uuid
from telegram import Update, InlineQueryResultCachedPhoto, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from database import waifus as waifu_db
from utils.helpers import get_rarity_emoji


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inline query handleri.
    Foydalanuvchi "@Bot collection.USER_ID" yozganda chaqiriladi.
    Natijada o'sha foydalanuvchining waifulari InlineQueryResultCachedPhoto
    ko'rinishida qaytariladi — guruhda rasmli kolleksiya sifatida ko'rinadi.
    """
    query = update.inline_query
    if not query:
        return

    text = (query.query or "").strip()

    # Faqat "collection.USER_ID" formatini qabul qilamiz
    if not text.startswith("collection."):
        await query.answer([], cache_time=5)
        return

    # User ID ni ajratib olamiz
    raw_id = text[len("collection."):]
    try:
        owner_id = int(raw_id)
    except ValueError:
        await query.answer([], cache_time=5)
        return

    # Kolleksiyani bazadan yuklaymiz
    items = await col_db.get_collection(owner_id, limit=50)
    if not items:
        # Bo'sh kolleksiya uchun xabar
        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Kolleksiya bo'sh",
            input_message_content=InputTextMessageContent(
                message_text=f"📦 Bu foydalanuvchining kolleksiyasi hali bo'sh."
            ),
            description="Hali hech qanday waifu qo'lga kiritilmagan."
        )
        await query.answer([result], cache_time=10)
        return

    # Egasining ismini olamiz
    owner = await user_db.get_user(owner_id)
    owner_name = "Noma'lum"
    if owner:
        owner_name = owner.get("full_name") or owner.get("username") or str(owner_id)

    # Har bir waifu uchun InlineQueryResultCachedPhoto yaratamiz
    results = []
    for item in items:
        emoji = get_rarity_emoji(item["rarity"])
        is_fav = bool(item.get("is_favorite"))
        fav_mark = "⭐ " if is_fav else ""

        title = f"{emoji} {fav_mark}{item['name']}"
        description = f"{item['anime']} • {item['rarity']}"

        caption = (
            f"🎴 <b>{owner_name}</b>ning kolleksiyasidan\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} {fav_mark}<b>{item['name']}</b>\n"
            f"🎌 {item['anime']}\n"
            f"⭐ {item['rarity']}\n"
            f"🆔 <code>{item['collection_id']}</code>"
        )

        results.append(
            InlineQueryResultCachedPhoto(
                id=str(uuid.uuid4()),
                photo_file_id=item["file_id"],
                title=title,
                description=description,
                caption=caption,
                parse_mode="HTML"
            )
        )

    # Telegramga maksimal 50 ta natija yuboramiz
    await query.answer(
        results[:50],
        cache_time=30,
        is_personal=True
    )
