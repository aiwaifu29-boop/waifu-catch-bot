from database.groups import get_required_channels
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return True

    channels = await get_required_channels()
    if not channels:
        return True

    not_subscribed = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user.id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(ch)
        except Exception:
            pass

    if not_subscribed:
        lines = ["🔒 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>\n"]
        buttons = []
        for ch in not_subscribed:
            name = ch.get("channel_name") or ch["channel_id"]
            lines.append(f"• <b>{name}</b>")
            cid = ch["channel_id"]
            if not cid.startswith("-"):
                link = f"https://t.me/{cid.lstrip('@')}"
                buttons.append([InlineKeyboardButton(f"📢 {name}", url=link)])

        lines.append("\nObuna bo'lgach, pastdagi tugmani bosing:")
        buttons.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="sub_check")])
        keyboard = InlineKeyboardMarkup(buttons)

        try:
            if update.message:
                await update.message.reply_text(
                    "\n".join(lines),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "\n".join(lines),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        except Exception:
            pass
        return False

    return True


async def handle_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    channels = await get_required_channels()
    if not channels:
        await query.message.delete()
        return

    not_subscribed = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user.id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(ch)
        except Exception:
            pass

    if not_subscribed:
        names = ", ".join(ch.get("channel_name") or ch["channel_id"] for ch in not_subscribed)
        await query.answer(f"❌ Hali obuna bo'lmadingiz: {names}", show_alert=True)
    else:
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.",
        )
