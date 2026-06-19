from telegram import Update
from telegram.ext import ContextTypes
from database import groups as grp_db
from database import logs as log_db

async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat = update.effective_chat
    bot = await context.bot.get_me()
    new_members = update.message.new_chat_members or []
    for member in new_members:
        if member.id == bot.id:
            await on_bot_added(context, chat)

async def on_bot_added(context, chat):
    group_id = chat.id
    group_name = chat.title

    group = await grp_db.get_or_create_group(group_id, group_name)

    # Check skip_member_check flag
    skip_check = group.get("skip_member_check", 0)

    if not skip_check:
        try:
            count = await context.bot.get_chat_member_count(group_id)
        except:
            count = 999

        if count < 20:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text="❌ Bu bot faqat 20 yoki undan ko'p a'zoga ega guruhlarda ishlaydi.",
                )
                await context.bot.leave_chat(group_id)
            except:
                pass
            return

    await log_db.add_log("group_join", group_id=group_id, details=f"name={group_name}")

    try:
        await context.bot.send_message(
            chat_id=group_id,
            text=(
                "👋 <b>Waifu Catch Bot guruhga qo'shildi!</b>\n\n"
                "⚠️ Bot ishlashi uchun guruhda <b>admin huquqi</b> bering!\n\n"
                "🎴 Har 100 ta xabardan keyin waifu paydo bo'ladi.\n"
                "👉 Ushlash: <code>/waifu [ism]</code>\n\n"
                "📋 /help — barcha buyruqlar"
            ),
            parse_mode="HTML"
        )
    except:
        pass

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    chat = update.chat_member.chat
    new_status = update.chat_member.new_chat_member
    bot = await context.bot.get_me()
    if new_status.user.id == bot.id and new_status.status in ("member", "administrator"):
        await on_bot_added(context, chat)
