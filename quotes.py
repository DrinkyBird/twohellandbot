import discord
import config
from discord.ext import commands
import db
import datetime
import time
import random

BURNISH_FACE_IMG = "https://tohellandbot.s3-eu-west-1.amazonaws.com/static/RichardBurnishface.jpg"
ADJECTIVES = [
    "insightful",
    "wonderful",
    "amazing",
    "lovely",
    "stunning"
]

class QuotesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_speaker(self, id):
        cur = db.get_cursor()

        db.execute(cur, 'SELECT * FROM quote_speakers WHERE id=? LIMIT 1', (id,))

        return cur.fetchone()

    @commands.command(help="Returns a quote from the database", usage="[id]")
    async def quote(self, ctx, id=-1):
        cur = db.get_cursor()

        # specific quote id
        if id != -1:
            db.execute(cur, 'SELECT * FROM quotes WHERE id=? LIMIT 1', (id,))
        # random quote
        else:
            db.execute(cur, 'SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1')

        row = cur.fetchone()

        if row is None:
            await ctx.send('There is no quote with ID ' + str(id))
        else:
            user = self.bot.get_user(int(row["submitter"]))
            username = row["submitter_name"]
            if not user is None:
                username = user.name

            speaker = self.get_speaker(row["speaker"])
            dt = datetime.datetime.utcfromtimestamp(row["date"] / 1000)
            embed = discord.Embed(title='Quote #' + str(row["id"]), colour=0xFFFFFF, description=row["text"], timestamp=dt)
            embed.set_author(name=speaker["name"], icon_url=speaker["picture_url"], url="http://bot.montclairpublicaccess.info/quotes.php")
            embed.set_footer(text="Submitted by " + username)
            await ctx.send(embed=embed)

    @commands.command(help="Submit a quote to the database", usage="<text>")
    async def addquote(self, ctx, *args):
        await ctx.send("Please use the website to add quotes: <http://bot.montclairpublicaccess.info/quotes.php>")

    @commands.command(help="Delete a quote from the database", usage="<id>")
    async def delquote(self, ctx, id):
        await ctx.send("Please use the website to delete quotes: <http://bot.montclairpublicaccess.info/quotes.php>")

    @commands.command(help="Edit a quote in the database", usage="<id> <text>")
    async def editquote(self, ctx, id, *args):
        await ctx.send("Please use the website to edit quotes: <http://bot.montclairpublicaccess.info/quotes.php>")

    @commands.command(help="Shows statistics about the quote database")
    async def quotestats(self, ctx):

        cur = db.get_cursor()
        db.execute(cur, 'SELECT COUNT(id) FROM quotes')
        row = cur.fetchone()

        if not row:
            await ctx.send('Failed to get stats')
            return

        embed = discord.Embed(title="Quote Database Statistics", color=0x1ABC9C)
        embed.add_field(name="Number of quotes", value=row[0])

        await ctx.send(embed=embed)