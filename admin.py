import discord
from discord.ext import commands
import config
import sys

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Speaks a thing", usage="<text>", hidden=True)
    async def say(self, ctx, target, *args):
        if ctx.author.id in config.ADMINS:
            if len(args) < 1:
                await ctx.send('<@%d> Syntax: `%ssay <channel ID> <text>`' % (ctx.author.id, config.COMMAND_PREFIX))
                return

            text = ' '.join(args)

            try:
                channel = self.bot.get_channel(int(target))
                await channel.send(text)
            except Exception as e:
                await ctx.send('An error occured (`' + str(e) + '`) - channel doesn\'t exist, is in invalid format, or isn\'t accessible by the bot')

    @commands.command(help="Kills the bot", hidden=True)
    async def exit(self, ctx):
        if ctx.author.id in config.ADMINS:
            await self.bot.close()
            sys.exit()