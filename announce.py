import discord
from discord.ext import commands
import config

def member_had_role(member):
    for role in member.roles:
        if role.id in config.WELCOME_ROLES:
            return True
    return False

class AnnouncementsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generic_announce(self, string, member):
        chan = self.bot.get_channel(config.ANNOUNCE_CHANNEL)
        if not chan is None:
            await chan.send(string % (member.mention,))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        in_before = member_had_role(before)
        in_after = member_had_role(after)

        if not in_before and in_after:
            await self.generic_announce(config.WELCOME_MESSAGE, after)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member_had_role(member):
            await self.generic_announce(config.WELCOME_MESSAGE, member)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild.id != config.ANNOUNCE_SERVER:
            return

        if message.type == discord.MessageType.premium_guild_subscription:
            await self.generic_announce(config.BOOST_MESSAGE, message.author)
        elif message.type == discord.MessageType.premium_guild_tier_1:
            await self.generic_announce(config.BOOST_LEVEL1_MESSAGE, message.author)
        elif message.type == discord.MessageType.premium_guild_tier_2:
            await self.generic_announce(config.BOOST_LEVEL2_MESSAGE, message.author)
        elif message.type == discord.MessageType.premium_guild_tier_3:
            await self.generic_announce(config.BOOST_LEVEL3_MESSAGE, message.author)