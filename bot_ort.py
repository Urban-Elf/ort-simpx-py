import asyncio
import os
from types import MethodType
import sys
from simpx import BotProfile, SimpleXBot
from ort import ort

ALLOW_SYSTEM_CONTROL = False

# 1. Create a bot profile (can be saved/loaded)
# If a profile with this name exists, it will be loaded.
# Otherwise, a new one is created on the server.
profile = BotProfile(
    display_name="Ort",
    full_name="Ort",
    description="Cutting-edge AI assistant.",
    # Optional: Welcome message for new contacts
    welcome_message="...",
    # Optional: Set command prefix (default is "!")
    command_prefix="!ort_",
    # TODO: image=
)

# 2. Create the bot instance
# You can pass the profile directly or let the bot handle loading/creation
bot = SimpleXBot(profile)

@bot.command(name="info", help="Shows bot information")
async def info_command(chat_info, profile):
    """Command that shows information about the bot's profile."""
    await bot.send_message(
        chat_info,
        f"*Bot Information*\n"
        f"Name: {profile.display_name}\n"
        f"Description: {profile.description}\n"
        f"Address: {profile.address}"
    )

@bot.command(name="shutdown", help="Shutdown bot")
async def shutdown_command(chat_info, args):
    await bot.send_message(
        chat_info,
        "Thank you for using ORT (v0.0.0-eol).\nShutting down now.")
    await bot.close()
    sys.exit(0)

# Really handy if you're running headless, but be careful not to run on test machines
@bot.command(name="shutdown_os", help="Shutdown bot and OS")
async def shutdown_command(chat_info, args):
    await bot.send_message(
        chat_info,
        "Thank you for using ORT (v0.0.0-eol).\nShutting down OS now.")
    await bot.close()
    if ALLOW_SYSTEM_CONTROL:
        if sys.platform == "win32":
            os.system("shutdown /s /t 1")
        elif sys.platform == "linux":
            os.system("shutdown now")
        elif sys.platform == "darwin":
            os.system("sudo shutdown -h now")
        else:
            print("Unsupported OS for shutdown command.")
    sys.exit(0)

# 4. Define event handlers (optional)
@bot.event("contactConnected")
async def handle_connection(response):
  """Handles new contact connections (alternative to welcome_message)."""
  contact = response.get("contact", {})
  display_name = contact.get("profile", {}).get("displayName", "Unknown")
  print(f"{display_name} connected!")


async def handle_message(self, msg_text, chat_info):
    if (msg_text is None) or (chat_info is None):
        return
    if (len(msg_text.strip()) == 0):
        return
    if ort.should_respond(msg_text):
        reply = ort.get_response(msg_text)
        await bot.send_message(chat_info, reply)

bot.message_received = MethodType(handle_message, bot)

# 5. Start the bot
if __name__ == "__main__":
    print("Starting bot...")
    # Ensure your SimpleX Chat Console (simplex-chat) backend is running
    # The bot will connect via WebSocket (default: ws://127.0.0.1:5225)
    # You can specify a different server_url in SimpleXBot constructor if needed
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        # Optional cleanup
        asyncio.run(bot.close())

