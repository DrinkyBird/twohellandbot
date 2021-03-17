# Dumb meme module
import discord
from discord.ext import commands
import util
import random

class SexCog(commands.Cog):
    @commands.command(hidden=True, aliases=['sexwithseamenator', 'sexwithtohellandbot'])
    async def sex(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        await ctx.reply(random.choice([
            "Abstinence is good for the soul",
            "Pre-marital sex is a sin.",
            "No.",
            "Why don't you go abuse <@115424328576663557>'s styrofoam hole instead"
        ]))
