import discord
from discord.ext import commands
import json
import random
import asyncio
import os # Added for environment variables in case you use Replit

# --- Configuration ---
# IMPORTANT: Replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token.
# If you're using Replit, use os.environ['DISCORD_TOKEN'] as discussed before.
TOKEN = os.environ.get('DISCORD_TOKEN')
DATA_FILE = 'player_bonuses.json' # File to store persistent player bonuses

# --- Global Data Structures ---

# This dictionary will hold our PERMANENT player bonus data in memory.
# Key: Discord Guild ID (string)
# Value: Dictionary {User ID (string): {"bonus": int, "last_roll_item": string}}
player_bonuses_by_guild = {}

# This dictionary will hold TEMPORARY data for currently active roll sessions.
# Key: Discord Guild ID (string)
# Value: Dictionary {"active": bool, "item": str, "initiator_id": str, "participants": {User ID (str): {"base_roll": int, "bonus_applied": int, "final_roll": int}}}
current_roll_sessions_by_guild = {}

# --- Discord Bot Setup ---
# Sets the intent to allow the bot to read message content.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Required for fetching member data reliably (display names)

# The 'commands.Bot' class is used for bots that have commands.
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Helper Functions for Data Persistence ---

def load_player_bonuses():
    """Loads player bonuses from the JSON file, now keyed by guild."""
    global player_bonuses_by_guild
    try:
        with open(DATA_FILE, 'r') as f:
            player_bonuses_by_guild = json.load(f)
        print(f"Loaded player data from {DATA_FILE}")
    except FileNotFoundError:
        print(f"No {DATA_FILE} found, starting with empty player data.")
        player_bonuses_by_guild = {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {DATA_FILE}, starting with empty player data.")
        player_bonuses_by_guild = {}

def save_player_bonuses():
    """Saves player bonuses to the JSON file, now keyed by guild."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(player_bonuses_by_guild, f, indent=4) # indent for pretty-printing
        print(f"Saved player data to {DATA_FILE}")
    except IOError as e:
        print(f"Error saving player data to {DATA_FILE}: {e}")

# --- Utility Functions ---

def get_guild_player_data(guild_id: str):
    """Ensures guild's player data exists and returns it."""
    if guild_id not in player_bonuses_by_guild:
        player_bonuses_by_guild[guild_id] = {}
    return player_bonuses_by_guild[guild_id]

def get_guild_roll_session(guild_id: str):
    """Ensures guild's roll session data exists and returns it."""
    if guild_id not in current_roll_sessions_by_guild:
        current_roll_sessions_by_guild[guild_id] = {
            "active": False,
            "item": None,
            "initiator_id": None,
            "participants": {}
        }
    return current_roll_sessions_by_guild[guild_id]

# --- Bot Events ---

@bot.event
async def on_ready():
    """Event that runs when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user}!')
    print('Bot is ready to roll!')
    load_player_bonuses() # Load persistent data when the bot starts

@bot.event
async def on_disconnect():
    """Event that runs when the bot disconnects, ensuring data is saved."""
    print("Bot disconnecting, saving data...")
    save_player_bonuses()

# --- Bot Commands ---

@bot.command()
async def hello(ctx):
    """Greets the user back with a friendly message."""
    await ctx.send('Hello there!')

@bot.command()
async def start_roll(ctx, *, item_being_rolled_for: str):
    """
    Starts a new rolling session for a specific item on this server.
    Usage: !start_roll <item_name>
    Example: !start_roll The Legendary Sword of Awesomeness
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_roll_session = get_guild_roll_session(guild_id)

    if guild_roll_session["active"]:
        await ctx.send(f"A roll for **{guild_roll_session['item']}** is already active on this server! Please `!end_roll` it first.")
        return

    guild_roll_session["active"] = True
    guild_roll_session["item"] = item_being_rolled_for
    guild_roll_session["initiator_id"] = str(ctx.author.id)
    guild_roll_session["participants"] = {} # Clear participants from previous rolls

    await ctx.send(
        f"A new roll has started for **{item_being_rolled_for}**! 🎉\n"
        f"Type `!join_roll` to participate."
    )

@bot.command()
async def join_roll(ctx):
    """
    Joins the current active rolling session on this server.
    Calculates the player's roll with their current bonus.
    Usage: !join_roll
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_player_bonuses = get_guild_player_data(guild_id)
    guild_roll_session = get_guild_roll_session(guild_id)

    if not guild_roll_session["active"]:
        await ctx.send("No active roll session on this server. Start one with `!start_roll <item_name>`.")
        return

    user_id = str(ctx.author.id)
    user_name = ctx.author.display_name
    item_being_rolled_for = guild_roll_session["item"]

    if user_id in guild_roll_session["participants"]:
        await ctx.send(f"{user_name}, you have already joined this roll!")
        return

    # Initialize player's persistent bonus for this guild if they're new
    if user_id not in guild_player_bonuses:
        guild_player_bonuses[user_id] = {"bonus": 0, "last_roll_item": ""}

    current_bonus = guild_player_bonuses[user_id]["bonus"]
    base_roll = random.randint(1, 100)
    final_roll = base_roll + current_bonus

    # Store the participant's roll data for this session
    guild_roll_session["participants"][user_id] = {
        "base_roll": base_roll,
        "bonus_applied": current_bonus,
        "final_roll": final_roll
    }

    await ctx.send(
        f"**{user_name}** joined the roll for **{item_being_rolled_for}**!\n"
        f"Your roll: `Base {base_roll}` + `Bonus {current_bonus}` = `Total {final_roll}`."
    )

@bot.command()
async def participants(ctx):
    """
    Shows who has joined the current active roll on this server.
    Usage: !participants
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_roll_session = get_guild_roll_session(guild_id)

    if not guild_roll_session["active"]:
        await ctx.send("There is no active roll session on this server to list participants for.")
        return

    item = guild_roll_session["item"]
    participants_list = []

    if not guild_roll_session["participants"]:
        await ctx.send(f"No one has joined the roll for **{item}** yet on this server.")
        return

    for user_id in guild_roll_session["participants"]:
        user = bot.get_user(int(user_id)) # Get user from bot's cache (cross-guild)
        participants_list.append(user.display_name if user else f"User {user_id} (Unknown)")

    description = f"Current participants for **{item}** on this server:\n" + "\n".join(participants_list)
    embed = discord.Embed(
        title="Active Roll Participants",
        description=description,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command()
async def remove_participant(ctx, user_to_remove: discord.User):
    """
    Removes a user from the current active roll session on this server.
    Only the roll initiator can use this command.
    Usage: !remove_participant <@user_mention> or <user_id>
    Example: !remove_participant @Jakodin
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_roll_session = get_guild_roll_session(guild_id)

    if not guild_roll_session["active"]:
        await ctx.send("No active roll session on this server to remove participants from.")
        return

    # Check if the command invoker is the roll initiator
    if str(ctx.author.id) != guild_roll_session["initiator_id"]:
        await ctx.send("🚫 You must be the initiator of this roll to remove participants.")
        return

    target_user_id = str(user_to_remove.id)
    target_user_name = user_to_remove.display_name

    if target_user_id not in guild_roll_session["participants"]:
        await ctx.send(f"{target_user_name} is not currently in the roll for **{guild_roll_session['item']}** on this server.")
        return

    del guild_roll_session["participants"][target_user_id]
    await ctx.send(f"✅ {target_user_name} has been removed from the roll for **{guild_roll_session['item']}** on this server.")


@bot.command()
async def end_roll(ctx):
    """
    Ends the current active rolling session on this server, determines the winner,
    and applies bonus logic. Only the initiator can end it.
    Usage: !end_roll
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_player_bonuses = get_guild_player_data(guild_id)
    guild_roll_session = get_guild_roll_session(guild_id)


    if not guild_roll_session["active"]:
        await ctx.send("No active roll session on this server to end.")
        return

    # Restrict who can end the roll to the initiator
    if str(ctx.author.id) != guild_roll_session["initiator_id"]:
        await ctx.send("Only the person who started the roll can end it.")
        return

    item_being_rolled_for = guild_roll_session["item"]
    participants = guild_roll_session["participants"]

    if not participants:
        await ctx.send(f"The roll for **{item_being_rolled_for}** ended with no participants on this server. No winner, no bonus changes.")
        # Reset current roll session for this guild
        current_roll_sessions_by_guild[guild_id] = {
            "active": False,
            "item": None,
            "initiator_id": None,
            "participants": {}
        }
        return

    # Determine the winner
    winner_id = None
    highest_roll = -1

    # In case of ties, the first person in the sorted list (which is stable) wins.
    # We sort by final_roll in descending order.
    sorted_participants_list = sorted(participants.items(), key=lambda item: item[1]['final_roll'], reverse=True)

    tied_winners = []

    if sorted_participants_list:
        highest_roll = sorted_participants_list[0][1]['final_roll']
        for user_id, data in sorted_participants_list:
            if data['final_roll'] == highest_roll:
                tied_winners.append(user_id)
            else:
                break

    if len(tied_winners) > 1:
        winner_id = random.choice(tied_winners)
        tie_message = "It's a tie! Randomly picking a winner from: "
        tied_names = []
        for tied_id in tied_winners:
            user_obj = bot.get_user(int(tied_id))
            tied_names.append(user_obj.display_name if user_obj else f"User {tied_id}")
        tie_message += ", ".join(tied_names) + "\n"
        await ctx.send(tie_message)
    else:
        winner_id = sorted_participants_list[0][0]

    winner_user = bot.get_user(int(winner_id))
    winner_name = winner_user.display_name if winner_user else f"User {winner_id}"

    roll_summary_lines = [f"--- Roll Results for **{item_being_rolled_for}** on this server ---"]
    for user_id, data in sorted_participants_list:
        user = bot.get_user(int(user_id))
        user_name = user.display_name if user else f"User {user_id}"
        roll_summary_lines.append(
            f"**{user_name}**: (Base {data['base_roll']} + Bonus {data['bonus_applied']}) = **{data['final_roll']}**"
        )
    roll_summary_lines.append(f"\n--- **{winner_name}** wins the roll with a **{highest_roll}**! ---")
    await ctx.send("\n".join(roll_summary_lines))

    # Apply bonus logic: winner's bonus resets, others' bonus increases
    bonus_changes_message_lines = ["__Bonus Updates:__"]
    for player_id, data in participants.items():
        user_obj = bot.get_user(int(player_id))
        player_name = user_obj.display_name if user_obj else f"User {player_id}"

        if player_id == winner_id:
            guild_player_bonuses[player_id]["bonus"] = 0
            guild_player_bonuses[player_id]["last_roll_item"] = item_being_rolled_for
            bonus_changes_message_lines.append(f"**{player_name}**: Bonus reset to `0`.")
        else:
            guild_player_bonuses[player_id]["bonus"] += 1
            guild_player_bonuses[player_id]["last_roll_item"] = item_being_rolled_for
            bonus_changes_message_lines.append(f"**{player_name}**: Bonus increased to `+{guild_player_bonuses[player_id]['bonus']}`.")

    await ctx.send("\n".join(bonus_changes_message_lines))

    # Reset the current roll session for this guild
    current_roll_sessions_by_guild[guild_id] = {
        "active": False,
        "item": None,
        "initiator_id": None,
        "participants": {}
    }
    save_player_bonuses() # Save persistent data after every roll

@bot.command()
async def bonuses(ctx):
    """
    Displays the current persistent bonuses for all players on this server.
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_player_bonuses = get_guild_player_data(guild_id)

    if not guild_player_bonuses:
        await ctx.send("No players have rolled yet on this server, so no bonuses to display!")
        return

    bonus_list = []
    for user_id, data in guild_player_bonuses.items():
        user = bot.get_user(int(user_id))
        user_name = user.display_name if user else f"User {user_id} (Left Server?)"
        bonus_list.append(f"**{user_name}**: `+{data['bonus']}` (Last roll for: {data['last_roll_item'] or 'N/A'})")

    embed = discord.Embed(
        title=f"Current Player Bonuses for {ctx.guild.name}",
        description="\n".join(bonus_list) if bonus_list else "No bonuses to display yet.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)
# --- Run the Bot ---
bot.run(TOKEN)
