import os
import re
import sys
import logging

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, filters, ChatMemberHandler
)

from database.db import init_db
from handlers.spawn import handle_message_count, cmd_waifu_catch
from handlers.gallery import cmd_collection_gallery, handle_gallery_callback
from handlers.inline_handler import handle_inline_query
from handlers.user_commands import (
    cmd_start, cmd_help, cmd_profil,
    cmd_daily, cmd_top, cmd_gtop, cmd_search, cmd_anime, cmd_stats,
    cmd_favorite, cmd_history
)
from handlers.trade import cmd_trade, handle_trade_callback
from handlers.gift import cmd_gift, handle_gift_callback
from handlers.market_handler import cmd_sell, cmd_market, cmd_buy, handle_shop_callback
from handlers.admin import (
    cmd_removewaifu, cmd_spawn_admin, cmd_broadcast,
    cmd_addadmin, cmd_removeadmin, cmd_ban_user, cmd_unban_user,
    cmd_givecoins, cmd_givewaifu, cmd_event, cmd_approvegroup, cmd_denygroup,
    cmd_addchannel, cmd_removechannel, cmd_panel, cmd_setspawn,
    cmd_addgroup_bypass, received_rarity,
    handle_panel_button, handle_admin_input, handle_admin_photo, handle_admin_callback,
    ALL_PANEL_BUTTONS,
    cmd_settitle, cmd_removetitle, cmd_titles
)
from handlers.group_management import handle_new_chat_member, handle_chat_member
from middlewares.moderation import cmd_warn, cmd_mute, cmd_unmute, cmd_kick, cmd_ban, cmd_unban
from middlewares.subscription import handle_subscription_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

GROUP_COMMANDS = [
    BotCommand("waifu", "Waifu tutish: /waifu [ism]"),
    BotCommand("collection", "Kolleksiyangiz"),
    BotCommand("profil", "Profilingiz"),
    BotCommand("daily", "Kunlik mukofot"),
    BotCommand("top", "Global reyting"),
    BotCommand("gtop", "Guruh reytingi"),
    BotCommand("trade", "Waifu savdosi"),
    BotCommand("gift", "Waifu sovg'a qilish"),
    BotCommand("sell", "Bozorga qo'yish"),
    BotCommand("market", "Bugungi do'kon"),
    BotCommand("buy", "Do'kondan sotib olish"),
    BotCommand("search", "Waifu qidirish"),
    BotCommand("help", "Yordam"),
]

PRIVATE_COMMANDS = [
    BotCommand("start", "Botni boshlash"),
    BotCommand("profil", "Profilingiz"),
    BotCommand("collection", "Kolleksiyangiz"),
    BotCommand("daily", "Kunlik mukofot"),
    BotCommand("top", "Global reyting"),
    BotCommand("market", "Bugungi do'kon"),
    BotCommand("search", "Waifu qidirish"),
    BotCommand("stats", "Statistika"),
    BotCommand("help", "Yordam"),
]


async def cmd_start_handler(update: Update, context):
    """Start — deep link ko'llab-quvvatlaydi: /start col_USER_ID"""
    args = context.args or []
    if args:
        param = args[0]
        if param.startswith("col_"):
            try:
                owner_id = int(param[4:])
            except ValueError:
                pass
            else:
                await show_user_collection_by_id(update, context, owner_id)
                return
    await cmd_start(update, context)


