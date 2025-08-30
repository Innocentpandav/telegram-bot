# August 2025 (continued)

## August 25, 2025

### Added/Changed
- Admins can now post links without needing points (infinite posting for admins).
- Users are only added to the database after passing screenshot verification (except admin).
- Users must click a request/menu button before replying (e.g., sending a link); replies are only accepted if a request is active.
- When a user posts a link, they will not see their own links when going to gain points (view links).
- Gain points flow improved: users never see their own posts, and only see links they have not viewed before.

### Added/Changed (Recent)
- Only add users to the database after passing screenshot verification.
- Do not save installation ID, version, or sign out to the DB; only check them.
- Users can only see links they have not viewed before when earning points.
- When a user requests links to earn points, show 10 links: 4 from admin, 6 from random users (never previously viewed by the user).
- Added `is_admin(user_id)` utility for admin checks using config.
- Database auto-migrates to add `points` column if missing.
- Users earn 0.1 points per successful news view, stored in the DB.
- 'View My Points' button shows total accumulated points from DB.
- Fixed callback query reply errors in timer confirmation.
- Modularized bot logic and improved error handling.
- File storage for heavy post/media data, only metadata in SQLite.
- Added scripts for DB management (clear, list users).
- Reorganized all import statements to the top of the file to fix a NameError and improve code structure.

# Changelog

## August 28, 2025

### Fixed
- Buy points inline button was not working due to incorrect regex pattern in callback handler registration. Now the handler triggers correctly when a buy points button is clicked.

### Added
- Added instructions to install missing Google Drive dependency (`google-api-python-client`) for backup feature.

## August 2025

### Added
- Interactive, step-by-step gain points flow: When the user clicks 'Continue' after 'Gain Points', the bot sends news links one at a time, tracking progress per user. After each link, the user must click 'Continue' to get the next, and a completion message is shown at the end. The flow is robust and event-driven.
- When the user clicks "🔙 Back to Menu", they now see a friendly message ("Welcome back to the menu! How may we proceed?") and the main menu keyboard.
- When the user clicks "💰 Gain Points", they receive clear instructions and a keyboard with "Back to Menu" and "Continue" buttons, guiding them on how to proceed to earn points.
- Initial Telegram bot with:
	- Custom reply keyboard and button responses for user interaction.
	- Personalized greeting using the user's Telegram name.
	- Friendly, improved welcome message with emojis and clear community rules.
	- Inline keyboard (inline buttons) for accepting or rejecting the rules after the welcome message.
	- Handler for inline button responses to control onboarding flow.
	- Flow for handling acceptance (show menu) or rejection (farewell message).
				- After accepting rules, send a video message (not just a link) showing how to send a screenshot, with the screenshot instructions included as the video caption in a single message.
				- Added screenshot verification: bot scans received screenshots for 'installation id' and 'signout' using OCR and replies with verification status.
	- Modular onboarding: user must accept rules and send a screenshot before accessing main features.
	- All user-facing messages improved for clarity, friendliness, and engagement.
- '🛒 Buy Post Points' button to all main keyboards and gain points menu.
	- When clicked, users see a message explaining the benefits and inline buttons to buy 1-10 post points for stars.

### Changed
- Bot name changed from "Opera Clicker" to "Panda Clicker" in all user-facing messages and logic.
- Welcome message and rules improved for clarity, friendliness, and to include step-by-step onboarding.
- Removed the default welcome message after /start; now, onboarding is handled via inline buttons and responses.
- Environment variable for bot token changed to `BOT_TOKEN_API` for clarity.
- Hardcoded token removed from code; now loaded securely from `.env` file.
	- Increased Telegram bot network timeouts for better reliability on slow connections.
	- Suppressed all error messages to users if sending video fails; users only see real content, not error notifications.
- Onboarding flow now processes only one request per user at a time to prevent duplicate or concurrent actions.
- All error messages to users are now fully suppressed during onboarding and video sending; users will not see any error notifications, only successful content.
- Implemented per-user request ID state tracking for all onboarding button actions: only the latest request for each user will send a reply, older requests are discarded if superseded by a newer action.
- Screenshot handler now uses OCR to extract and report:
    - The value of "Installation ID" (if present)
    - The value of "Version" (if present)
    - The presence of "Sign out"
