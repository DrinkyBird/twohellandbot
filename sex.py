# Dumb meme module
import discord
from discord.ext import commands
import db
import time
import random
import config
import util

EMBED_ICON = "https://tohellandbot.s3-eu-west-1.amazonaws.com/static/SecksPuppet.png"

# 1x
MESSAGES = [
    "Not with you lol fuck off",
    "Sorry, AUTHORMENTION. You don't have sufficient Sex Privileges.",
    "I don't think so.",
    "Maybe take a shower first, AUTHORMENTION?",
    "Maybe ask blachool instead <a:blacube:727669022065295382>",
    "Pfft, you wish.",
    "Even the Veggie Mobile Truck gets fucked more than you, AUTHORMENTION <a:GloriousDay:713767794566627338>",
    "Not until I graduate elementary school",
    "Lol my standards aren't *that* low",
    "I'd rather fuck that harce back there",
    "Not without condoms... or with them",
    "The doctor recommends against it...",
    "What about the bees?"
]

# Admins who aren't me or Richard get these
MESSAGES_ADMIN = [
    "fine.",
    "I'd rather not, but whatever.",
    "If you insist.",
    "Ok...",
    "When I said 'I love you', AUTHORMENTION, I meant *familial* love, not romantic love..."
]

# >= 10x
MESSAGES_MULTIPLIER = [
    "Wow! You're SUPER desperate!",
    "GodDAMN you're desperate!",
    "Ultra-Virgin!",
    "You better pay extra for this!",
    "I really do take pity on you...",
    "Can't you just accept this and go away?",
    "I hope you're not like this in real life...",
    "I can't take much more of this"
]

# < 10x
MESSAGES_SHITTY_MULTIPLIER = [
    "You're pretty desperate, huh?",
    "I mean, if you're *that* desperate...",
    "This is going to cost you, AUTHORMENTION.",
    "You don't deserve more than this, tbh."
]

APPEND_EMOJIS = [
    "",
    "<:patrick:717464136329592912>",
    "<:burnished:412329154718072833>",
    "<:SecksPuppet:770722496013402144>",
    "<:Jebus:739245449323610242>",
    "<:fedora:412330894377091084>"
]

class SexCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def user_has_sex(self, id):
        cur = db.get_cursor()
        db.execute(cur, "SELECT total FROM sex_totals WHERE user = ?", (id,))
        row = cur.fetchone()

        if row is None or row["total"] < 1:
            return False
        return True

    def get_user_rank(self, id, descending):
        if not self.user_has_sex(id):
            return -1

        cur = db.get_cursor()

        cmd = "SELECT COUNT(*) FROM sex_totals WHERE CAST(total AS INTEGER)"
        cmd = cmd + (">" if descending else "<")
        cmd = cmd + "(SELECT CAST(total AS INTEGER) FROM sex_totals WHERE user=?)"
        db.execute(cur, cmd, (id,))
        row = cur.fetchone()

        if row is None:
            return -1

        return row[0] + 1

    def get_total_counts(self):
        cur = db.get_cursor()
        db.execute(cur, "SELECT COUNT(*) FROM sex_totals")
        return cur.fetchone()[0]

    # returns difficulty multiplier for given user
    def get_user_difficulty(self, user):
        rank = self.get_user_rank(user, True)
        if rank == -1:
            return 1

        worst = self.get_worst_rank()

        difficulty = max(0, 1.0 - ((rank - 1) / (worst - 1)))

        return difficulty

    def get_user_sex(self, user):
        cur = db.get_cursor()

        db.execute(cur, 'SELECT total FROM sex_totals WHERE user=?', (user,))
        row = cur.fetchone()

        if row is None:
            return -1

        count = row["total"]
        return count

    def get_worst_rank(self):
        cur = db.get_cursor()
        db.execute(cur, 'SELECT user FROM sex_totals')
        rows = cur.fetchall()

        result = -1
        for row in rows:
            rank = self.get_user_rank(row['user'], True)
            result = max(result, rank)

        return result

    def chance(self, user, n):
        ts = time.time()

        difficulty = self.get_user_difficulty(user)
        n *= 1.0 + difficulty

        val = random.randrange(0, int(n))
        return val == 0

    @commands.command(help="sex !!", aliases=['sexwithseamenator', 'sexwithtohellandbot'])
    async def sex(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        with ctx.typing():
            amount = 1
            if self.chance(ctx.author.id, 60000):
                amount = 5000
            if self.chance(ctx.author.id, 1500):
                amount = 1000
            elif self.chance(ctx.author.id, 300):
                amount = 200
            elif self.chance(ctx.author.id, 100):
                amount = 100
            elif self.chance(ctx.author.id, 20):
                amount = 10
            elif self.chance(ctx.author.id, 15):
                amount = 5
            elif self.chance(ctx.author.id, 6):
                amount = 2

            # Burnish gets more
            if ctx.author.id == 688191761977311259:
                amount = random.choice([1, 500, 2000, 5000])

            cur = db.get_cursor()
            db.commit()

            if self.user_has_sex(ctx.author.id):
                db.execute(cur, 'UPDATE sex_totals SET total=total+? WHERE user=?',
                           (amount, ctx.author.id))
            else:
                amount = 1  # first time is always 1x
                db.execute(cur, 'INSERT INTO sex_totals (user, total) VALUES (?, ?)',
                           (ctx.author.id, amount))
            db.commit()

            count = self.get_user_sex(ctx.author.id)

            # Richard special message
            if ctx.author.id == 688191761977311259:
                msg = "YES DADDY!!!\\~\\~\\~\\~\\~\\~\\~\\~\\~"
                if amount > 1:
                    msg += " **" + str(amount) + "\u00D7 BOOST**"
            elif amount >= 10:
                msg = random.choice(MESSAGES_MULTIPLIER)
                msg += " **" + str(amount) + "\u00D7 BOOST**"
            elif amount > 1:
                msg = random.choice(MESSAGES_SHITTY_MULTIPLIER)
                msg += " **" + str(amount) + "\u00D7 boost.**"
            else:
                # me!
                if ctx.author.id == 195246948847058954:
                    msg = "Yes daddy\\~\\~\\~\\~\\~"
                # Travis special!
                elif ctx.author.id == 190318086132465664:
                    msg = "But I'm not a board <:TravisGf:769302530467037215>"
                elif ctx.author.id in config.ADMINS:
                    msg = random.choice(MESSAGES_ADMIN)
                else:
                    msg = random.choice(MESSAGES)

            msg = msg.replace("AUTHORMENTION", ctx.author.mention)
            sexcount = "(%s, you've asked for sex %s times.)" % (
            ctx.author.name + "#" + str(ctx.author.discriminator), f'{count:,}')
            emoji = random.choice(APPEND_EMOJIS)

            await ctx.reply("%s %s %s" % (msg, sexcount, emoji))

    @commands.command(help="Lists the most desperate people")
    async def sexleaderboards(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        with ctx.typing():
            MAX_USERS = 10

            cur = db.get_cursor()
            db.execute(cur, 'SELECT * FROM sex_totals')
            rows = cur.fetchall()

            countmap = {}
            totalsex = 0

            for row in rows:
                user = int(row["user"])
                countmap[user] = row["total"]
                totalsex += row["total"]

            sort = sorted(countmap, key=countmap.get, reverse=True)

            embed = discord.Embed(title="Most Desperate Leaderboard", color=0xFF7FED)
            embed.set_author(name="Burnish & Co. !sex Services LLC", icon_url=EMBED_ICON,
                             url="http://bot.montclairpublicaccess.info/sex.php")
            embed.set_footer(
                text=f'{totalsex:,} total requests for sex | {self.get_total_counts():,} users have asked for sex')

            topuser = self.bot.get_user(sort[0])
            if not topuser is None:
                embed.set_thumbnail(url=topuser.avatar_url)

            i = 0
            for user in sort:
                value = countmap[user]
                pos = self.get_user_rank(user, True)

                discorduser = self.bot.get_user(user)
                username = "Unknown user ID `" + str(user) + "`"
                if not discorduser is None:
                    username = discorduser.name + "#" + discorduser.discriminator

                embed.add_field(name=str(pos) + ". " + username, value=f'{value:,}' + " requests for sex", inline=True)

                i += 1
                if i >= MAX_USERS:
                    break

            msg = "%s, you are currently position %d on the leaderboard." \
                  % (ctx.author.name + "#" + str(ctx.author.discriminator), self.get_user_rank(ctx.author.id, True))

            await ctx.send(msg, embed=embed)

    @commands.command(hidden=True)
    async def sexinfo(self, ctx, user=None):
        if not util.check_ratelimiting(ctx):
            return

        if user is None:
            user = ctx.author.id
            discorduser = ctx.author
        else:
            discorduser = self.bot.get_user(int(user))
            if discorduser is None:
                await ctx.send("No such user with ID " + str(user))
                return

        has = self.user_has_sex(user)
        total = self.get_user_sex(user)
        rank = self.get_user_rank(user, True)
        irank = self.get_user_rank(user, False)
        difficulty = self.get_user_difficulty(user)

        embed = discord.Embed(title="!sex info for " + discorduser.name + "#" + str(discorduser.discriminator))
        embed.add_field(name="hasSex", value=str(has), inline=True)
        embed.add_field(name="totalSex", value=str(total), inline=True)
        embed.add_field(name="rank", value=str(rank), inline=True)
        embed.add_field(name="irank", value=str(irank), inline=True)
        embed.add_field(name="difficulty", value=str(difficulty), inline=True)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def sexwithsean(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        if ctx.author.id == 195246948847058954:
            await ctx.reply("No selfcest allowed")
        else:
            await ctx.reply("If you're really desperate for sex, pester <@264844361341075467> about the spam channel. Also, this attempt has been reported to the police.")

    @commands.command(hidden=True)
    async def sexwithtravis(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        if ctx.author.id == 190318086132465664:
            await ctx.reply("No selfcest allowed")
        else:
            await ctx.reply("Sorry, Travis <:TalksToBoards:769303261667917864> only has sex with (male) boards <:TravisGf:769302530467037215>.")

    @commands.command(hidden=True, aliases=['sexwithking'])
    async def sexwithsiggus(self, ctx):
        if not util.check_ratelimiting(ctx):
            return

        await ctx.reply("Sex with Siggus cannot be requested, it just happens <:siggus:758007416553209976>")