async def show_user_collection_by_id(update, context, owner_id: int):
    """Deep link orqali boshqa foydalanuvchi kolleksiyasini ko'rish."""
    from database import users as user_db, collections as col_db
    from utils.helpers import get_rarity_emoji
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    owner = await user_db.get_user(owner_id)
    if not owner:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return

    items = await col_db.get_collection(owner_id, limit=200)
    owner_name = owner.get("full_name") or owner.get("username") or str(owner_id)

    if not items:
        await update.message.reply_text(
            f"📦 <b>{owner_name}</b>ning kolleksiyasi bo'sh.", parse_mode="HTML"
        )
        return

    show_item = next((it for it in items if it.get("is_favorite")), items[0])
    emoji = get_rarity_emoji(show_item["rarity"])
    fav_mark = "⭐ " if show_item.get("is_favorite") else ""

    caption = (
        f"🎴 <b>{owner_name}</b>ning kolleksiyasi — jami {len(items)} ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} {fav_mark}<b>{show_item['name']}</b>\n"
        f"🎌 {show_item['anime']}\n"
        f"⭐ {show_item['rarity']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Quyidagi tugmani bosing</i>"
    )

    inline_btn = InlineKeyboardButton(
        "📖 To'liq kolleksiyani ko'rish",
        switch_inline_query_current_chat=f"collection.{owner_id}"
    )
    keyboard = InlineKeyboardMarkup([[inline_btn]])

    try:
        await update.message.reply_photo(
            photo=show_item["file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


async def post_init(application: Application):
    await init_db()
    logger.info("Database initialized")

    god_id = os.environ.get("GOD_ADMIN_ID")
    if god_id:
        try:
            import aiosqlite
            from database.db import DB_PATH
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO admins (user_id, username, added_by) VALUES (?,?,?)",
                    (int(god_id), "god_admin", int(god_id))
                )
                await db.commit()
            logger.info(f"God admin {god_id} registered")
        except Exception as e:
            logger.error(f"God admin setup error: {e}")

    try:
        await application.bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
        await application.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    except Exception as e:
        logger.warning(f"Could not set commands: {e}")


def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(post_init).build()

    # ── Start ──
    app.add_handler(CommandHandler("start", cmd_start_handler))

    # ── Foydalanuvchi buyruqlari ──
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profil", cmd_profil))
    app.add_handler(CommandHandler("collection", cmd_collection_gallery))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("gtop", cmd_gtop))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("anime", cmd_anime))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("favorite", cmd_favorite))
    app.add_handler(CommandHandler("history", cmd_history))

    # ── Waifu catch ──
    app.add_handler(CommandHandler("waifu", cmd_waifu_catch))

    # ── Trade va sovg'a ──
    app.add_handler(CommandHandler("trade", cmd_trade))
    app.add_handler(CommandHandler("gift", cmd_gift))

    # ── Bozor / Do'kon ──
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("buy", cmd_buy))

    # ── Admin buyruqlari ──
    app.add_handler(CommandHandler("removewaifu", cmd_removewaifu))
    app.add_handler(CommandHandler("spawn", cmd_spawn_admin))
    app.add_handler(CommandHandler("setspawn", cmd_setspawn))
    app.add_handler(CommandHandler("addgroup", cmd_addgroup_bypass))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("banuser", cmd_ban_user))
    app.add_handler(CommandHandler("unbanuser", cmd_unban_user))
    app.add_handler(CommandHandler("givecoins", cmd_givecoins))
    app.add_handler(CommandHandler("givewaifu", cmd_givewaifu))
    app.add_handler(CommandHandler("event", cmd_event))
    app.add_handler(CommandHandler("approvegroup", cmd_approvegroup))
    app.add_handler(CommandHandler("denygroup", cmd_denygroup))
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))
    app.add_handler(CommandHandler("removechannel", cmd_removechannel))
    app.add_handler(CommandHandler("panel", cmd_panel))
    app.add_handler(CommandHandler("settitle", cmd_settitle))
    app.add_handler(CommandHandler("removetitle", cmd_removetitle))
    app.add_handler(CommandHandler("titles", cmd_titles))

    # ── Moderatsiya ──
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))

    # ── Inline query ──
    app.add_handler(InlineQueryHandler(handle_inline_query))

    # ── Callback handlers (aniqroqdan umumiyga) ──
    app.add_handler(CallbackQueryHandler(handle_subscription_check, pattern="^sub_check$"))
    app.add_handler(CallbackQueryHandler(received_rarity, pattern="^rarity_"))
    app.add_handler(CallbackQueryHandler(handle_trade_callback, pattern="^trade_"))
    app.add_handler(CallbackQueryHandler(handle_gift_callback, pattern="^gift_"))
    app.add_handler(CallbackQueryHandler(handle_gallery_callback, pattern="^gal_"))
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern="^shop_"))
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^adm_"))

    # ── Admin panel tugmalari (ReplyKeyboard) ──
    panel_pattern = "^(" + "|".join(re.escape(btn) for btn in ALL_PANEL_BUTTONS) + ")$"
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(panel_pattern),
        handle_panel_button
    ))

    # ── Admin foto (waifu qo'shish, private chat) ──
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_admin_photo
    ))

    # ── Admin matn kiritish (state machine, private chat) ──
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_admin_input
    ))

    # ── Guruh hodisalari ──
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_member))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # ── Xabar sanagichi (guruhlar, oxirgi) ──
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handle_message_count
    ))

    return app


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found!")
        sys.exit(1)

    webhook_url = os.environ.get("WEBHOOK_URL", "")
    port = int(os.environ.get("PORT", 8443))

    app = build_app(token)

    if webhook_url:
        logger.info(f"Starting webhook mode: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            url_path=token,
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting polling mode...")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
