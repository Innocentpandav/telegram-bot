"""
database.py
Async SQLite3 database logic for Telegram bot.
Handles migrations, queries, and user/link/payment logic.
"""
import aiosqlite
import asyncio
import logging
from datetime import datetime

DB_PATH = 'bot.db'
SCHEMA_PATH = 'schema.sql'

async def init_db(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    """Initialize DB and run migrations."""
    async with aiosqlite.connect(db_path) as db:
        # Run schema migrations
        with open(schema_path, 'r') as f:
            await db.executescript(f.read())
        # Ensure 'points', and 'last_active' columns exist in users table
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] async for row in cursor]
        if 'points' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN points REAL DEFAULT 0")
        if 'last_active' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN last_active TEXT")
        await db.commit()

async def add_user(user_id, username, installation_id=None, version=None, signout=None, role='free'):
    """Add or update a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, date_joined, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                role=excluded.role
            """,
            (user_id, username, datetime.utcnow().isoformat(), role)
        )
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def set_user_role(user_id, role):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        await db.commit()


# All link data is now handled via posts table and file storage. See add_post and related logic below.

async def add_view(user_id, post_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO views (user_id, post_id, date_viewed) VALUES (?, ?, ?)",
            (user_id, post_id, datetime.utcnow().isoformat())
        )
        await db.commit()


# Add 0.1 points for a successful view
async def add_points(user_id, amount=0.1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_user_points(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT points FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def record_payment(user_id, amount, points_bought):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments (user_id, amount, posts_bought, date_paid) VALUES (?, ?, ?, ?)",
            (user_id, amount, points_bought, datetime.utcnow().isoformat())
        )
        await db.commit()

async def get_user_viewed_post_ids(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT post_id FROM views WHERE user_id = ?", (user_id,)) as cursor:
            return [row[0] async for row in cursor]

async def add_post(user_id, file_ref, status="active"):
    """
    Store a post reference in the DB. file_ref is in the format 'json_file:index'.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO posts (user_id, file_path, status, date_posted) VALUES (?, ?, ?, ?)",
            (user_id, file_ref, status, datetime.utcnow().isoformat())
        )
        await db.commit()

# Add more queries as needed for your bot logic
