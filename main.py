import discord
from discord.ext import commands
import config
import quotes
import db
import systems
import identicon

client = commands.Bot(command_prefix=config.COMMAND_PREFIX)
client.add_cog(quotes.QuotesCog())
client.add_cog(systems.SystemsCog())
client.add_cog(identicon.IdenticonCog())
client.run(config.BOT_TOKEN)