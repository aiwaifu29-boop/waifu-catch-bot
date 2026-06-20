from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from database import collections as col_db
from database import users as user_db
from utils.helpers import get_rarity_emoji, RARITY_ORDER
import os

BOT_USERNAME = os.environ.get('BOT_USERNAME', 'YourBot')


def _build_caption(items: list, index: int, owner_name: str) -> str:
    item = items[index]
    total = len(items)
    emoji = get_rarity_emoji(item['rarity'])
    fav = '⭐ ' if item.get('is_favorite') else ''

    # Favorite waifu (top)
    fav_item = next((it for it in items if it.get('is_favorite')), items[0])
    fav_emoji = get_rarity_emoji(fav_item['rarity'])

    # Waifu ro'yxati — 8 ta ko'rsatiladi, aktiv turgan belgilanadi
    start = max(0, index - 3)
    end = min(total, start + 8)
    if end - start < 8:
        start = max(0, end - 8)
    list_lines = []
    for i in range(start, end):
        it = items[i]
        e = get_rarity_emoji(it['rarity'])
        fv = '⭐' if it.get('is_favorite') else ''
        marker = '▶️' if i == index else ' '
        list_lines.append(f"{marker}{e}{fv} <b>{it['name']}</b> | <code>#{it['collection_id']}</code>")

    caption = (
        f'🎴 <b>{owner_name}</b> — kolleksiya [{index+1}/{total}]\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'{emoji} {fav}<b>{item["name"]}</b>\n'
        f'🎌 {item["anime"]}\n'
        f'⭐ {item["rarity"]}\n'
        f'🆔 <code>#{item["collection_id"]}</code>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        + '\n'.join(list_lines)
        + (f'\n<i>...va yana {total-end} ta boshqa</i>' if end < total else '')
    )
    return caption


def _build_keyboard(items: list, index: int, owner_id: int, bot_username: str) -> InlineKeyboardMarkup:
    total = len(items)
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton('⬅️', callback_data=f'gal_{owner_id}_{index-1}'))
    nav_row.append(InlineKeyboardButton(f'📄 {index+1}/{total}', callback_data='gal_noop'))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton('➡️', callback_data=f'gal_{owner_id}_{index+1}'))

    fav_item = items[index]
    fav_btn = InlineKeyboardButton(
        '⭐ Sevimli' if not fav_item.get('is_favorite') else '💔 Olib tashlash',
        callback_data=f'gal_fav_{owner_id}_{index}_{fav_item["collection_id"]}'
    )

    see_btn = InlineKeyboardButton(
        '📖 See Collection',
        switch_inline_query_current_chat=f'collection.{owner_id}'
    )

    return InlineKeyboardMarkup([nav_row, [fav_btn], [see_btn]])


async def cmd_collection_gallery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_db.get_or_create_user(user.id, user.username, user.full_name)

    items = await col_db.get_collection(user.id, limit=200)
    if not items:
        await update.message.reply_text(
            '📦 Kolleksiyangiz hali boʼsh!\n'
            'Guruhdagi waifularni qoʼl kiritib boring 🎮'
        )
        return

    # Favorite waifu birinchi bo'lsin
    fav_index = next((i for i, it in enumerate(items) if it.get('is_favorite')), 0)
    bot_username = context.bot.username or BOT_USERNAME
    caption = _build_caption(items, fav_index, user.full_name or user.username or str(user.id))
    keyboard = _build_keyboard(items, fav_index, user.id, bot_username)

    try:
        await update.message.reply_photo(
            photo=items[fav_index]['file_id'],
            caption=caption,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception as e:
        await update.message.reply_text(f'❌ Rasm yuborishda xato: {e}')


async def handle_gallery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'gal_noop':
        return

    if data == 'gal_close':
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data.startswith('gal_fav_'):
        parts = data.split('_')
        # gal_fav_{owner_id}_{index}_{cid}
        owner_id = int(parts[2])
        index = int(parts[3])
        cid = int(parts[4])

        if user_id != owner_id:
            await query.answer('Bu sizning kolleksiyangiz emas!', show_alert=True)
            return

        item = await col_db.get_collection_item(cid)
        if item:
            new_fav = not bool(item.get('is_favorite'))
            await col_db.set_favorite(cid, owner_id, new_fav)

        items = await col_db.get_collection(owner_id, limit=200)
        if not items:
            return
        index = min(index, len(items) - 1)
        owner = await user_db.get_user(owner_id)
        name = owner.get('full_name') or owner.get('username') or str(owner_id) if owner else str(owner_id)
        bot_username = context.bot.username or BOT_USERNAME
        caption = _build_caption(items, index, name)
        keyboard = _build_keyboard(items, index, owner_id, bot_username)
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=items[index]['file_id'], caption=caption, parse_mode='HTML'),
                reply_markup=keyboard
            )
        except Exception:
            pass
        return

    if data.startswith('gal_'):
        parts = data.split('_')
        if len(parts) < 3:
            return
        owner_id = int(parts[1])
        index = int(parts[2])

        if user_id != owner_id:
            await query.answer('Bu sizning kolleksiyangiz emas!', show_alert=True)
            return

        items = await col_db.get_collection(owner_id, limit=200)
        if not items:
            await query.answer('Kolleksiya boʼsh!', show_alert=True)
            return

        index = max(0, min(index, len(items) - 1))
        owner = await user_db.get_user(owner_id)
        name = owner.get('full_name') or owner.get('username') or str(owner_id) if owner else str(owner_id)
        bot_username = context.bot.username or BOT_USERNAME
        caption = _build_caption(items, index, name)
        keyboard = _build_keyboard(items, index, owner_id, bot_username)
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=items[index]['file_id'], caption=caption, parse_mode='HTML'),
                reply_markup=keyboard
            )
        except Exception as e:
            try:
                await query.answer(f'Xato: {e}', show_alert=True)
            except Exception:
                pass
