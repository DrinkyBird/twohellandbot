import discord
import config
from discord.ext import commands
import db
import datetime
import time

COL_ID = 0
COL_TEXT = 1
COL_TIMESTAMP = 2
COL_SUBMITTER_ID = 3
COL_SUBMITTER_USERNAME = 4

BURNISH_FACE_IMG = "https://tohellandbot.s3-eu-west-1.amazonaws.com/static/RichardBurnishface.jpg"
ADJECTIVES = [
    "insightful",
    "wonderful",
    "amazing",
    "lovely",
    "stunning"
]

class QuotesCog(commands.Cog):
    @commands.command(help="Returns a quote from the database", usage="[id]")
    async def quote(self, ctx, id=-1):
        cur = db.get_cursor()

        # specific quote id
        if id != -1:
            cur.execute('SELECT * FROM quotes WHERE id=? LIMIT 1', (id,))
        # random quote
        else:
            cur.execute('SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1')

        row = cur.fetchone()

        if row is None:
            await ctx.send('There is no quote with ID ' + str(id))
        else:
            dt = datetime.datetime.utcfromtimestamp(row[COL_TIMESTAMP] / 1000)
            embed = discord.Embed(title='Quote #' + str(row[COL_ID]), colour=0xFFFFFF, description=row[COL_TEXT], timestamp=dt)
            embed.set_author(name="Richard Burnish", icon_url=BURNISH_FACE_IMG)
            embed.set_footer(text="Submitted by " + row[COL_SUBMITTER_USERNAME])
            await ctx.send(embed=embed)

    @commands.command(help="Submit a quote to the database", usage="<text>")
    async def addquote(self, ctx, *args):
        if len(args) < 1:
            await ctx.send('<@%d> Syntax: `%saddquote <text>`' % (ctx.author.id, config.COMMAND_PREFIX))
            return

        text = ' '.join(args)
        timestamp = int(round(time.time() * 1000))

        cur = db.get_cursor()
        cur.execute('INSERT INTO quotes (text, date, submitter, submitter_name) VALUES (?, ?, ?, ?)', (text, timestamp, ctx.author.id, ctx.author.name))
        db.commit()

        # now find its ID
        cur.execute('SELECT id FROM quotes WHERE text=? AND date=? AND submitter=?', (text, timestamp, ctx.author.id))
        row = cur.fetchone()

        await ctx.send("Thank you, <@%d>! :pray: Your quote has been added as number %d." % (ctx.author.id, row[COL_ID]))

    @commands.command(help="Delete a quote from the database", usage="<id>")
    async def delquote(self, ctx, id):
        cur = db.get_cursor()

        cur.execute('SELECT * FROM quotes WHERE id=?', (id,))
        row = cur.fetchone()

        if row is None:
            await ctx.send('There is no quote with ID ' + str(id))
            return

        # We can delete this
        if ctx.author.id in config.ADMINS or str(ctx.author.id) == row[COL_SUBMITTER_ID]:
            cur.execute('DELETE FROM quotes WHERE id=?', (id,))
            db.commit()
            await ctx.send("Quote %d has been deleted." % (row[COL_ID],))
        # We can't
        else:
            await ctx.send("You don't have permission to delete that quote!")

    @commands.command(help="Edit a quote in the database", usage="<id> <text>")
    async def editquote(self, ctx, id, *args):
        cur = db.get_cursor()

        cur.execute('SELECT * FROM quotes WHERE id=?', (id,))
        row = cur.fetchone()

        if row is None:
            await ctx.send('There is no quote with ID ' + str(id))
            return

        # We can delete this
        if ctx.author.id in config.ADMINS or str(ctx.author.id) == row[COL_SUBMITTER_ID]:
            timestamp = int(round(time.time() * 1000))
            text = ' '.join(args)

            cur.execute('UPDATE quotes SET text=?,date=?', (text, timestamp))
            db.commit()

            await ctx.send('Quote updated.')
        else:
            await ctx.send("You don't have permission to edit that quote!")

    @commands.command(help="Shows statistics about the quote database")
    async def quotestats(self, ctx):

        cur = db.get_cursor()
        cur.execute('SELECT COUNT(id) FROM quotes')
        row = cur.fetchone()

        if not row:
            await ctx.send('Failed to get stats')
            return

        embed = discord.Embed(title="Quote Database Statistics", color=0x1ABC9C)
        embed.add_field(name="Number of quotes", value=row[0])

        await ctx.send(embed=embed)