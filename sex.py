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
    "Maybe take a shower first, AUTHORMENTION?",
    "Maybe ask blachool instead <a:blacube:727669022065295382>",
    "Pfft, you wish.",
    "Even the Veggie Mobile Truck gets fucked more than you, AUTHORMENTION <a:GloriousDay:713767794566627338>"
]

MESSAGES_ADMIN = [
    "fine.",
    "I'd rather not, but whatever.",
    "If you insist.",
    "Ok..."
]

MESSAGES_MULTIPLIER = [
    "Wow! You're SUPER desperate!",
    "GodDAMN you're desperate!",
    "Ultra-Virgin!",
    "You better pay extra for this!",
    "I really do take pity on you..."
]

MESSAGES_SHITTY_MULTIPLIER = [
    "You're pretty desperate, huh?",
    "I mean, if you're *that* desperate...",
    "This is going to cost you, AUTHORMENTION."
]

class SexCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="sex !!")
    async def sex(self, ctx):
        timestamp = int(round(time.time()))

        amount = 1
        if random.randrange(0, 1500) == 0:
            amount = 1000
        elif random.randrange(0, 300) == 0:
            amount = 200
        elif random.randrange(0, 100) == 0:
            amount = 100
        elif random.randrange(0, 20) == 0:
            amount = 10
        elif random.randrange(0, 15) == 0:
            amount = 5
        elif random.randrange(0, 6) == 0:
            amount = 2

        cur = db.get_cursor()
        for i in range(amount):
            db.execute(cur, 'INSERT INTO sex (user, time, channel, server) VALUES (?, ?, ?, ?)',
                       (ctx.author.id, timestamp, ctx.channel.id, ctx.guild.id))
        db.commit()

        db.execute(cur, 'SELECT COUNT(*) FROM sex WHERE user=?', (ctx.author.id,))
        row = cur.fetchone()

        count = row[0]

        if amount >= 10:
            msg = random.choice(MESSAGES_MULTIPLIER)
            msg += " **" + str(amount) + "\u00D7 BOOST**"
        elif amount > 1:
            msg = random.choice(MESSAGES_SHITTY_MULTIPLIER)
            msg += " **" + str(amount) + "\u00D7 boost.**"
        else:
            # Burnish and I, respectively
            if ctx.author.id == 688191761977311259 or ctx.author.id == 195246948847058954:
                msg = "Yes daddy\\~\\~\\~\\~\\~"
            elif ctx.author.id in config.ADMINS:
                msg = random.choice(MESSAGES_ADMIN)
            else:
                msg = random.choice(MESSAGES)

        msg = msg.replace("AUTHORMENTION", ctx.author.mention)

        await ctx.send("%s (%s, you've asked for sex %s times.)" % (msg, ctx.author.name + "#" + str(ctx.author.id), f'{count:,}'))

    @commands.command(help="Lists the most desperate people")
    async def sexleaderboards(self, ctx):
        MAX_USERS = 10

        cur = db.get_cursor()
        db.execute(cur, 'SELECT * FROM sex')
        rows = cur.fetchall()

        countmap = {}

        for row in rows:
            user = int(row["user"])
            if user in countmap:
                countmap[user] += 1
            else:
                countmap[user] = 1

        sort = sorted(countmap, key=countmap.get, reverse=True)

        embed = discord.Embed(title="Most Desperate Leaderboard", color=0xFF7FED)

        topuser = self.bot.get_user(sort[0])
        if not topuser is None:
            embed.set_thumbnail(url=topuser.avatar_url)

        i = 0
        pos = 1
        tmppos = 1
        lastvalue = -9999
        for user in sort:
            value = countmap[user]

            if value < lastvalue:
                pos = i + 1

            discorduser = self.bot.get_user(user)
            username = "Unknown user ID `" + str(user) + "`"
            if not discorduser is None:
                username = discorduser.name + "#" + discorduser.discriminator

            embed.add_field(name=str(pos) + ". " + username, value=f'{value:,}' + " requests for sex", inline=True)

            i += 1
            if i >= MAX_USERS:
                break

            lastvalue = value

        await ctx.send(embed=embed)