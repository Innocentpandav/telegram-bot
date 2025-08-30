import random
from datetime import datetime, timedelta, timezone
# In-memory store for summary password and expiry
SUMMARY_PASSWORDS = {}

import logging
import asyncio
import os
import time
import io
import re
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler
)
from database import (
    init_db, add_user, get_user, set_user_role, add_view,
    add_points, get_user_points, record_payment, get_user_viewed_post_ids, add_post
)
from file_storage import store_link_data
from payments import mock_buy5
from PIL import Image
import pytesseract

""" 
bot.py 
Main Telegram bot logic, handlers, and integration with database, file storage, and payments. 
"""

# Load config
with open('config.json') as f:
    CONFIG = json.load(f)

# Utility to check if a user is admin by user ID
def is_admin(user_id):
    # Support multiple admin user IDs from config
    ADMIN_USER_IDS = CONFIG.get('admin_user_ids', [])
    return str(user_id) in [str(uid) for uid in ADMIN_USER_IDS]

async def summery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Generate a random 6-digit password
    password = ''.join(random.choices('0123456789', k=6))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    SUMMARY_PASSWORDS[user_id] = {'password': password, 'expires_at': expires_at}
    # Send password to admin
    admin_id = CONFIG.get('admin_user_id')
    try:
        await context.bot.send_message(chat_id=admin_id, text=f"[SUMMARY ACCESS] User {user_id} ({update.effective_user.username}) requested summary. Password: {password}")
    except Exception:
        pass
    context.user_data['awaiting_summary_password'] = True
    cancel_keyboard = ReplyKeyboardMarkup([["Cancel"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "🔒 Please enter the summary password (sent to admin). Password expires in 10 minutes.",
        reply_markup=cancel_keyboard
    )
    return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single text message handler that handles the summary password flow and the main menu actions."""
    user = update.effective_user
    user_id = user.id
    request_id = set_latest_request(context, user_id)
    text = update.message.text.strip() if update.message and update.message.text else ""
    main_keyboard = ReplyKeyboardMarkup([
        ["🔗 Post My Link", "💰 Gain Points", "👀 View My Points"],
        ["🛒 Buy Post Points", "🌟 Explor YT"]
    ], resize_keyboard=True)
    # Handle 'Explor YT' button
    if text.strip().lower() in ["explor yt", "🌟 explor yt"]:
        yt_msg = (
            "🌟 Explore our YouTube channel for more tips and videos on how to write articles with no stress and get published easily!\n\n"
            "👉 https://youtube.com/@panda_groups?si=1Zzwjfa6de2B96g5"
        )
        await update.message.reply_text(yt_msg, reply_markup=main_keyboard)
        return

    # Always handle 'Cancel' to return to main menu, regardless of state
    if text.lower() == 'cancel':
        context.user_data.pop('awaiting_summary_password', None)
        await update.message.reply_text("❌ Cancelled. Returning to menu.", reply_markup=main_keyboard)
        return

    # If user is in summary-password mode, handle that first
    if context.user_data.get('awaiting_summary_password'):
        # Password attempt
        entry = SUMMARY_PASSWORDS.get(user_id)
        if not entry:
            context.user_data.pop('awaiting_summary_password', None)
            return
        if datetime.now(timezone.utc) > entry['expires_at']:
            del SUMMARY_PASSWORDS[user_id]
            context.user_data.pop('awaiting_summary_password', None)
            await update.message.reply_text("❌ Password expired. Please try again.")
            return
        if text == entry['password']:
            del SUMMARY_PASSWORDS[user_id]
            context.user_data.pop('awaiting_summary_password', None)
            # Gather and send summary
            from database import DB_PATH
            import aiosqlite
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()
            week_ago = (now - timedelta(days=7)).date().isoformat()
            month_ago = (now - timedelta(days=30)).date().isoformat()
            active_cutoff = (now - timedelta(minutes=10)).isoformat()
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                total_users = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
                users_today = await (await db.execute("SELECT COUNT(*) FROM users WHERE date(date_joined)=?", (today,))).fetchone()
                users_week = await (await db.execute("SELECT COUNT(*) FROM users WHERE date(date_joined)>=?", (week_ago,))).fetchone()
                users_month = await (await db.execute("SELECT COUNT(*) FROM users WHERE date(date_joined)>=?", (month_ago,))).fetchone()
                total_links = await (await db.execute("SELECT COUNT(*) FROM posts")).fetchone()
                active_users = await (await db.execute("SELECT COUNT(*) FROM users WHERE last_active>=?", (active_cutoff,))).fetchone()
            msg = (
                f"📊 <b>Summary</b>\n"
                f"Total users: <b>{total_users[0]}</b>\n"
                f"Users today: <b>{users_today[0]}</b>\n"
                f"Users this week: <b>{users_week[0]}</b>\n"
                f"Users this month: <b>{users_month[0]}</b>\n"
                f"Total links: <b>{total_links[0]}</b>\n"
                f"Active users (last 10 min): <b>{active_users[0]}</b>"
            )
            await update.message.reply_text(msg, parse_mode='HTML')
            return
        else:
            # Wrong password: clear state and return so other handlers can process next messages
            context.user_data.pop('awaiting_summary_password', None)
            return

    # Not in summary mode: proceed with main menu actions
    if not is_latest_request(context, user_id, request_id):
        return


    # If user sends a valid Opera News link directly, only allow if they have started the post flow
    import re, urllib.parse
    opera_link_pattern = re.compile(r"https://(www\.)?(opr\.news|operanewsapp\.com)/")
    if opera_link_pattern.match(text.strip()):
        if not context.user_data.get('post_link_active'):
            await try_send_reply(update.message.reply_text, "❌ Invalid request, please use the buttons.", reply_markup=main_keyboard)
            return
        # Check admin status at the start of the post flow
        is_admin_user = is_admin(user.id)
        user_data = await get_user(user.id)
        if not user_data:
            await add_user(user.id, user.username)
            user_data = await get_user(user.id)
        role = user_data['role']
        points = await get_user_points(user.id)
        url = text.strip()
        url = shorten_opera_link(url)
        # Explicitly apply admin or regular privileges
        if is_admin_user:
            can_post = True
        elif role in ('vip', 'free'):
            can_post = points >= 1
        else:
            can_post = False

        if not can_post:
            if is_admin_user:
                await try_send_reply(update.message.reply_text, "❌ Admin error: please check your privileges.", reply_markup=main_keyboard)
            elif role in ('vip', 'free'):
                await try_send_reply(update.message.reply_text, "❌ You need 1 point to post a link. View more news or buy points.", reply_markup=main_keyboard)
            else:
                await try_send_reply(update.message.reply_text, "❌ Unknown user role. Please contact admin.", reply_markup=main_keyboard)
            return

        # Passed all checks, now store the link
        from file_post_storage import add_post_to_json
        post_meta = {
            'user_id': user.id,
            'url': url,
            'date_posted': datetime.now(timezone.utc).isoformat(),
            'status': 'active'
        }
        json_file, post_idx = add_post_to_json(post_meta)
        # Store both the JSON file and the index in the DB
        file_ref = f"{json_file}:{post_idx}"
        await add_post(user.id, file_ref, status='active')
        # Only non-admins lose points
        if not is_admin_user:
            await add_points(user.id, -1)
        await try_send_reply(update.message.reply_text, f"✅ Your link has been posted!\nShort link: {url}", reply_markup=main_keyboard)
        # Reset post flow flag
        context.user_data['post_link_active'] = False
        return

    if text == "🛒 Buy Post Points":
        await show_buy_points_options(update, context)
        return

    if text == "👀 View My Points":
        points = await get_user_points(user_id)
        await try_send_reply(update.message.reply_text, f"🏅 You have accumulated {points:.1f} points from successful news viewing.", reply_markup=main_keyboard)
        return
    elif text == "💰 Gain Points":
        # Always generate a fresh list of unviewed links
        gain_points_msg = (
            "💡 In order to gain points, you must click and engage with other users' news on the Opera News app.\n\n"
            "If you wish to continue, click the 'Continue' button below to receive the links to the news."
        )
        gain_points_keyboard = ReplyKeyboardMarkup([
            ["🔙 Back to Menu", "➡️ Continue"],
            ["🛒 Buy Post Points"]
        ], resize_keyboard=True)
        from database import DB_PATH, get_user_viewed_post_ids
        import aiosqlite, random
        async def get_links():
            import json
            admin_id = CONFIG.get('admin_user_id')
            admin_links = []
            user_links = []
            user_id_local = update.effective_user.id
            viewed_post_ids = set(await get_user_viewed_post_ids(user_id_local))
            from file_post_loader import load_post_from_ref
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                # Admin links (exclude links posted by the current user, even if admin)
                async with db.execute("SELECT post_id, file_path, user_id FROM posts WHERE user_id = ? AND status = 'active' ORDER BY RANDOM()", (admin_id,)) as cursor:
                    async for row in cursor:
                        if row['post_id'] in viewed_post_ids:
                            continue
                        if str(row['user_id']) == str(user_id_local):
                            continue
                        link_data = load_post_from_ref(row['file_path'])
                        admin_links.append({'url': link_data['url'], 'post_id': row['post_id']})
                        if len(admin_links) >= 4:
                            break
                # User links (exclude posts by the current user)
                async with db.execute("SELECT post_id, file_path, user_id FROM posts WHERE user_id != ? AND status = 'active' ORDER BY RANDOM()", (user_id_local,)) as cursor:
                    async for row in cursor:
                        if row['post_id'] in viewed_post_ids:
                            continue
                        if str(row['user_id']) == str(user_id_local):
                            continue
                        link_data = load_post_from_ref(row['file_path'])
                        user_links.append({'url': link_data['url'], 'post_id': row['post_id']})
                        if len(user_links) >= 6:
                            break
            all_links = admin_links + user_links
            random.shuffle(all_links)
            return all_links
        news_links = await get_links()
        # Store both url and post_id for each link
        context.user_data['news_links'] = news_links
        context.user_data['news_link_idx'] = 0
        context.user_data['pending_link'] = None
        context.user_data['pending_timer'] = None
        context.user_data['pending_min_time'] = None
        await try_send_reply(update.message.reply_text, gain_points_msg, reply_markup=gain_points_keyboard)
        return
    elif text == "➡️ Continue":
        news_links = context.user_data.get('news_links', [])
        idx = context.user_data.get('news_link_idx', 0)
        if context.user_data.get('pending_link'):
            await try_send_reply(update.message.reply_text, "⚠️ Please confirm you have viewed the previous link by pressing '✅ I’m Done' before continuing.")
            return
        if idx == 0:
            intro_msg = (
                "🎉 Great! We will send you the links one at a time. Please view each news article.\n\n"
                "Note: Make sure to stay on the news for at least a minute to help each other."
            )
            await try_send_reply(update.message.reply_text, intro_msg)
        if idx < len(news_links):
            import random, time
            processing_msg = await try_send_reply(update.message.reply_text, "⏳ Processing...")
            try:
                if processing_msg:
                    await processing_msg.delete()
            except Exception:
                pass
            link_info = news_links[idx]
            min_time = random.randint(60, 80)
            now = int(time.time())
            context.user_data['pending_link'] = link_info['url']
            context.user_data['pending_post_id'] = link_info['post_id']
            context.user_data['pending_timer'] = now
            context.user_data['pending_min_time'] = min_time
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            link_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Go to Link (Earn Points)", url=link_info['url'])],
                [InlineKeyboardButton("✅ I’m Done", callback_data="confirm_done")]
            ])
            link_msg = f"📰 News Link {idx+1}: Please click the button below to open the news.\n\nAfter viewing, return and press '✅ I’m Done'.\n\nYou must stay at least 1 minute (randomized) to earn points!"
            await try_send_reply(update.message.reply_text, link_msg, reply_markup=link_keyboard)
        else:
            await try_send_reply(update.message.reply_text, "✅ You have completed all the news links! Thank you for helping each other.", reply_markup=main_keyboard)
            context.user_data.pop('news_links', None)
            context.user_data.pop('news_link_idx', None)
            context.user_data.pop('pending_link', None)
            context.user_data.pop('pending_post_id', None)
            context.user_data.pop('pending_timer', None)
            context.user_data.pop('pending_min_time', None)
        return
    elif text == "🔗 Post My Link":
        # Set flag to allow link posting
        context.user_data['post_link_active'] = True
        processing_msg = await try_send_reply(update.message.reply_text, "⏳ Processing...")
        instructions = (
            "📺 How to get your post link: Please watch this YouTube short!\n\n"
            "https://youtube.com/shorts/pbtNmCYezOc?si=gwRKa0uAxkLCu258\n\n"
            "-----------------------------\n"
            "📢 After watching, please send your link to be posted below.\n"
            "If you need help, just ask!"
        )
        back_keyboard = ReplyKeyboardMarkup([["🔙 Back to Menu"]], resize_keyboard=True)
        try:
            await update.message.reply_text(instructions, reply_markup=back_keyboard)
        except Exception:
            pass
        try:
            if processing_msg:
                await processing_msg.delete()
        except Exception:
            pass
        return
    elif text == "🔙 Back to Menu":
        welcome_back_msg = "👋 Welcome back to the menu! How may we proceed?"
        await try_send_reply(update.message.reply_text, welcome_back_msg, reply_markup=main_keyboard)
        return
    else:
        responses = {}
        await try_send_reply(update.message.reply_text, responses.get(text, "❌ Unknown option"))



async def try_send_reply(send_func, *args, **kwargs):
    for attempt in range(10):
        try:
            return await send_func(*args, **kwargs)
        except Exception:
            if attempt == 9:
                return None
            await asyncio.sleep(1)

# ---------- Utils for Request Tracking ----------
def set_latest_request(context, user_id):
    if not hasattr(context.application, "user_request_ids"):
        context.application.user_request_ids = {}
    request_id = str(time.time_ns())
    context.application.user_request_ids[user_id] = request_id
    return request_id

def is_latest_request(context, user_id, request_id):
    return context.application.user_request_ids.get(user_id) == request_id

def shorten_opera_link(url):
    """Convert long Opera News links to short format if possible."""
    import urllib.parse
    if 'operanewsapp.com' in url and 'news_entry_id=' in url:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        news_entry_id = qs.get('news_entry_id', [None])[0]
        if news_entry_id:
            return f"https://opr.news/{news_entry_id}"
    return url

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    request_id = set_latest_request(context, user_id)
    user_name = update.effective_user.first_name if update.effective_user else "there"
    # Set user role to admin if their Telegram ID matches admin_user_id in config
    admin_id = CONFIG.get('admin_user_id')
    # Do not add user to DB here; only after screenshot verification (except admin)
    welcome_message = (
        f"👋 Hello {user_name}!\n\n"
        "🎉 Welcome to Panda Clicker! Here, we help each other grow on Opera News by following a few simple rules:\n\n"
        "1️⃣ You must have the Opera News app installed.\n"
        "2️⃣ You must be logged in to the Opera News app.\n"
        "3️⃣ You need to click and view 10 other members' news articles to be eligible to post your own link.\n"
        "4️⃣ Please stay on each viewing link for at least 1 minute.⏱\n"
        "5️⃣ ALL RULES APPLY TO EVERYONE 🤝\n\n"
        "Let's support each other and make this community awesome! 🚀"
    )
    inline_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Follow & Continue", callback_data="accept_rules"),
            InlineKeyboardButton("❌ Reject & Stop", callback_data="reject_rules")
        ]
    ])
    if not is_latest_request(context, user_id, request_id):
        return
    await try_send_reply(
        update.message.reply_text,
        welcome_message + "\n\nDo you agree to follow these rules and continue?",
        reply_markup=inline_keyboard
    )

async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    request_id = set_latest_request(context, user_id)
    if not is_latest_request(context, user_id, request_id):
        return
    if query.data == "accept_rules":
        processing_msg = await query.message.reply_text("⏳ Processing...")
        instructions = (
            "📺 How to send your screenshot: Please watch this YouTube short!\n\n"
            "https://youtube.com/shorts/efmVhVG2fSQ?si=Mib9kEZacpw-z9-B\n\n"
            "To verify you are on board, please send us a screenshot of your Opera News app.\n\n"
            "📸 Make sure the screenshot clearly shows you are logged in.\n\n"
            "Once you send your screenshot, you will be able to continue!"
        )
        try:
            await query.message.reply_text(instructions)
        except Exception:
            pass
        try:
            await processing_msg.delete()
        except Exception:
            pass
    elif query.data == "reject_rules":
        await try_send_reply(
            query.message.reply_text,
            "👋 No worries! Thank you for checking out Panda Clicker. If you change your mind, you can always /start again. 🌟"
        )

async def button_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    request_id = set_latest_request(context, user_id)
    text = update.message.text if update.message else ""
    main_keyboard = ReplyKeyboardMarkup([
        ["🔗 Post My Link", "💰 Gain Points", "👀 View My Points"],
        ["🛒 Buy Post Points"]
    ], resize_keyboard=True)


    # Guard: If awaiting summary password, do not process this handler
    if context.user_data.get('awaiting_summary_password'):
        return

    # Always handle 'Cancel' to return to main menu, regardless of state
    if (update.message and update.message.text and update.message.text.strip().lower() == 'cancel'):
        main_keyboard = ReplyKeyboardMarkup([
            ["🔗 Post My Link", "💰 Gain Points", "👀 View My Points"],
            ["🛒 Buy Post Points"]
        ], resize_keyboard=True)
        await update.message.reply_text("❌ Cancelled. Returning to menu.", reply_markup=main_keyboard)
        return

    if not is_latest_request(context, user_id, request_id):
        return
    # If user sends a valid Opera News link directly, treat as post attempt
    import re, urllib.parse
    opera_link_pattern = re.compile(r"https://(www\.)?(opr\.news|operanewsapp\.com)/")
    if opera_link_pattern.match(text.strip()):
        user = update.effective_user
        user_data = await get_user(user.id)
        if not user_data:
            await add_user(user.id, user.username)
            user_data = await get_user(user.id)
        role = user_data['role']
        credits = user_data['credits']
        url = text.strip()
        # Trim long Opera News links to short format
        url = shorten_opera_link(url)
        # Admins can always post, never lose credits
        if role == 'admin':
            can_post = True
        elif role in ('vip', 'free'):
            can_post = credits > 0
        else:
            can_post = False

        if not can_post:
            if role in ('vip', 'free'):
                await try_send_reply(update.message.reply_text, "❌ You need 1 posting credit to post a link. View more news to earn credits.", reply_markup=main_keyboard)
            else:
                await try_send_reply(update.message.reply_text, "❌ Unknown user role. Please contact admin.", reply_markup=main_keyboard)
            return

        # Passed all checks, now store the link
        import uuid, json, os
        post_id = str(uuid.uuid4())
        post_meta = {
            'user_id': user.id,
            'url': url,
            'date_posted': datetime.now(timezone.utc).isoformat(),
            'status': 'active'
        }
        os.makedirs('storage/posts', exist_ok=True)
        meta_path = os.path.join('storage', 'posts', f'{post_id}.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(post_meta, f)
        # Store only reference in DB: post_id, user_id, status
        from database import add_post
        await add_post(user.id, meta_path, status='active')
        # Only non-admins lose credits
        if role != 'admin':
            await add_points(user.id, -1)
        await try_send_reply(update.message.reply_text, f"✅ Your link has been posted!\nShort link: {url}", reply_markup=main_keyboard)
        return


    if text == "🛒 Buy Post Points":
        await show_buy_points_options(update, context)
        return

    if text == "👀 View My Points":
        points = await get_user_points(user_id)
        await try_send_reply(update.message.reply_text, f"🏅 You have accumulated {points:.1f} points from successful news viewing.", reply_markup=main_keyboard)
        return
    elif text == "💰 Gain Points":
        gain_points_msg = (
            "💡 In order to gain points, you must click and engage with other users' news on the Opera News app.\n\n"
            "If you wish to continue, click the 'Continue' button below to receive the links to the news."
        )
        gain_points_keyboard = ReplyKeyboardMarkup([
            ["🔙 Back to Menu", "➡️ Continue"],
            ["🛒 Buy Post Points"]
        ], resize_keyboard=True)
        # Fetch 4 admin links and 6 random user links
        from database import DB_PATH
        import aiosqlite, random
        async def get_links():
            import json
            admin_id = CONFIG.get('admin_user_id')
            admin_links = []
            user_links = []
            user_id = update.effective_user.id
            viewed_post_ids = set(await get_user_viewed_post_ids(user_id))
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                # Get 4 random admin posts the user hasn't viewed
                async with db.execute("SELECT post_id, file_path FROM posts WHERE user_id = ? AND status = 'active' ORDER BY RANDOM()", (admin_id,)) as cursor:
                    async for row in cursor:
                        if row['post_id'] not in viewed_post_ids:
                            with open(row['file_path'], 'r') as f:
                                link_data = json.load(f)
                                admin_links.append(link_data['url'])
                        if len(admin_links) >= 4:
                            break
                # Get 6 random user posts (excluding admin) the user hasn't viewed
                async with db.execute("SELECT post_id, file_path FROM posts WHERE user_id != ? AND status = 'active' ORDER BY RANDOM()", (admin_id,)) as cursor:
                    async for row in cursor:
                        if row['post_id'] not in viewed_post_ids:
                            with open(row['file_path'], 'r') as f:
                                link_data = json.load(f)
                                user_links.append(link_data['url'])
                        if len(user_links) >= 6:
                            break
            # Combine and shuffle all links
            all_links = admin_links + user_links
            random.shuffle(all_links)
            return all_links
        news_links = await get_links()
        context.user_data['news_links'] = news_links
        context.user_data['news_link_idx'] = 0
        context.user_data['pending_link'] = None
        context.user_data['pending_timer'] = None
        context.user_data['pending_min_time'] = None
        await try_send_reply(update.message.reply_text, gain_points_msg, reply_markup=gain_points_keyboard)
        return
    elif text == "➡️ Continue":
        news_links = context.user_data.get('news_links', [])
        idx = context.user_data.get('news_link_idx', 0)
        if context.user_data.get('pending_link'):
            await try_send_reply(update.message.reply_text, "⚠️ Please confirm you have viewed the previous link by pressing '✅ I’m Done' before continuing.")
            return
        if idx == 0:
            intro_msg = (
                "🎉 Great! We will send you the links one at a time. Please view each news article.\n\n"
                "Note: Make sure to stay on the news for at least a minute to help each other."
            )
            await try_send_reply(update.message.reply_text, intro_msg)
        if idx < len(news_links):
            import random, time
            processing_msg = await try_send_reply(update.message.reply_text, "⏳ Processing...")
            try:
                if processing_msg:
                    await processing_msg.delete()
            except Exception:
                pass
            link = news_links[idx]
            min_time = random.randint(60, 80)
            now = int(time.time())
            context.user_data['pending_link'] = link
            context.user_data['pending_timer'] = now
            context.user_data['pending_min_time'] = min_time
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            link_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Go to Link (Earn Points)", url=link)],
                [InlineKeyboardButton("✅ I’m Done", callback_data="confirm_done")]
            ])
            link_msg = f"📰 News Link {idx+1}: Please click the button below to open the news.\n\nAfter viewing, return and press '✅ I’m Done'.\n\nYou must stay at least 1 minute (randomized) to earn points!"
            await try_send_reply(update.message.reply_text, link_msg, reply_markup=link_keyboard)
        else:
            await try_send_reply(update.message.reply_text, "✅ You have completed all the news links! Thank you for helping each other.", reply_markup=main_keyboard)
            context.user_data.pop('news_links', None)
            context.user_data.pop('news_link_idx', None)
            context.user_data.pop('pending_link', None)
            context.user_data.pop('pending_timer', None)
            context.user_data.pop('pending_min_time', None)
        return
    elif text == "🔗 Post My Link":
        processing_msg = await try_send_reply(update.message.reply_text, "⏳ Processing...")
        video_path = "testing.mp4"
        caption = (
            "🎥 Here is a short video showing how to get your link and post it.\n\n"
            "-----------------------------\n"
            "📢 After watching, please send your link to be posted below.\n"
            "If you need help, just ask!"
        )
        back_keyboard = ReplyKeyboardMarkup([["🔙 Back to Menu"]], resize_keyboard=True)
        try:
            await update.message.reply_video(
                video=open(video_path, "rb"),
                caption=caption,
                reply_markup=back_keyboard
            )
        except Exception:
            pass
        try:
            if processing_msg:
                await processing_msg.delete()
        except Exception:
            pass
        return
    elif text == "🔙 Back to Menu":
        welcome_back_msg = "👋 Welcome back to the menu! How may we proceed?"
        await try_send_reply(update.message.reply_text, welcome_back_msg, reply_markup=main_keyboard)
        return
    else:
        responses = {}
        await try_send_reply(update.message.reply_text, responses.get(text, "❌ Unknown option"))

from telegram import LabeledPrice
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters as ext_filters

# --- Payment Integration for Buy Points (Telegram Stars, no provider_token) ---

async def show_buy_points_options(update, context):
    keyboard = [
        [InlineKeyboardButton(f"Buy {i} Point{'s' if i > 1 else ''} ({i*100}⭐)", callback_data=f"buy_points_{i}")]
        for i in range(1, 11)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 Select how many points you want to buy. Each point costs 100 stars. Tap a button:",
        reply_markup=reply_markup
    )

async def buy_points_option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logging.info(f"buy_points_option_callback triggered: data={query.data}")
    await query.answer()
    data = query.data
    if data.startswith("buy_points_"):
        try:
            points = int(data.split("_")[-1])
        except Exception:
            points = 100
        from telegram import LabeledPrice
        price = points * 1  # 100 stars per point, in hundredths
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="Buy Points",
            description=f"Exchange {points*100} Stars for {points} Point{'s' if points > 1 else ''}",
            payload=f"buy_points_{points}",
            currency="XTR",
            prices=[LabeledPrice(f"{points} Point{'s' if points > 1 else ''}", price)]
        )

async def precheckout_callback(update, context):
    query = update.pre_checkout_query
    # Accept any valid buy_points_X payload
    if query.invoice_payload and query.invoice_payload.startswith("buy_points_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Invalid payload!")

async def successful_payment_callback(update, context):
    user_id = update.effective_user.id
    from database import add_points, record_payment
    payment = update.message.successful_payment
    # Determine how many points to add
    points = 1
    if payment.invoice_payload and payment.invoice_payload.startswith("buy_points_"):
        try:
            points = int(payment.invoice_payload.split("_")[-1])
        except Exception:
            points = 1
    await add_points(user_id, points)
    await record_payment(user_id, payment.total_amount, points)
    await update.message.reply_text(f"✅ Payment successful! You received {points} Point{'s' if points > 1 else ''}.")

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    request_id = set_latest_request(context, user_id)
    processing_msg = await try_send_reply(update.message.reply_text, "⏳ Processing...")
    if not update.message.photo:
        await try_send_reply(processing_msg.edit_text, "❌ Please send a valid screenshot as a photo.")
        return
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(photo_bytes))
    extracted_text = pytesseract.image_to_string(image)
    installation_id = None
    version = None
    signout = False
    for line in extracted_text.splitlines():
        if installation_id is None:
            match = re.search(r"installation id\s*[:\-]?\s*([^\n]+)", line, re.IGNORECASE)
            if match:
                installation_id = match.group(1).strip()
        if version is None:
            match = re.search(r"version\s*[:\-]?\s*([^\n]+)", line, re.IGNORECASE)
            if match:
                version = match.group(1).strip()
        if not signout and re.search(r"sign out", line, re.IGNORECASE):
            signout = True
    if not is_latest_request(context, user_id, request_id):
        try:
            await processing_msg.delete()
        except Exception:
            pass
        return
    # We still check for installation_id, version, and signout, but do NOT save them to DB
    if installation_id and version and signout:
        # Add user to DB only after passing screenshot verification (set admin role if in config)
        from database import add_user, set_user_role
        user = update.effective_user
        admin_ids = CONFIG.get('admin_user_ids', [])
        if str(user.id) in [str(uid) for uid in admin_ids]:
            await add_user(user.id, user.username, role='admin')
        else:
            await add_user(user.id, user.username)
        # Double-check and set admin role if needed (in case user already existed)
        if str(user.id) in [str(uid) for uid in admin_ids]:
            from database import set_user_role
            await set_user_role(user.id, 'admin')
        main_keyboard = [
            ["🔗 Post My Link", "💰 Gain Points", "👀 View My Points"],
            ["🛒 Buy Post Points", "🌟 Explor YT"]
        ]
        reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        welcome_msg = (
            "🎉 You have passed verification and are now onboard!\n\n"
            "Welcome to Panda Clicker! Use the menu below to post your link, gain points, or view your points.\n\n"
            "👇 Tap a button to get started:"
        )
        try:
            await processing_msg.delete()
        except Exception:
            pass
        await try_send_reply(update.message.reply_text, welcome_msg, reply_markup=reply_markup)
    else:
        error_msg = (
            "❌ Verification failed. Please follow the instructions and send the correct screenshot."
        )
        await try_send_reply(processing_msg.edit_text, error_msg)
async def confirm_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Answer the callback immediately to avoid Telegram 'query is too old' errors
    try:
        await query.answer()
    except Exception:
        pass
    user_id = update.effective_user.id
    data = context.user_data
    if not data.get('pending_link'):
        await try_send_reply(query.message.reply_text, "❌ No link is currently pending confirmation.")
        return
    import time, random
    now = int(time.time())
    min_time = data.get('pending_min_time')
    pending_timer = data.get('pending_timer')
    if not pending_timer or not min_time or (now - pending_timer) < min_time:
        min_time = random.randint(60, 80)
        data['pending_timer'] = now
        data['pending_min_time'] = min_time
        link = data['pending_link']
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        link_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Go to Link (Earn Points)", url=link)],
            [InlineKeyboardButton("✅ I’m Done", callback_data="confirm_done")]
        ])
        link_msg = f"📰 Please click the button below to open the news.\n\nAfter viewing, return and press '✅ I’m Done'.\n\nYou must stay at least some time (random) to earn points!"
        await try_send_reply(query.message.reply_text, f"⏳ Too fast! You must wait at least {min_time} seconds. Please try again and wait longer.")
        await try_send_reply(query.message.reply_text, link_msg, reply_markup=link_keyboard)
        return
    # Grant points, record view, move to next link
    from database import add_points, add_view, get_user_viewed_post_ids
    await add_points(user_id, 0.1)
    post_id = data.get('pending_post_id')
    if post_id:
        await add_view(user_id, post_id)
    await try_send_reply(query.message.reply_text, "✅ Great! You have earned 0.1 points for this link.")
    # Advance to next unviewed link automatically
    data['news_link_idx'] = data.get('news_link_idx', 0) + 1
    data['pending_link'] = None
    data['pending_post_id'] = None
    data['pending_timer'] = None
    data['pending_min_time'] = None
    news_links = data.get('news_links', [])
    idx = data.get('news_link_idx', 0)
    viewed_post_ids = set(await get_user_viewed_post_ids(user_id))
    next_link_info = None
    next_idx = idx
    while next_idx < len(news_links):
        link_info = news_links[next_idx]
        if link_info['post_id'] not in viewed_post_ids:
            next_link_info = link_info
            break
        next_idx += 1
    if next_link_info:
        # Prepare and send the next link
        import random, time
        min_time = random.randint(60, 80)
        now = int(time.time())
        data['pending_link'] = next_link_info['url']
        data['pending_post_id'] = next_link_info['post_id']
        data['pending_timer'] = now
        data['pending_min_time'] = min_time
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        link_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Go to Link (Earn Points)", url=next_link_info['url'])],
            [InlineKeyboardButton("✅ I’m Done", callback_data="confirm_done")]
        ])
        link_msg = f"📰 News Link: Please click the button below to open the news.\n\nAfter viewing, return and press '✅ I’m Done'.\n\nYou must stay at least 1 minute (randomized) to earn points!"
        await try_send_reply(query.message.reply_text, link_msg, reply_markup=link_keyboard)
        data['news_link_idx'] = next_idx
    else:
        main_keyboard = ReplyKeyboardMarkup([
            ["🔗 Post My Link", "💰 Gain Points", "👀 View My Points"],
            ["🛒 Buy Post Points"]
        ], resize_keyboard=True)
        await try_send_reply(update.callback_query.message.reply_text, "✅ You have completed all the news links! Thank you for helping each other.", reply_markup=main_keyboard)
        context.user_data.pop('news_links', None)
        context.user_data.pop('news_link_idx', None)
    # Removed duplicate screenshot handler code from confirm_done_callback.

async def save_post_and_media(user_id, media, metadata):
    """Save post metadata and media file, return file_path for DB."""
    import os, json, uuid
    from datetime import datetime
    storage_dir = os.path.join('storage', 'media')
    os.makedirs(storage_dir, exist_ok=True)
    post_id = str(uuid.uuid4())
    # Save media file
    ext = 'jpg'  # Default, you can detect from media type
    media_path = os.path.join(storage_dir, f"{post_id}.{ext}")
    with open(media_path, 'wb') as f:
        f.write(media)
    # Save metadata
    meta_dir = os.path.join('storage', 'posts')
    os.makedirs(meta_dir, exist_ok=True)
    meta_path = os.path.join(meta_dir, f"{post_id}.json")
    metadata['user_id'] = user_id
    metadata['media_path'] = media_path
    metadata['date_posted'] = datetime.now(timezone.utc).isoformat()
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f)
    return meta_path

# Update post handler to use file storage and check credits
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id)
    if not user_data:
        await add_user(user.id, user.username)
        user_data = await get_user(user.id)
    role = user_data['role']
    points = await get_user_points(user.id)
    # Only admin can post without points
    if role != 'admin' and points < 1:
        await update.message.reply_text("❌ You need 1 point to post a link. View more news or buy points.")
        return
    # Assume user sends a photo with caption as post
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a photo to post.")
        return
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    caption = update.message.caption or ''
    # Save post and media
    meta_path = await save_post_and_media(user.id, photo_bytes, {'caption': caption})
    # Insert post reference in DB
    from database import add_post
    await add_post(user.id, meta_path)
    if role != 'admin':
        await add_points(user.id, -1)
    await update.message.reply_text(f"✅ Your post has been saved!\nMetadata: {meta_path}")



async def buy5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    result = await mock_buy5(user.id, __import__('database'))
    if result:
        await update.message.reply_text("✅ Payment successful! 5 posting credits added.")
    else:
        await update.message.reply_text("❌ Payment failed. Please try again later.")

async def role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /role <free|vip|admin> <user_id>")
        return
    role, target_id = context.args[0], int(context.args[1])
    user_data = await get_user(user.id)
    if user_data and user_data['role'] == 'admin':
        await set_user_role(target_id, role)
        await update.message.reply_text(f"✅ Set user {target_id} role to {role}.")
    else:
        await update.message.reply_text("❌ Only admins can set roles.")


def main():
    import asyncio
    asyncio.run(init_db(CONFIG['db_path'], 'schema.sql'))
    # Ensure an event loop exists in the main thread for python-telegram-bot
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    token = os.environ.get("BOT_TOKEN_API")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN_API not found.")
    app = Application.builder().token(token).build()
    # --- Start backup manager ---
    try:
        from backup_manager import BackupManager
        backup_mgr = BackupManager(bot_app=app)
        backup_mgr.start()
    except Exception as e:
        logging.error(f"Backup manager failed to start: {e}")
    # Global error handler
    async def error_handler(update, context):
        logging.error("Exception while handling an update:", exc_info=context.error)
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summery", summery_command))
    # Single text handler for summary flow and main menu
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(rules_callback, pattern="^(accept_rules|reject_rules)$"))
    app.add_handler(CallbackQueryHandler(confirm_done_callback, pattern="^confirm_done$"))
    app.add_handler(CallbackQueryHandler(reset_timer_callback, pattern="^reset_timer$"))
    app.add_handler(CallbackQueryHandler(buy_points_option_callback, pattern=r"^buy_points_\d+$"))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("buy5", buy5))
    app.add_handler(CommandHandler("role", role))
    # Register payment handlers
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(ext_filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    logging.info("🤖 Bot is running...")
    print("🤖 Bot is running...")
    print("✅ Handlers registered:", app.handlers)
    import asyncio
    async def run():
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.updater.idle()
    asyncio.run(run())
# --- Add reset_timer_callback ---
async def reset_timer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = context.user_data
    import random, time
    now = int(time.time())
    min_time = random.randint(60, 80)
    data['pending_timer'] = now
    data['pending_min_time'] = min_time
    await update.callback_query.answer("Timer started! Please view the link and wait before confirming.")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
