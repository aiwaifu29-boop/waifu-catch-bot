from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationHandlerStop
import os
import time

_ban_cache: dict = {}
_CACHE_TTL = 60


async def _is_banned(user_id: int) -> tuple:
    now = time.time()
    cached = _ban_cache.get(user_id)
    if cached and now - cached["ts"] < _CACHE_TTL:
        return cached["banned"], cached.get("reason", "")
    try:
        from database import users as user_db
        user = await user_db.get_user(user_id)
        if user and user.get("is_banned"):
            _ban_cache[user_id] = {"banned": True, "reason": user.get("ban_reason") or "", "ts": now}
            return True, user.get("ban_reason") or ""
    except Exception:
        pass
    _ban_cache[user_id] = {"banned": False, "reason": "", "ts": now}
    return False, ""


def clear_ban_cache(user_id: int):
    _ban_cache.pop(user_id, None)


BAN_TEXT = (
    "🚫 <b>Siz ban olgansiz!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Bu botdan foydalanish huquqingiz cheklangan.\n"
    "Murojaat uchun: @admin_username\n"
    "━━━━━━━━━━━━━━━━━━━━"
)


async def ban_check_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    god_id = os.environ.get("GOD_ADMIN_ID", "")
    try:
        if god_id and user.id == int(god_id):
            return
    except ValueError:
        pass
    banned, reason = await _is_banned(user.id)
    if not banned:
        return
    if update.message or update.callback_query:
        ban_msg = BAN_TEXT
        if reason:
            ban_msg += f"\n📋 <b>Sabab:</b> {reason}"
        try:
            if update.message:
                await update.message.reply_text(ban_msg, parse_mode="HTML")
            elif update.callback_query:
                await update.callback_query.answer(
                    "🚫 Siz ban olgansiz! Buyruqlardan foydalana olmaysiz.", show_alert=True
                )
        except Exception:
            pass
    raise ApplicationHandlerStop
