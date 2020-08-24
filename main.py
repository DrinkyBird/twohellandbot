import discord
from discord.ext import commands
import config
import quotes
import db
import systems
import welcome
import identicon
import admin

client = commands.Bot(command_prefix=config.COMMAND_PREFIX)
client.add_cog(quotes.QuotesCog())
client.add_cog(systems.SystemsCog())
client.add_cog(identicon.IdenticonCog())
client.add_cog(welcome.WelcomeCog(client))
client.add_cog(admin.AdminCog(client))
client.run(config.BOT_TOKEN)