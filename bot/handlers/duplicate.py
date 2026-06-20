from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import cards as cards_db
from utils.helpers import get_rarity_emoji

RARITY_ORDER = cards_db.RARITY_ORDER
RARITY_EMOJI = cards_db.RARITY_EMOJI


def _build_main_text(dupes: dict, cards: dict) -> str:
    lines = [
        '🃏 <b>DUPLICATE TIZIMI</b>',
        '━━━━━━━━━━━━━━━━━━━━',
        '',
        '<b>📦 Duplicatelaringiz:</b>',
    ]
    any_dupes = False
    for r in RARITY_ORDER:
        d = dupes.get(r, 0)
        if d > 0:
            e = RARITY_EMOJI[r]
            ready = d // 10
            bar = '🟩' * min(d, 10) + '⬜' * max(0, 10 - d)
            lines.append(f'{e} {r}: <b>{d}</b> ta  {bar}')
            if ready > 0:
                lines.append(f'   ✅ {ready} ta karta olishingiz mumkin!')
            any_dupes = True
    if not any_dupes:
        lines.append('   Hali duplicate yoq.')
    lines.append('')
    lines.append('<b>🎴 Kartalaringiz:</b>')
    any_cards = False
    for r in RARITY_ORDER:
        c = cards.get(r, 0)
        if c > 0:
            e = RARITY_EMOJI[r]
            lines.append(f'{e} {r}: <b>{c}</b> ta karta')
            any_cards = True
    if not any_cards:
        lines.append('   Hali karta yoq.')
    lines.append('')
    lines.append('<i>10 duplicate = 1 karta | Karta = random waifu</i>')
    lines.append('<i>10 karta = 1 yuqori rarity karta</i>')
    return '\n'.join(lines)


def _build_keyboard(dupes: dict, cards: dict, user_id: int) -> InlineKeyboardMarkup:
    rows = []
    # Exchange duplicate buttons
    xchg_row = []
    for r in RARITY_ORDER:
        if dupes.get(r, 0) >= 10:
            e = RARITY_EMOJI[r]
            xchg_row.append(InlineKeyboardButton(
                f'{e} {r[:3]}→🃏',
                callback_data=f'dup_xchg_{user_id}_{r}'
            ))
            if len(xchg_row) == 2:
                rows.append(xchg_row)
                xchg_row = []
    if xchg_row:
        rows.append(xchg_row)
    # Use card buttons
    use_row = []
    for r in RARITY_ORDER:
        if cards.get(r, 0) >= 1:
            e = RARITY_EMOJI[r]
            use_row.append(InlineKeyboardButton(
                f'{e} Karta ishlatish',
                callback_data=f'dup_use_{user_id}_{r}'
            ))
            if len(use_row) == 2:
                rows.append(use_row)
                use_row = []
    if use_row:
        rows.append(use_row)
    # Upgrade card buttons
    up_row = []
    for i, r in enumerate(RARITY_ORDER[:-1]):
        if cards.get(r, 0) >= 10:
            e1 = RARITY_EMOJI[r]
            e2 = RARITY_EMOJI[RARITY_ORDER[i+1]]
            up_row.append(InlineKeyboardButton(
                f'{e1}→{e2} Upgrade',
                callback_data=f'dup_up_{user_id}_{r}'
            ))
            if len(up_row) == 2:
                rows.append(up_row)
                up_row = []
    if up_row:
        rows.append(up_row)
    # Refresh
    rows.append([InlineKeyboardButton('🔄 Yangilash', callback_data=f'dup_refresh_{user_id}')])
    return InlineKeyboardMarkup(rows)


async def cmd_duplicate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Guruhda — PM ga yo'naltirish tugmasini ko'rsatamiz
    if chat.type in ('group', 'supergroup'):
        bot_username = context.bot.username
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                '🃏 Duplicate menyusini ochish',
                url=f'https://t.me/{bot_username}?start=dup'
            )
        ]])
        await update.message.reply_text(
            '🃏 <b>Duplicate tizimi</b>\n\nDuplicatelarni kartaga almashtirish va kartadan waifu olish uchun botga o\'ting!',
            parse_mode='HTML', reply_markup=kb
        )
        return

    # PM da — to'liq menyu
    dupes = await cards_db.get_duplicate_stats(user.id)
    cards = await cards_db.get_card_counts(user.id)
    text = _build_main_text(dupes, cards)
    kb = _build_keyboard(dupes, cards, user.id)
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=kb)


async def handle_dup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    caller = query.from_user.id

    parts = data.split('_')
    # Format: dup_{action}_{owner_id}_{rarity...}
    action = parts[1]
    owner_id = int(parts[2])

    if caller != owner_id:
        await query.answer('Bu sizning menyungiz emas!', show_alert=True)
        return

    if action == 'refresh':
        dupes = await cards_db.get_duplicate_stats(owner_id)
        cards = await cards_db.get_card_counts(owner_id)
        text = _build_main_text(dupes, cards)
        kb = _build_keyboard(dupes, cards, owner_id)
        try:
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=kb)
        except Exception:
            pass
        return

    # rarity = remaining parts joined (e.g. 'Super Rare')
    rarity = '_'.join(parts[3:]).replace('_', ' ')

    if action == 'xchg':
        ok, msg = await cards_db.exchange_duplicates(owner_id, rarity)
        await query.answer(msg, show_alert=True)

    elif action == 'use':
        ok, msg, waifu = await cards_db.use_card(owner_id, rarity)
        if ok and waifu:
            e = get_rarity_emoji(waifu['rarity'])
            full_msg = (
                f'🎴 <b>Yangi waifu!</b>\n'
                f'━━━━━━━━━━━━━━━━━━━━\n'
                f'{e} <b>{waifu["name"]}</b>\n'
                f'🎌 {waifu["anime"]}\n'
                f'⭐ {waifu["rarity"]}\n'
                f'━━━━━━━━━━━━━━━━━━━━'
            )
            try:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=waifu['file_id'],
                    caption=full_msg,
                    parse_mode='HTML'
                )
            except Exception:
                await query.answer(msg, show_alert=True)
        else:
            await query.answer(msg, show_alert=True)

    elif action == 'up':
        ok, msg = await cards_db.upgrade_cards(owner_id, rarity)
        await query.answer(msg, show_alert=True)

    # Refresh display
    dupes = await cards_db.get_duplicate_stats(owner_id)
    cards_count = await cards_db.get_card_counts(owner_id)
    text = _build_main_text(dupes, cards_count)
    kb = _build_keyboard(dupes, cards_count, owner_id)
    try:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=kb)
    except Exception:
        pass