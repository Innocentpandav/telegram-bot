---
title: Telegram Bot
emoji: 🤖
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: 5.44.1
app_file: app.py
pinned: false
---

# Telegram Bot
This is my custom Telegram bot running inside a Hugging Face Space 🚀
# Opera News Link Sharing Telegram Bot

A robust Telegram bot for sharing Opera News links, earning points, and automating community link exchange. Features persistent user/link/points/admin tracking, Google Drive backup, multi-admin support, and YouTube-based onboarding.

## Features
- Share Opera News links and earn points for viewing others' links
- Never see the same link twice; users can't view their own links
- Admins can post unlimited links
- Multi-admin support (set in `config.json`)
- Robust onboarding with YouTube channel guide
- Google Drive backup/restore for database and files
- Persistent storage: SQLite for metadata, file storage for heavy data
- Modular, production-ready codebase

## Setup Instructions

### 1. Clone the Repository
```
git clone https://github.com/Innocentpandav/telegram-bot
cd telegram-bot
```

### 2. Install Python Dependencies
Make sure you have Python 3.12+ installed.
```
pip install -r requirements.txt
```

#### If using Google Drive backup, also install:
```
pip install google-api-python-client
```

### 3. Configure the Bot
- Copy `config.example.json` to `config.json` and fill in your values:
  - `bot_token`: Your Telegram bot token
  - `admin_user_ids`: List of Telegram user IDs for admins
  - `youtube_channel_url`: Your onboarding YouTube channel link
  - (Other config options as needed)

### 4. Run the Bot
```
python bot.py
```

## Usage
- Start the bot on Telegram and follow the menu.
- New users must verify with a screenshot before posting links.
- Use the main menu to post links, view points, buy points, or explore the YouTube channel.
- Admins can post links without using points.
- Points can be bought using Telegram Stars (if enabled).

## Backup & Restore
- The bot can back up its database and files to Google Drive (if configured).
- Make sure to set up Google Drive API credentials as described in `drive_utils.py`.

## Project Structure
- `bot.py` — Main bot logic and handlers
- `database.py` — SQLite DB logic
- `file_storage.py` — File storage for post data
- `config.json` — Bot configuration
- `backup_manager.py`, `drive_utils.py` — Google Drive backup
- `CHANGELOG.md` — Project changelog

## Contributing
- Please read the code and follow the modular structure.
- PRs and issues are welcome!

## License
MIT License