from telegram import Update
from telegram.ext import ContextTypes
from database import users as user_db
from database import logs as log_db

BAD_WORDS = []

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not update.message.reply_to_message:
      await update.message.reply_text("❌ Ogohlantirish uchun xabarga reply bering.")
      return

  target = update.message.reply_to_message.from_user
  count = await user_db.add_warn(target.id)
  await log_db.add_log("warn", user_id=update.effective_user.id, details=f"warned={target.id} count={count}")

  if count >= 3:
      await user_db.ban_user(target.id, "3 ta ogohlantirish")
      await update.message.reply_text(
          f"🚫 <b>{target.full_name}</b> 3 ta ogohlantirish tufayli bloklandi.",
          parse_mode="HTML"
      )
  else:
      await update.message.reply_text(
          f"⚠️ <b>{target.full_name}</b> ogohlantirdi! ({count}/3)",
          parse_mode="HTML"
      )

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not update.message.reply_to_message:
      await update.message.reply_text("❌ Mute uchun xabarga reply bering.")
      return

  from telegram import ChatPermissions
  target = update.message.reply_to_message.from_user
  try:
      await context.bot.restrict_chat_member(
          update.effective_chat.id,
          target.id,
          ChatPermissions(can_send_messages=False)
      )
      await log_db.add_log("mute", user_id=update.effective_user.id, details=f"muted={target.id}")
      await update.message.reply_text(f"🔇 <b>{target.full_name}</b> mute qilindi.", parse_mode="HTML")
  except Exception as e:
      await update.message.reply_text(f"❌ Mute qilib bo'lmadi: {e}")

async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not update.message.reply_to_message:
      await update.message.reply_text("❌ Unmute uchun xabarga reply bering.")
      return

  from telegram import ChatPermissions
  target = update.message.reply_to_message.from_user
  try:
      await context.bot.restrict_chat_member(
          update.effective_chat.id,
          target.id,
          ChatPermissions(
              can_send_messages=True,
              can_send_media_messages=True,
              can_send_other_messages=True,
          )
      )
      await update.message.reply_text(f"🔊 <b>{target.full_name}</b> unmute qilindi.", parse_mode="HTML")
  except Exception as e:
      await update.message.reply_text(f"❌ Unmute qilib bo'lmadi: {e}")

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not update.message.reply_to_message:
      await update.message.reply_text("❌ Kick uchun xabarga reply bering.")
      return

  target = update.message.reply_to_message.from_user
  try:
      await context.bot.ban_chat_member(update.effective_chat.id, target.id)
      await context.bot.unban_chat_member(update.effective_chat.id, target.id)
      await log_db.add_log("kick", user_id=update.effective_user.id, details=f"kicked={target.id}")
      await update.message.reply_text(f"👢 <b>{target.full_name}</b> kick qilindi.", parse_mode="HTML")
  except Exception as e:
      await update.message.reply_text(f"❌ Kick qilib bo'lmadi: {e}")

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not update.message.reply_to_message:
      await update.message.reply_text("❌ Ban uchun xabarga reply bering.")
      return

  target = update.message.reply_to_message.from_user
  reason = " ".join(context.args) if context.args else "Sabab ko'rsatilmagan"
  try:
      await context.bot.ban_chat_member(update.effective_chat.id, target.id)
      await user_db.ban_user(target.id, reason)
      await log_db.add_log("ban", user_id=update.effective_user.id, details=f"banned={target.id}")
      await update.message.reply_text(f"🚫 <b>{target.full_name}</b> ban qilindi.", parse_mode="HTML")
  except Exception as e:
      await update.message.reply_text(f"❌ Ban qilib bo'lmadi: {e}")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
  from database.logs import is_admin
  if not await is_admin(update.effective_user.id):
      await update.message.reply_text("❌ Ruxsatingiz yo'q.")
      return

  if not context.args:
      await update.message.reply_text("❌ Format: /unban [user_id]")
      return

  try:
      uid = int(context.args[0])
      await context.bot.unban_chat_member(update.effective_chat.id, uid)
      await user_db.unban_user(uid)
      await update.message.reply_text(f"✅ {uid} unban qilindi.")
  except Exception as e:
      await update.message.reply_text(f"❌ Unban qilib bo'lmadi: {e}")
