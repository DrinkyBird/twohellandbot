import discord
from discord.ext import commands
import config
import quotes
import systems
import announce
import identicon
import admin
import stats
import sex

client = commands.Bot(command_prefix=config.COMMAND_PREFIX)
client.add_cog(systems.SystemsCog())
client.add_cog(quotes.QuotesCog(client))
client.add_cog(identicon.IdenticonCog())
client.add_cog(announce.AnnouncementsCog(client))
client.add_cog(admin.AdminCog(client))
client.add_cog(stats.StatsCog(client))
client.add_cog(sex.SexCog(client))

@client.event
async def on_command(ctx):
    stats.increment_stat("commands_executed")

client.run(config.BOT_TOKEN)