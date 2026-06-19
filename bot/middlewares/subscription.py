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
        except:
            pass

    if not_subscribed:
        lines = ["🔒 <b>Botdan foydalanish uchun obuna bo'ling:</b>\n"]
        buttons = []
        for ch in not_subscribed:
            name = ch.get("channel_name") or ch["channel_id"]
            lines.append(f"• <b>{name}</b>")
            cid = ch["channel_id"]
            if not cid.startswith("-"):
                link = f"https://t.me/{cid.lstrip('@')}"
                buttons.append([InlineKeyboardButton(f"📢 {name}", url=link)])

        lines.append("\nObuna bo'lgach, buyruqni qayta yuboring.")
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        try:
            if update.message:
                await update.message.reply_text(
                    "\n".join(lines),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        except:
            pass
        return False

    return True
