import os
import shutil
import asyncio
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "waifu_bot.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")

def create_backup(backup_type: str = "daily"):
  os.makedirs(BACKUP_DIR, exist_ok=True)
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  backup_file = os.path.join(BACKUP_DIR, f"backup_{backup_type}_{timestamp}.db")

  if os.path.exists(DB_PATH):
      shutil.copy2(DB_PATH, backup_file)
      print(f"Backup created: {backup_file}")

      backups = sorted([
          f for f in os.listdir(BACKUP_DIR)
          if f.startswith(f"backup_{backup_type}")
      ])
      if len(backups) > 7:
          for old in backups[:-7]:
              os.remove(os.path.join(BACKUP_DIR, old))
      return backup_file
  return None

def schedule_backups(scheduler):
  from apscheduler.triggers.cron import CronTrigger
  scheduler.add_job(
      lambda: create_backup("daily"),
      CronTrigger(hour=3, minute=0),
      id="daily_backup",
      replace_existing=True
  )
  scheduler.add_job(
      lambda: create_backup("weekly"),
      CronTrigger(day_of_week="mon", hour=4, minute=0),
      id="weekly_backup",
      replace_existing=True
  )
  print("Backup scheduler configured")
