from discord.ext import commands

class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def blachool(self, ctx):
        emoji = self.bot.get_emoji(727669022065295382)
        if emoji is not None:
            try:
                await ctx.message.add_reaction(emoji)
            except:
                pass
