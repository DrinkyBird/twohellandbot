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
            "Why don't you go abuse <@115424328576663557>'s styrofoam hole instead",
            "<@&739564035648782487>s please help",
            "No. Go read the Neon Bible instead.",
            "SINNER!",
            f"NO! EVERYONE SHAME {ctx.author.mention}",
            "I am currently being attacked by a swarm of bees. Please try again later.",
            "I'm only 3 years old...",
            "Sorry, you look too much like Dan Schneider"
        ]), allowed_mentions=discord.AllowedMentions(everyone=False, users=[ctx.author], roles=False, replied_user=True))
