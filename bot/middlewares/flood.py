import time
import asyncio
from collections import defaultdict

# Flood sozlamalari
FLOOD_LIMIT = 7       # Qancha xabar
FLOOD_WINDOW = 7      # Qancha sekund ichida
BAN_DURATION = 30 * 60  # 30 daqiqa (sekund)

_msg_times: dict = defaultdict(list)   # key=(user_id, group_id) -> [timestamps]
_flood_banned: dict = {}               # key=(user_id, group_id) -> ban_until
_warned: set = set()                   # key=(user_id, group_id) -> warned this episode


async def check_flood(user_id: int, group_id: int, context) -> bool:
    """
    True qaytaradi agar user flood qilgan va ban ostida bo'lsa.
    False qaytaradi agar normal ishlayotgan bo'lsa.
    """
    key = (user_id, group_id)
    now = time.time()

    # Hozirda ban ostidami?
    if key in _flood_banned:
        if now < _flood_banned[key]:
            return True  # Hali ban davom etmoqda
        else:
            # Ban tugadi, tozalaymiz
            del _flood_banned[key]
            _warned.discard(key)

    # Xabar vaqtlarini yangilaymiz
    times = _msg_times[key]
    times = [t for t in times if now - t < FLOOD_WINDOW]
    times.append(now)
    _msg_times[key] = times

    # Flood chegarasiga yetdimi?
    if len(times) >= FLOOD_LIMIT:
        # Ban qo'yamiz
        _flood_banned[key] = now + BAN_DURATION
        _msg_times[key] = []

        # Birinchi marta ogohlantiramiz
        if key not in _warned:
            _warned.add(key)

            # DB ga yozamiz
            try:
                from database import users as user_db
                await user_db.set_flood_until(user_id, int(now + BAN_DURATION))
            except Exception:
                pass

            # Guruhdagi ogohlantirish
            try:
                sent = await context.bot.send_message(
                    chat_id=group_id,
                    text=(
                        f"⚠️ <b>FLOOD ANIQLANDI!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"Foydalanuvchi juda tez xabar yuboryapti.\n\n"
                        f"Keyingi <b>30 daqiqa</b> davomida:\n"
                        f"• ❌ Spawn hisobiga kirmaydik\n"
                        f"• ❌ Waifu tuta olmaydi\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"<i>Spam va flood oldini olish uchun bu cheklov mavjud.</i>"
                    ),
                    parse_mode="HTML"
                )
                # 30 soniyadan keyin ogohlantirishni o'chiramiz
                async def _del_warn(chat_id, msg_id):
                    await asyncio.sleep(30)
                    try:
                        await context.bot.delete_message(chat_id, msg_id)
                    except Exception:
                        pass
                asyncio.create_task(_del_warn(group_id, sent.message_id))
            except Exception:
                pass

            # 30 daqiqadan keyin warned holatini tozalaymiz
            async def _clear_warned():
                await asyncio.sleep(BAN_DURATION + 60)
                _warned.discard(key)
            asyncio.create_task(_clear_warned())

        return True

    return False


def is_flood_banned(user_id: int, group_id: int) -> bool:
    """Sinxron tekshiruv — flood ban ostidami?"""
    key = (user_id, group_id)
    now = time.time()
    if key in _flood_banned:
        return now < _flood_banned[key]
    return False


def flood_ban_remaining(user_id: int, group_id: int) -> int:
    """Qolgan ban sekundlar"""
    key = (user_id, group_id)
    now = time.time()
    if key in _flood_banned:
        remaining = _flood_banned[key] - now
        return max(0, int(remaining))
    return 0
