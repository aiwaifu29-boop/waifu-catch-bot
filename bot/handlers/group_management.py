from telegram import Update, ChatMemberUpdated
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

    try:
        count = await context.bot.get_chat_member_count(group_id)
    except:
        count = 0

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

    group = await grp_db.get_or_create_group(group_id, group_name)
    await log_db.add_log("group_join", group_id=group_id, details=f"name={group_name} members={count}")

    if not group.get("is_approved"):
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=(
                    "⏳ <b>Guruh tasdiqlanishi kutilmoqda.</b>\n\n"
                    "Bot faqat God Admin tasdiqlagan guruhlarda to'liq ishlaydi.\n"
                    "Tasdiqlash uchun God Admin bilan bog'laning."
                ),
                parse_mode="HTML"
            )
        except:
            pass
    else:
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=(
                    "👋 <b>Waifu Catch Bot guruhga qo'shildi!</b>\n\n"
                    "🎴 Har 100 ta xabardan keyin waifu spawn bo'ladi.\n"
                    "❓ Ism topgan birinchi kishi waifuni qo'lga kiritadi!\n\n"
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
    if new_status.user.id == bot.id and new_status.status == "member":
        await on_bot_added(context, chat)
