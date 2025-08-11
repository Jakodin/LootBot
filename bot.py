import discord
from discord.ext import commands

# Sets the intent to allow the bot to read message content.
intents = discord.Intents.default()
intents.message_content = True

# The 'commands.Bot' class is used for bots that have commands like '!hello'.
# The prefix tells the bot what to look for at the start of a command.
bot = commands.Bot(command_prefix='!', intents=intents)

# This event runs when the bot successfully connects to Discord.
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    print('Bot is ready to roll!')

# This creates a command named 'hello'. To use it, you'd type '!hello'.
@bot.command()
async def hello(ctx):
    await ctx.send('Hello there!')

# Replace 'YOUR_BOT_TOKEN_HERE' with the token you copied from the Discord Developer Portal.
bot.run('MTQwNDQ1NTA0NTQ2MTgzNTg3OQ.GghN-y.DfxKMkzSY4UTL9EzWfxeFLr_aTQ-Ot4DVI3beY')