- Bot replies with a detailed summary of which items were found and their values, or indicates if any are missing.
- Screenshot handler now:
    - Extracts the full line after "Installation ID" and after "Version" from OCR text.
    - Checks for the presence of "Sign out" in the text.
    - Only replies if all three are found; otherwise, sends an error message.
    - Ensures reply is only sent if this is still the latest request for the user (request ID check).
- Request ID logic now applied to all user-triggered handlers (start, rules_callback, button_response, screenshot_handler):
    - Each user action assigns a unique request ID.
    - Only the latest request for a user will send a reply; older requests are ignored if superseded.
    - Prevents race conditions and duplicate replies for all user actions.
- Moved `await query.answer()` to the very top of `rules_callback` for immediate callback acknowledgement.
- Request ID is now only generated when a new user action begins (e.g., button press), not inside every handler, for more efficient and accurate request tracking.
- When the "accept rules" button is clicked, the bot now sends only one response: the video message with caption. No duplicate or fallback text message is sent, even if the video fails to send. This ensures a fast and clean user experience.
- For heavy/slow actions (sending video on accept rules, screenshot OCR), the bot now instantly replies with a "⏳ Processing..." message. This message is updated or deleted with the final result, ensuring users always get immediate feedback.
- After successful OCR verification, the bot now sends a welcome message and displays a main menu with interactive buttons, allowing users to explore the full extent of the bot's features.
- After successful OCR verification, the main menu is now presented as a ReplyKeyboardMarkup (regular keyboard with button labels), not as an inline keyboard. Users see only clickable keyboard buttons after passing verification.
- Removed all inline keyboard usage from the main menu after verification for a more native chat experience.
- After passing OCR verification, users now see only three buttons in their keyboard: "Post Link", "Gain Points", and "View Points". All other menu options have been removed for a focused user experience.
- When OCR verification fails, users now receive a simple, user-friendly message: "❌ Verification failed. Please follow the instructions and send the correct screenshot." The bot no longer lists which items are missing.
- The post-OCR keyboard buttons are now more friendly and engaging, with emoji-enhanced labels: "🔗 Post My Link", "💰 Gain Points", and "👀 View My Points".
- When users click "🔗 Post My Link" after passing OCR, the keyboard is removed, they are prompted to send their link, and a video guide (using the testing video) is sent showing how to get and post the link.

### Fixed
- Ensured onboarding flow is clear and users cannot access main features without accepting rules and sending a screenshot.
- Improved error handling for missing bot token in `.env` file.
- Improved concurrency control and robustness in the onboarding flow.
- Prevented race conditions and duplicate replies when users trigger multiple onboarding actions quickly.
- Fixed InlineKeyboardMarkup error by ensuring each button is in its own row for Telegram compatibility.

## August 19, 2025 (continued)

### Changed
- After clicking "🔗 Post My Link" and receiving the video, users now see only a "🔙 Back to Menu" button as their keyboard. If the video fails to send, nothing is sent and the keyboard remains unchanged.

### Fixed
- Fixed a bug where the bot tried to send an empty message (reply_text with an empty string), causing a "Message text is empty" Telegram error. Now, the reply keyboard is only sent with a valid message.
- Ensured that after successful OCR, the welcome message and reply keyboard are always sent together in a single message, never separately.
- Fixed all indentation and misplaced else errors in the screenshot handler, so the bot runs without syntax errors.
- Ensured that the reply keyboard is never sent with edit_text (only with reply_text), preventing "Inline keyboard expected" errors.

### Improved
- The gain points flow is now robust and event-driven, using context.user_data to track user progress through news links. No unsupported methods are used; the experience is smooth and reliable for each user.
- For all actions that process and send videos (or other potentially slow actions), the bot now always sends a "⏳ Processing..." message first, which is deleted after the action completes.
- When users click "🔗 Post My Link", they now receive a single, user-friendly video message with clear instructions and space, telling them to send their link after watching. The keyboard is removed in the same message for a smoother experience.
- After OCR verification, the onboarding welcome, instructions, and menu prompt are now combined into a single, user-friendly message with the reply keyboard, instead of being sent as separate messages.

### Security & Robustness
- All error messages to users are fully suppressed; only valid, user-friendly messages are sent.
- Added a global error handler to catch and log all exceptions, including Telegram and HTTPX timeouts, so the bot never crashes or leaks errors to users.
- Wrapped deletion of the "Processing..." message in a try-except block to suppress timeouts and prevent crashes or error leakage to users during network issues.
- Implemented a retry mechanism for all user-facing replies and edits: if an error occurs, the bot will automatically retry up to 10 times before giving up. This ensures users are much less likely to be left without a response due to temporary errors.

