# Dumb meme module
import discord
from discord.ext import commands
import db
import time
import random
import config

MESSAGES = [
    "Not with you lol fuck off",
    "Sorry, AUTHORMENTION. You don't have sufficient Sex Privileges.",
    "I don't think so.",
    "Maybe take a shower first, AUTHORMENTION?"
]

MESSAGES_ADMIN = [
    "fine.",
    "I'd rather not, but whatever.",
    "If you insist.",
    "Ok..."
]

class SexCog(commands.Cog):
    @commands.command(help="sex !!")
    async def sex(self, ctx):
        timestamp = int(round(time.time()))

        cur = db.get_cursor()
        db.execute(cur, 'INSERT INTO sex (user, time, channel, server) VALUES (?, ?, ?, ?)',
                   (ctx.author.id, timestamp, ctx.channel.id, ctx.guild.id))
        db.commit()

        db.execute(cur, 'SELECT COUNT(*) FROM sex WHERE user=?', (ctx.author.id,))
        row = cur.fetchone()

        count = row[0]

        # Burnish and I, respectively
        if ctx.author.id == 688191761977311259 or ctx.author.id == 195246948847058954:
            msg = "Yes daddy\\~\\~\\~\\~\\~"
        elif ctx.author.id in config.ADMINS:
            msg = random.choice(MESSAGES_ADMIN)
        else:
            msg = random.choice(MESSAGES)

        msg = msg.replace("AUTHORMENTION", ctx.author.mention)

        await ctx.send("%s (You've asked for sex %d times.)" % (msg, count))