from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationHandlerStop
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "waifu_bot.db")

BAN_TEXT = (
    "🚫 <b>Siz ban olgansiz!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Bu botdan foydalanish huquqingiz cheklangan.\n"
    "Murojaat uchun: @admin_username\n"
    "━━━━━━━━━━━━━━━━━━━━"
)

_ban_cache: dict = {}
_CACHE_TTL = 60  # sekund


async def _is_banned(user_id: int) -> tuple:
    """(is_banned: bool, reason: str)"""
    import time
    now = time.time()
    cached = _ban_cache.get(user_id)
    if cached and now - cached["ts"] < _CACHE_TTL:
        return cached["banned"], cached.get("reason", "")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT is_banned, ban_reason FROM users WHERE user_id=?", (user_id,)
            )
            row = await cursor.fetchone()
            if row and row["is_banned"]:
                _ban_cache[user_id] = {"banned": True, "reason": row["ban_reason"] or "", "ts": now}
                return True, row["ban_reason"] or ""
    except Exception:
        pass
    _ban_cache[user_id] = {"banned": False, "reason": "", "ts": now}
    return False, ""


def clear_ban_cache(user_id: int):
    _ban_cache.pop(user_id, None)


async def ban_check_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har bir xabar/buyruqdan oldin ban tekshiruvi. group=-1 da ishlatiladi."""
    user = update.effective_user
    if not user:
        return

    # Adminlar hech qachon ban bo'lmaydi (God Admin)
    god_id = os.environ.get("GOD_ADMIN_ID", "")
    try:
        if god_id and user.id == int(god_id):
            return
    except ValueError:
        pass

    banned, reason = await _is_banned(user.id)
    if not banned:
        return

    # Faqat buyruq yoki xabarda xabar yuboramiz
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
