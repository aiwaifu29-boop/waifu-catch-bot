import time
from collections import defaultdict

flood_tracker = defaultdict(list)

async def check_flood(user_id: int, group_id: int, context) -> bool:
    from database import users as user_db
    from database.db import DB_PATH
    import aiosqlite

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT flood_until FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0] and int(row[0]) > int(time.time()):
            return True

    now = time.time()
    key = f"{user_id}_{group_id}"
    flood_tracker[key] = [t for t in flood_tracker[key] if now - t < 30]
    flood_tracker[key].append(now)

    if len(flood_tracker[key]) >= 20:
        flood_until = int(now + 1800)
        await user_db.set_flood_until(user_id, flood_until)
        flood_tracker[key].clear()

        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=(
                    f"⚠️ <b>Flood aniqlandi!</b>\n\n"
                    f"Sizning xabarlaringiz <b>30 daqiqa</b> davomida spawn hisoblagichiga qo'shilmaydi.\n\n"
                    f"Bu vaqt ichida:\n"
                    f"• Xabarlari spawn hisobiga kirmaydi\n"
                    f"• Waifu topa olmaysiz\n"
                    f"• Coin ololmaysiz"
                ),
                parse_mode="HTML"
            )
        except:
            pass
        return True

    return False
