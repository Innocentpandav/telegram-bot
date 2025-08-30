import subprocess
import time

# Start your bot (your bot logic is in bot.py)
process = subprocess.Popen(["python", "bot.py"])

try:
    # Keep the space alive
    while True:
        time.sleep(10)
        # Restart bot if it crashes
        if process.poll() is not None:
            print("Bot crashed! Restarting...")
            process = subprocess.Popen(["python", "bot.py"])
except KeyboardInterrupt:
    print("Shutting down bot...")
    process.terminate()
