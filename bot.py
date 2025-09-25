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
# Allowed role for level commands
# ------------------------------
ALLOWED_ROLE_ID = 1412532422167236679

# ------------------------------
# Flask app to keep Render awake
# ------------------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

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
    # ------------------------------
    # CHANGE THE MESSAGE BELOW TO YOUR PREFERRED HELP TEXT
    # ------------------------------
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
    list_position: int  # New input
):
    # Check role
    member = interaction.user
    if ALLOWED_ROLE_ID not in [role.id for role in member.roles]:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    # Map list to folder
    folder_map = {
        "Demon List": "list",
        "Challenge List": "clist",
        "Impossible List": "ilist"
    }
    folder = folder_map[list_name.value]

    # Prepare JSON file for the level
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

    # Create JSON if it doesn't exist
    try:
        repo.get_contents(file_path)
        await interaction.followup.send(f"⚠️ `{level_name}` already exists in `{folder}`!")
    except:
        repo.create_file(file_path, commit_message, content_str)
        await interaction.followup.send(f"✅ `{level_name}` created in `{folder}`.")

    # ------------------------------
    # Insert level into array at the given position
    # ------------------------------
    array_file_map = {
        "list": "data/_list.json",
        "clist": "data/_clist.json",
        "ilist": "data/_ilist.json"
    }
    array_file_path = array_file_map[folder]

    try:
        array_file = repo.get_contents(array_file_path)
        array_content = json.loads(array_file.decoded_content.decode())

        # Convert user line number to 0-based index
        insert_index = max(0, min(len(array_content), list_position - 1))
        array_content.insert(insert_index, level_name)

        array_str = json.dumps(array_content, indent=4)
        repo.update_file(array_file.path, f"Insert {level_name} at position {list_position} in {array_file_path}", array_str, array_file.sha)
        await interaction.followup.send(f"✅ `{level_name}` inserted into `{array_file_path}` at position {list_position}.")
        print(f"Inserted {level_name} into {array_file_path} at position {list_position} via /list_add")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Could not update array file `{array_file_path}`.")
        print(f"Array insert error: {e}")

# ------------------------------
# /list delete command
# ------------------------------
@bot.tree.command(name="list_delete", description="Delete a level from a list")
@app_commands.describe(
    list_name="Select which list to delete the level from",
    level_name="Name of the level to delete"
)
@app_commands.choices(list_name=[
    app_commands.Choice(name="Demon List", value="Demon List"),
    app_commands.Choice(name="Challenge List", value="Challenge List"),
    app_commands.Choice(name="Impossible List", value="Impossible List")
])
async def list_delete_command(
    interaction: discord.Interaction,
    list_name: app_commands.Choice[str],
    level_name: str
):
    # Check role
    member = interaction.user
    if ALLOWED_ROLE_ID not in [role.id for role in member.roles]:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    # Map user choice to GitHub folder
    folder_map = {
        "Demon List": "list",
        "Challenge List": "clist",
        "Impossible List": "ilist"
    }
    folder = folder_map[list_name.value]

    # Delete level JSON
    file_path = f"data/{folder}/{level_name}.json"
    try:
        file = repo.get_contents(file_path)
        repo.delete_file(file.path, f"Delete {level_name} from {folder}", file.sha)
        await interaction.followup.send(f"✅ `{level_name}` deleted from `{folder}`.")
        print(f"Deleted {file_path} on GitHub via /list_delete by {interaction.user}")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Could not find `{level_name}.json` in `{folder}`.")
        print(f"Delete JSON error: {e}")

    # Delete level from array file
    array_file_map = {
        "list": "data/_list.json",
        "clist": "data/_clist.json",
        "ilist": "data/_ilist.json"
    }
    array_file_path = array_file_map[folder]

    try:
        array_file = repo.get_contents(array_file_path)
        array_content = json.loads(array_file.decoded_content.decode())

        if level_name in array_content:
            array_content.remove(level_name)
            array_str = json.dumps(array_content, indent=4)
            repo.update_file(array_file.path, f"Remove {level_name} from {array_file_path}", array_str, array_file.sha)
            await interaction.followup.send(f"✅ `{level_name}` removed from `{array_file_path}`.")
            print(f"Removed {level_name} from {array_file_path} via /list_delete")
        else:
            await interaction.followup.send(f"⚠️ `{level_name}` not found in `{array_file_path}`.")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Could not access array file `{array_file_path}`.")
        print(f"Delete array error: {e}")

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
