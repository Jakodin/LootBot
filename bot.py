import discord
from discord.ext import commands
import json
import random
import os

# --- Configuration ---
# IMPORTANT: Replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token.
TOKEN = os.environ.get('DISCORD_TOKEN', 'MTQwNDQ1NTA0NTQ2MTgzNTg3OQ.G9AF64.31p5MDhTJKRQNsH8Pn3WfOVg7cinyz9NoM1cSc')
DATA_FILE = 'player_bonuses.json'

# --- Global Data Structures ---

# This dictionary will hold our PERMANENT player bonus data in memory.
# Key: Discord Guild ID (string)
# Value: Dictionary {User ID (string): {"bonus": int, "last_roll_item": string}}
player_bonuses_by_guild = {}

# This dictionary will hold TEMPORARY data for currently active roll sessions.
# Key: Discord Guild ID (string)
# Value: List of dictionaries, each representing a single roll session.
current_roll_sessions_by_guild = {}

# This counter ensures each new roll gets a unique ID across the bot's lifetime.
# This will be loaded from and saved to the data file.
next_roll_id = 1

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- Helper Functions for Data Persistence ---

def load_player_bonuses():
    """Loads player bonuses and the roll ID counter from the JSON file."""
    global player_bonuses_by_guild, next_roll_id
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            player_bonuses_by_guild = data.get('bonuses', {})
            next_roll_id = data.get('next_roll_id', 1)
        print(f"Loaded player data and roll ID from {DATA_FILE}")
    except FileNotFoundError:
        print(f"No {DATA_FILE} found, starting with empty player data.")
        player_bonuses_by_guild = {}
        next_roll_id = 1
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {DATA_FILE}, starting with empty player data.")
        player_bonuses_by_guild = {}
        next_roll_id = 1

def save_player_bonuses():
    """Saves player bonuses and the roll ID counter to the JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            data = {
                'bonuses': player_bonuses_by_guild,
                'next_roll_id': next_roll_id
            }
            json.dump(data, f, indent=4)
        print(f"Saved player data and roll ID to {DATA_FILE}")
    except IOError as e:
        print(f"Error saving player data to {DATA_FILE}: {e}")

# --- Utility Functions ---

def get_guild_player_data(guild_id: str):
    """Ensures guild's player data exists and returns it."""
    if guild_id not in player_bonuses_by_guild:
        player_bonuses_by_guild[guild_id] = {}
    return player_bonuses_by_guild[guild_id]

def get_guild_roll_sessions(guild_id: str):
    """Ensures guild's roll session list exists and returns it."""
    if guild_id not in current_roll_sessions_by_guild:
        current_roll_sessions_by_guild[guild_id] = []
    return current_roll_sessions_by_guild[guild_id]

# --- Bot Events ---

@bot.event
async def on_ready():
    """Event that runs when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user}!')
    print('Bot is ready to roll!')
    load_player_bonuses()

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
async def rigged(ctx):
    """
    Reassures users that the bot is not rigged.
    """
    if str(ctx.author.id) == "107171787057426432":
        await ctx.send("Yes, the bot is rigged against you, good luck winning")
    else:
        await ctx.send("The bot is not rigged, you're just unlucky!")

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

    global next_roll_id
    guild_id = str(ctx.guild.id)
    guild_roll_sessions = get_guild_roll_sessions(guild_id)

    # Create a new roll session with a unique ID
    new_session = {
        "roll_id": next_roll_id,
        "item": item_being_rolled_for,
        "initiator_id": str(ctx.author.id),
        "participants": {}
    }
    guild_roll_sessions.append(new_session)
    next_roll_id += 1 # Increment the global counter

    await ctx.send(
        f"A new roll has started for **{item_being_rolled_for}**! 🎉\n"
        f"The roll ID is **`{new_session['roll_id']}`**. Type `!join_roll {new_session['roll_id']}` to participate."
    )

@bot.command()
async def join_roll(ctx, roll_id: int):
    """
    Joins the current active rolling session on this server.
    Calculates the player's roll with their current bonus.
    Usage: !join_roll <roll_id>
    Example: !join_roll 1
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_player_bonuses = get_guild_player_data(guild_id)
    guild_roll_sessions = get_guild_roll_sessions(guild_id)

    # Find the specific roll session by its ID
    target_session = next((session for session in guild_roll_sessions if session["roll_id"] == roll_id), None)

    if not target_session:
        await ctx.send(f"No active roll session with ID **`{roll_id}`** found on this server.")
        return

    user_id = str(ctx.author.id)
    user_name = ctx.author.display_name
    item_being_rolled_for = target_session["item"]

    if user_id in target_session["participants"]:
        await ctx.send(f"{user_name}, you have already joined this roll!")
        return

    # Initialize player's persistent bonus for this guild if they're new
    if user_id not in guild_player_bonuses:
        guild_player_bonuses[user_id] = {"bonus": 0, "last_roll_item": ""}

    current_bonus = guild_player_bonuses[user_id]["bonus"]
    base_roll = random.randint(1, 100)
    final_roll = base_roll + current_bonus

    # Store the participant's roll data for this session
    target_session["participants"][user_id] = {
        "base_roll": base_roll,
        "bonus_applied": current_bonus,
        "final_roll": final_roll
    }

    await ctx.send(
        f"**{user_name}** joined the roll for **{item_being_rolled_for}**!\n"
        f"Your roll: `Base {base_roll}` + `Bonus {current_bonus}` = `Total {final_roll}`."
    )

