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
import obkov
import misc
import ud
import eightball

intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)
client.add_cog(quotes.QuotesCog(client))
client.add_cog(systems.SystemsCog())
client.add_cog(identicon.IdenticonCog())
client.add_cog(announce.AnnouncementsCog(client))
client.add_cog(admin.AdminCog(client))
client.add_cog(stats.StatsCog(client))
client.add_cog(sex.SexCog(client))
client.add_cog(obkov.ObkovCog(client))
client.add_cog(misc.MiscCog(client))
client.add_cog(ud.UdCog(client))
client.add_cog(eightball.EightBallCog())

@client.event
async def on_command(ctx):
    stats.increment_stat("commands_executed")

@client.event
async def on_ready():
    for user in client.users:
        stats.update_user(user)

client.run(config.BOT_TOKEN)