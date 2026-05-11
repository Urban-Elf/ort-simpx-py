import asyncio
import os
import random
from types import MethodType
import sys
from ort.filter import ProfanityFilter
from simpx import BotProfile, SimpleXBot
from ort import ort

ort.load_default_config()

# 1. Create a bot profile (can be saved/loaded)
# If a profile with this name exists, it will be loaded.
# Otherwise, a new one is created on the server.
profile = BotProfile(
    display_name=ort.CONFIG.display_name,
    full_name=ort.CONFIG.profile_name,
    description=ort.CONFIG.description,
    # Optional: Welcome message for new contacts
    welcome_message=ort.CONFIG.welcome_msg,
    # Optional: Set command prefix (default is "!")
    command_prefix=ort.CONFIG.command_prefix,
    image=ort.CONFIG.image_path["path"]
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
        ort.CONFIG.shutdown_msg % ort.CONFIG.version)
    await bot.close()
    sys.exit(0)

# Really handy if you're running headless, but be careful not to run on test machines. Alternatively, ignore all warnings. YOLO, my dude.
@bot.command(name="shutdown_os", help="Shutdown bot and OS")
async def shutdown_command(chat_info, args):
    await bot.send_message(
        chat_info,
        ort.CONFIG.shutdown_msg % ort.CONFIG.version)
    await bot.close()
    if ort.CONFIG.allow_os_commands:
        if sys.platform == "win32":
            os.system("shutdown /s /t 1")
        elif sys.platform == "linux":
            os.system("shutdown now")
        elif sys.platform == "darwin":
            os.system("sudo shutdown -h now")
        else:
            print("Unsupported OS for shutdown command. Try not using a mobile device.")
    sys.exit(0)

@bot.command(name="load_config", help="Temporarily switch LLM config")
async def load_config_command(chat_info, args):
    err_msg = None
    if (args is None) or (len(args.strip()) == 0):
        err_msg = "!4 Please provide a config name to load.!"
        return
    elif not os.path.exists(args.strip()):
        err_msg = f"!4 Config file not found.!"
    if err_msg:
        await bot.send_message(chat_info, err_msg)
    try:
        ort.load_config(args)
        await bot.send_message(
            chat_info,
            "!2 Switched config -> '" + args + "'!")
    except Exception as e:
        await bot.send_message(
            chat_info,
            f"!1 Load failed: {str(e)}")
        

@bot.command(name="reload_config", help="Reload current LLM config")
async def reload_config(chat_info, args):
    try:
        ort.load_config(ort.CONFIG_PATH)
        await bot.send_message(
            chat_info,
            "!1 Reload successful.!")
    except Exception as e:
        await bot.send_message(
            chat_info,
            f"!2 Reload failed: {str(e)}!")

# 4. Define event handlers (optional)
@bot.event("contactConnected")
async def handle_connection(response):
  """Handles new contact connections (alternative to welcome_message)."""
  contact = response.get("contact", {})
  display_name = contact.get("profile", {}).get("displayName", "Unknown")
  print(f"{display_name} connected!")

profanity_filter = ProfanityFilter()

async def handle_message(self, msg_text, chat_info):
    if (msg_text is None) or (chat_info is None):
        return
    if (len(msg_text.strip()) == 0):
        return
    result = ort.should_respond(msg_text)
    if result["respond"]:
        reply = ort.get_response(msg_text)
        await bot.send_message(chat_info, profanity_filter.filter_text(reply))
    else:
        if result["response"] is not None:
            await bot.send_message(chat_info, profanity_filter.filter_text(result["response"]))

bot.message_received = MethodType(handle_message, bot)

# 5. Start the bot
if __name__ == "__main__":
    print("Starting bot... This little maneuver is going to cost us fifty-one years.")
    # Ensure your SimpleX Chat Console (simplex-chat) backend is running
    # The bot will connect via WebSocket (default: ws://127.0.0.1:5225)
    # You can specify a different server_url in SimpleXBot constructor if needed
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("Bot stopped. Hasta la vista.")
    finally:
        # Optional cleanup
        asyncio.run(bot.close())

