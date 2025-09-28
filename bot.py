import discord
from discord.ext import commands
from discord import app_commands
from github import Github, Auth
import json
import os
from flask import Flask
from threading import Thread

# ------------------------------
# Tokens from environment variables
# ------------------------------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "Linkjustice2/saltoback-demonlist"

# ------------------------------
# Allowed role for level commands
# ------------------------------
ALLOWED_ROLE_ID = 1412532422167236679

# ------------------------------
# Discord bot setup
# ------------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to GitHub
g = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = g.get_repo(GITHUB_REPO)
print(f"Connected to GitHub repo: {repo.full_name}")

# ------------------------------
# Flask app for UptimeRobot
# ------------------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is online!", 200

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

# Start Flask in a separate thread
t = Thread(target=run)
t.start()

# ------------------------------
# /help command
# ------------------------------
@bot.tree.command(name="help", description="Simple help command")
async def help_command(interaction: discord.Interaction):
    message = "Hello! This is your help message. Change this text to whatever you like."
    await interaction.response.send_message(message)
    print(f"/help used by {interaction.user}")

# ------------------------------
# Role check helper
# ------------------------------
async def has_allowed_role(interaction: discord.Interaction):
    member = interaction.guild.get_member(interaction.user.id)
    if member is None:
        return False
    return ALLOWED_ROLE_ID in [role.id for role in member.roles]

# ------------------------------
# /list add command
# ------------------------------
@bot.tree.command(name="list_add", description="Add a level to a list")
@app_commands.describe(
    list_name="Select which list to add the level to",
    level_name="Name of the level",
    level_id="ID of the level",
    level_author="Author of the level",
    level_verifier="Verifier of the level",
    video_link="Video link for the level",
    list_position="Position in the list array (line number, starting at 1)"
)
@app_commands.choices(list_name=[
    app_commands.Choice(name="Demon List", value="Demon List"),
    app_commands.Choice(name="Challenge List", value="Challenge List"),
    app_commands.Choice(name="Impossible List", value="Impossible List")
])
async def list_add_command(
    interaction: discord.Interaction,
    list_name: app_commands.Choice[str],
    level_name: str,
    level_id: str,
    level_author: str,
    level_verifier: str,
    video_link: str,
    list_position: int
):
    if not await has_allowed_role(interaction):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    folder_map = {
        "Demon List": "list",
        "Challenge List": "clist",
        "Impossible List": "ilist"
    }
    folder = folder_map[list_name.value]

    file_path = f"data/{folder}/{level_name}.json"
    file_content = {
        "id": level_id,
        "name": level_name,
        "author": level_author,
        "creators": [level_author],
        "verifier": level_verifier,
        "verification": video_link,
        "percentToQualify": "100",
        "password": "N/A",
        "records": []
    }
    content_str = json.dumps(file_content, indent=4)
    content_str = "{\n" + content_str[1:-1] + "\n}"
    commit_message = f"Add {level_name}.json to {folder} via /list add"

    try:
        repo.get_contents(file_path)
        await interaction.followup.send(f"⚠️ `{level_name}.json` already exists in `{folder}`!")
    except:
        repo.create_file(file_path, commit_message, content_str)
        await interaction.followup.send(f"✅ `{level_name}` created in `{folder}`.")

    array_file_map = {
        "list": "data/_list.json",
        "clist": "data/_clist.json",
        "ilist": "data/_ilist.json"
    }
    array_file_path = array_file_map[folder]

    try:
        array_file = repo.get_contents(array_file_path)
        array_content = json.loads(array_file.decoded_content.decode())
        insert_index = max(0, min(len(array_content), list_position - 1))
        array_content.insert(insert_index, level_name)
        array_str = json.dumps(array_content, indent=4)
        repo.update_file(array_file.path, f"Insert {level_name} at position {list_position} in {array_file_path}", array_str, array_file.sha)
        await interaction.followup.send(f"✅ `{level_name}` inserted into `{array_file_path}` at position {list_position}.")
        print(f"Inserted {level_name} into {array_file_path} via /list_add")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Could not update array file `{array_file_path}`.")
        print(f"Array insert error: {e}")

# ------------------------------
# /list delete command
# ------------------------------
# ... keep your existing /list_delete code here unchanged ...

# ------------------------------
# On ready
# ------------------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} global command(s)")
    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Bot online as {bot.user}")

# ------------------------------
# Run bot
# ------------------------------
bot.run(DISCORD_TOKEN)
