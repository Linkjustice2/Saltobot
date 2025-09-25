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
DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_REPO = "Linkjustice2/saltoback-demonlist"

# ------------------------------
# Flask app to keep Repl/Render awake
# ------------------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Run Flask in a separate thread
Thread(target=run).start()

# ------------------------------
# Discord bot setup
# ------------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to GitHub
g = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = g.get_repo(GITHUB_REPO)
print(f"Connected to GitHub repo: {repo.full_name}")

# ------------------------------
# /help command
# ------------------------------
@bot.tree.command(name="help", description="Simple help command")
async def help_command(interaction: discord.Interaction):
    # CHANGE THE MESSAGE BELOW TO YOUR PREFERRED HELP TEXT
    message = "Hello! This is your help message. Change this text to whatever you like."
    await interaction.response.send_message(message)
    print(f"/help used by {interaction.user}")

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
    video_link="Video link for the level"
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
    video_link: str
):
    await interaction.response.defer()

    # Map user choice to GitHub folder
    folder_map = {
        "Demon List": "list",
        "Challenge List": "clist",
        "Impossible List": "ilist"
    }
    folder = folder_map[list_name.value]

    # File path
    file_path = f"data/{folder}/{level_name}.json"

    # JSON content
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

    # Convert to string and ensure {} wrapping
    content_str = json.dumps(file_content, indent=4)
    content_str = "{\n" + content_str[1:-1] + "\n}"

    commit_message = f"Added {level_name} to {folder}"

    # Check if file exists, create if not
    try:
        repo.get_contents(file_path)
        await interaction.followup.send(f"⚠️ `{level_name}.json` already exists in `{folder}`!")
    except:
        repo.create_file(file_path, commit_message, content_str)
        await interaction.followup.send(f"✅ `{level_name}.json` created in `{folder}`.")
        print(f"Created {file_path} on GitHub via /list add by {interaction.user}")

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
