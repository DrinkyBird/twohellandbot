import discord
from discord.ext import commands
import config

def member_had_role(member):
    for role in member.roles:
        if role.id in config.WELCOME_ROLES:
            return True
    return False

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def announce_join(self, member):
        chan = self.bot.get_channel(config.WELCOME_CHANNEL)
        if not chan is None:
            await chan.send('Welcome aboard the Ark, %s! Thanks for supporting the show.' % (member.mention,))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        in_before = member_had_role(before)
        in_after = member_had_role(after)

        if not in_before and in_after:
            await self.announce_join(after)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member_had_role(member):
            await self.announce_join(member)