### Fixed
- Fixed a bug where the bot tried to send a ReplyKeyboardMarkup as an inline keyboard, causing a 'Inline keyboard expected' error. The reply keyboard is now sent in a new message after the onboarding text, ensuring compatibility and no errors.
- Fixed indentation and misplaced else errors in `screenshot_handler`, resolving all syntax issues. The bot now runs without syntax errors.
- Fixed all indentation and control flow errors in the `screenshot_handler` function, ensuring robust and valid Python code.

## August 2025 (Event Loop & Cross-Platform Fixes)

### Fixed
- Fixed event loop errors on Windows and Python 3.10+/3.11+ with python-telegram-bot v20+ by ensuring a new event loop is created and set in the main thread before starting the bot.
- Switched to a synchronous `main()` function for bot startup, running async DB initialization with `asyncio.run()` and then starting the bot with `app.run_polling()`.

## August 2025 (Major Refactor & Modularization)

### Major Changes
- Refactored the entire bot into a modular structure for maintainability and extensibility.
- Split the codebase into multiple files: `bot.py` (main logic), `database.py` (async DB logic), `file_storage.py` (rotating JSONL storage), `payments.py` (mock payment logic), `config.json` (settings), and `schema.sql` (DB schema).
- Integrated SQLite for persistent user, link, and credit management using async access (`aiosqlite`).
- Added robust file storage for heavy data using rotating JSONL files.
- Implemented a mock payment system for buying posting credits.
- Added role-based logic (admin, VIP, free) for posting and viewing links.
- Ensured all original onboarding, menu, OCR, retry, and error handling flows/messages from the legacy `my_telegram_bot.py` are preserved in the new modular structure.
- Fixed all import, event loop, and Windows compatibility issues.
- All handlers (commands, text, photo, callback) are now registered in a single place, with robust error handling and retry logic.

### Details
- All onboarding, menu, OCR, and retry logic from the original bot was carefully merged into the new modular `bot.py`, preserving every user-facing message, keyboard, and flow.
- The new structure allows for easy extension (e.g., adding new payment providers, storage backends, or admin features) without breaking existing flows.
- The event loop and import logic was rewritten to ensure the bot runs on all platforms (Windows, Linux, macOS) and Python versions (3.8+), with no event loop or import errors.
- The codebase is now robust, maintainable, and ready for future features.

## August 2025 (Bug Fixes & Handler Order)

### Fixed
- Fixed all syntax and indentation errors in `button_response` by flattening the logic and ensuring all variables are in scope.
- Moved `confirm_done_callback` above `main()` to resolve handler registration errors.
- Added a `pass` statement to `screenshot_handler` to fix the 'expected indented block' error.
- Cleaned up unreachable and duplicated code in handlers.
- Ensured all callback and message handlers are defined before being registered in the bot.
# August 2025 (Latest Updates)
### Improved
- The Cancel button now always returns the user to the main menu, regardless of where they are in the flow (including after summary/password or any other state). This ensures a consistent and user-friendly experience.


### Added
- Persistent post_id-based tracking of viewed links: When a user confirms viewing a link, its post_id is stored in the database. Users will never see the same post again, even if they clear chat, delete their account, or return later.
- Rolling JSON file storage for posts: All posted links are stored in batches of 10,000 per JSON file, with the database referencing the file and index for each post. This improves scalability and performance.
- Unified and robust message handler: All text and button actions are now handled by a single handler, preventing overlap and ensuring consistent menu and flow logic.

### Fixed
- Fixed all logic to ensure users never see the same post_id again, regardless of session, chat history, or account deletion.
- Fixed all handler and callback query issues, including UnboundLocalError, NameError, and indentation errors.
- Fixed buy points inline button handler: Regex pattern corrected so buy points buttons now work as expected.
- Callback queries are now answered immediately to avoid 'query is too old' errors.

### Changed
- All link filtering and gain points logic now uses post_id for robust, persistent, and unique link delivery per user.
- Improved error handling, logging, and retry logic for all user actions.
- Removed all legacy/duplicate handlers and consolidated logic for clarity and maintainability.
