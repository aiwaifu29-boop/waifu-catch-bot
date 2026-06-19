import os
import sys
import logging

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ChatMemberHandler
)

from database.db import init_db
from handlers.spawn import handle_message_count, cmd_waifu_catch
from handlers.gallery import cmd_collection_gallery, handle_gallery_callback
from handlers.user_commands import (
    cmd_start, cmd_help, cmd_profil,
    cmd_daily, cmd_top, cmd_search, cmd_anime, cmd_stats,
    cmd_favorite, cmd_history
)
from handlers.trade import cmd_trade, handle_trade_callback
from handlers.gift import cmd_gift, handle_gift_callback
from handlers.market_handler import cmd_sell, cmd_market, cmd_buy
from handlers.admin import (
    cmd_removewaifu, cmd_spawn_admin, cmd_broadcast,
    cmd_addadmin, cmd_removeadmin, cmd_ban_user, cmd_unban_user,
    cmd_givecoins, cmd_givewaifu, cmd_event, cmd_approvegroup, cmd_denygroup,
    cmd_addchannel, cmd_removechannel, cmd_panel, cmd_setspawn,
    cmd_addgroup_bypass, get_addwaifu_handler, received_rarity
)
from handlers.group_management import handle_new_chat_member, handle_chat_member
from middlewares.moderation import cmd_warn, cmd_mute, cmd_unmute, cmd_kick, cmd_ban, cmd_unban

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

GROUP_COMMANDS = [
    BotCommand("waifu", "Waifu tutish: /waifu [ism]"),
    BotCommand("collection", "Kolleksiyangiz va galereya"),
    BotCommand("profil", "Profilingiz"),
    BotCommand("daily", "Kunlik mukofot"),
    BotCommand("top", "Reyting"),
    BotCommand("trade", "Waifu savdosi"),
    BotCommand("gift", "Waifu sovg'a qilish"),
    BotCommand("sell", "Bozorga qo'yish"),
    BotCommand("market", "Bozor"),
    BotCommand("buy", "Bozordan sotib olish"),
    BotCommand("search", "Waifu qidirish"),
    BotCommand("help", "Yordam"),
]

PRIVATE_COMMANDS = [
    BotCommand("start", "Botni boshlash"),
    BotCommand("profil", "Profilingiz"),
    BotCommand("collection", "Kolleksiyangiz"),
    BotCommand("daily", "Kunlik mukofot"),
    BotCommand("top", "Reyting"),
    BotCommand("market", "Bozor"),
    BotCommand("search", "Waifu qidirish"),
    BotCommand("stats", "Statistika"),
    BotCommand("help", "Yordam"),
]

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
                    "INSERT OR IGNORE INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
                    (int(god_id), "god_admin", int(god_id))
                )
                await db.commit()
            logger.info(f"God admin {god_id} registered")
        except Exception as e:
            logger.error(f"God admin setup error: {e}")

    # Set bot commands for different scopes
    try:
        await application.bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
        await application.bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.warning(f"Could not set commands: {e}")


def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(post_init).build()

    # Admin conversation handler
    app.add_handler(get_addwaifu_handler())

    # User commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profil", cmd_profil))
    app.add_handler(CommandHandler("collection", cmd_collection_gallery))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("anime", cmd_anime))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("favorite", cmd_favorite))
    app.add_handler(CommandHandler("history", cmd_history))

    # Waifu catch command
    app.add_handler(CommandHandler("waifu", cmd_waifu_catch))

    # Trade & gift
    app.add_handler(CommandHandler("trade", cmd_trade))
    app.add_handler(CommandHandler("gift", cmd_gift))

    # Market
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("buy", cmd_buy))

    # Admin commands
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

    # Moderation
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_trade_callback, pattern="^trade_"))
    app.add_handler(CallbackQueryHandler(handle_gift_callback, pattern="^gift_"))
    app.add_handler(CallbackQueryHandler(received_rarity, pattern="^rarity_"))
    app.add_handler(CallbackQueryHandler(handle_gallery_callback, pattern="^gal_"))

    # Group join events
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_member))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Message counter (groups only)
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