@bot.command()
async def participants(ctx, roll_id: int):
    """
    Shows who has joined the current active roll with a specific ID on this server.
    Usage: !participants <roll_id>
    Example: !participants 1
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_roll_sessions = get_guild_roll_sessions(guild_id)

    target_session = next((session for session in guild_roll_sessions if session["roll_id"] == roll_id), None)

    if not target_session:
        await ctx.send(f"No active roll session with ID **`{roll_id}`** found on this server.")
        return

    item = target_session["item"]
    participants_list = []

    if not target_session["participants"]:
        await ctx.send(f"No one has joined the roll for **{item}** yet on this server.")
        return

    for user_id in target_session["participants"]:
        user = bot.get_user(int(user_id))
        participants_list.append(user.display_name if user else f"User {user_id} (Unknown)")

    description = f"Current participants for **{item}** (ID: `{roll_id}`) on this server:\n" + "\n".join(participants_list)
    embed = discord.Embed(
        title="Active Roll Participants",
        description=description,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def remove_participant(ctx, roll_id: int, user_to_remove: discord.User):
    """
    Removes a user from a specific active roll session on this server.
    Only the roll initiator can use this command.
    Usage: !remove_participant <roll_id> <@user_mention> or <user_id>
    Example: !remove_participant 1 @Jakodin
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_roll_sessions = get_guild_roll_sessions(guild_id)

    target_session = next((session for session in guild_roll_sessions if session["roll_id"] == roll_id), None)

    if not target_session:
        await ctx.send(f"No active roll session with ID **`{roll_id}`** found on this server.")
        return

    if str(ctx.author.id) != target_session["initiator_id"]:
        await ctx.send("🚫 You must be the initiator of this roll to remove participants.")
        return

    target_user_id = str(user_to_remove.id)
    target_user_name = user_to_remove.display_name
    item_being_rolled_for = target_session["item"]

    if target_user_id not in target_session["participants"]:
        await ctx.send(f"{target_user_name} is not currently in the roll for **{item_being_rolled_for}**.")
        return

    del target_session["participants"][target_user_id]
    await ctx.send(f"✅ {target_user_name} has been removed from the roll for **{item_being_rolled_for}**.")

@bot.command()
async def end_roll(ctx, roll_id: int):
    """
    Ends the current active rolling session with a specific ID, determines the winner,
    and applies bonus logic. Only the initiator can end it.
    Usage: !end_roll <roll_id>
    Example: !end_roll 1
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    guild_id = str(ctx.guild.id)
    guild_player_bonuses = get_guild_player_data(guild_id)
    guild_roll_sessions = get_guild_roll_sessions(guild_id)

    # Find the specific roll session by its ID
    target_session = next((session for session in guild_roll_sessions if session["roll_id"] == roll_id), None)

    if not target_session:
        await ctx.send(f"No active roll session with ID **`{roll_id}`** found on this server.")
        return

    if str(ctx.author.id) != target_session["initiator_id"]:
        await ctx.send("Only the person who started the roll can end it.")
        return

    item_being_rolled_for = target_session["item"]
    participants = target_session["participants"]

    if not participants:
        await ctx.send(f"The roll for **{item_being_rolled_for}** (ID: `{roll_id}`) ended with no participants on this server. No winner, no bonus changes.")
        # Remove the empty roll session
        guild_roll_sessions.remove(target_session)
        return

    winner_id = None
    highest_roll = -1

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
    winner_mention = winner_user.mention if winner_user else f"User {winner_id}"

    roll_summary_lines = [f"--- Roll Results for **{item_being_rolled_for}** (ID: `{roll_id}`) on this server ---"]
    for user_id, data in sorted_participants_list:
        user = bot.get_user(int(user_id))
        user_name = user.display_name if user else f"User {user_id}"
        roll_summary_lines.append(
            f"**{user_name}**: (Base {data['base_roll']} + Bonus {data['bonus_applied']}) = **{data['final_roll']}**"
        )
    roll_summary_lines.append(f"\n--- **{winner_mention}** wins the roll with a **{highest_roll}**! 🎉 ---")
    await ctx.send("\n".join(roll_summary_lines))

    bonus_changes_message_lines = ["__Bonus Updates:__"]
    for player_id in participants.keys():
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

    # Remove the completed roll session from the list
    guild_roll_sessions.remove(target_session)
    save_player_bonuses()

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