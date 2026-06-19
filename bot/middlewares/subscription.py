from database.groups import get_required_channels
from telegram import Update
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
        lines = ["❌ <b>Botdan foydalanish uchun quyidagilarga obuna bo'ling:</b>\n"]
        for ch in not_subscribed:
            lines.append(f"• {ch['channel_name']} — {ch['channel_id']}")
        lines.append("\nObuna bo'lgach, yana urinib ko'ring.")

        try:
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        except:
            pass
        return False

    return True
