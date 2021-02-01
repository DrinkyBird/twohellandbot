from discord.ext import commands
import asyncio
import random

BLACHOOL_RESPONSES = [
    [ 727669022065295382 ],
    [ 799359301176000562 ],
    [ "🇭", "🇪", "🇱", "🇵" ],
    [ "🇧", "🇮", "🇬", "🅱" ]
]

class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def blachool(self, ctx):
        response = random.choice(BLACHOOL_RESPONSES)
        print(str(response))

        for emoji in response:
            e = emoji
            if isinstance(emoji, int):
                e = self.bot.get_emoji(emoji)
            try:
                await ctx.message.add_reaction(e)
                await asyncio.sleep(0.1)
            except:
                raise