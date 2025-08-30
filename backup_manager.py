import os
import glob
import threading
import time
import signal
from drive_utils import upload_file, download_file, list_files_in_drive
from database import get_user

BACKUP_INTERVAL = 60  # seconds
LOCAL_DB = 'bot.db'
LOCAL_JSONS = glob.glob('*.json')

# Set these from env or config
FOLDER_ID = os.environ.get('GDRIVE_FOLDER_ID', 'YOUR_FOLDER_ID_HERE')

class BackupManager:
    def __init__(self, bot_app=None):
        self.shutdown_flag = threading.Event()
        self.bot_app = bot_app
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.sync_from_drive()
        self.thread.start()
        self.broadcast_online()

    def run(self):
        while not self.shutdown_flag.is_set():
            self.sync_to_drive()
            time.sleep(BACKUP_INTERVAL)

    def handle_sigterm(self, signum, frame):
        self.sync_to_drive()
        self.broadcast_maintenance()
        self.shutdown_flag.set()

    def sync_from_drive(self):
        # Download DB and all JSONs from Drive
        for fname in [LOCAL_DB] + glob.glob('*.json'):
            try:
                download_file(fname, fname)
            except Exception:
                pass

    def sync_to_drive(self):
        # Upload DB and all JSONs to Drive
        for fname in [LOCAL_DB] + glob.glob('*.json'):
            if os.path.exists(fname):
                try:
                    upload_file(fname, fname)
                except Exception:
                    pass

    def broadcast_maintenance(self):
        # Send maintenance message to all users in DB
        if self.bot_app:
            import asyncio
            async def send_all():
                from database import DB_PATH
                import aiosqlite
                async with aiosqlite.connect(DB_PATH) as db:
                    cursor = await db.execute('SELECT user_id FROM users')
                    rows = await cursor.fetchall()
                    for row in rows:
                        try:
                            await self.bot_app.bot.send_message(row[0], "⚠️ Bot maintenance in progress, please hold on...")
                        except Exception:
                            pass
            asyncio.run(send_all())

    def broadcast_online(self):
        # Send online message to all users in DB
        if self.bot_app:
            import asyncio
            async def send_all():
                from database import DB_PATH
                import aiosqlite
                async with aiosqlite.connect(DB_PATH) as db:
                    cursor = await db.execute('SELECT user_id FROM users')
                    rows = await cursor.fetchall()
                    for row in rows:
                        try:
                            await self.bot_app.bot.send_message(row[0], "✅ Bot is back online, you may continue.")
                        except Exception:
                            pass
            asyncio.run(send_all())
