import discord
from discord.ext import commands
import util
import random
import db
import config
import time
import math
import datetime
import re
import requests
import io
import asyncio
from PIL import Image

EMOJI_VALUES = {
    817927111884144670: 1,
    823664582316261446: 5,
    823664581884248145: 50,
    823664582412861481: 20,
    823664581309104148: 10,
    823664581373067274: 100
}

# DELETE FROM currency_balances; DELETE FROM currency_ledger; DELETE FROM currency_daily;

class CurrencyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lawsuit = None
        self.loss_cooldown = {}

    async def create_account(self, uid):
        if not self.user_signed_up(uid):
            # ensure this user actually exists
            user = self.bot.get_user(uid)
            if user is None:
                return

            cur = db.get_cursor()

            db.execute(cur, "INSERT INTO currency_balances (user, balance) VALUES (?, ?)", (uid, 0))
            db.commit()

            await self.transfer_money(self.bot.user.id, uid, config.CURRENCY_SIGNUP_BONUS, "Bank of Montclair sign-up bonus", True)

    def user_signed_up(self, uid):
        cur = db.get_cursor()
        db.execute(cur, "SELECT COUNT(*) FROM `currency_balances` WHERE user = ?", (str(uid),))
        num = cur.fetchone()[0]

        return num == 1

    def get_user_balance(self, uid):
        if not self.user_signed_up(uid):
            return None

        cur = db.get_cursor()
        db.execute(cur, "SELECT `balance` FROM `currency_balances` WHERE user = ?", (str(uid),))

        return cur.fetchone()[0]

    def user_can_afford(self, uid, amount):
        if uid == self.bot.user.id:
            return True

        return self.get_user_balance(uid) >= amount

    async def transfer_money(self, from_uid, to_uid, amount, note="", silent=False, ignore_can_afford=False):
        if from_uid == to_uid:
            print(f'Transfer {from_uid} -> {to_uid} failed as same user')
            return False

        if amount == 0:
            return False

        source_user = self.bot.get_user(from_uid)
        dest_user = self.bot.get_user(to_uid)
        if source_user is None or dest_user is None:
            print(f'Transfer {from_uid} ({source_user}) -> {to_uid} ({to_uid}) failed as one of them was None')
            return False

        await self.create_account(from_uid)
        await self.create_account(to_uid)

        if not ignore_can_afford and not self.user_can_afford(from_uid, amount):
            if not silent:
                balance = self.get_user_balance(from_uid)
                await source_user.send(f'You do not have sufficient VeggieBucks to do this. Your current balance is: {balance:,}')
            print(f'Transfer {from_uid} ({source_user}) -> {to_uid} ({to_uid}) failed as source has insufficient balance')
            return False

        cur = db.get_cursor()
        db.execute(cur, "INSERT INTO currency_ledger (`from`, `to`, `amount`, `timestamp`, `note`) VALUES (?, ?, ?, ?, ?)",
                   (from_uid, to_uid, amount, time.time(), note))
        db.execute(cur, "UPDATE currency_balances SET `balance` = `balance` - ? WHERE `user` = ?",
                   (amount, from_uid))
        db.execute(cur, "UPDATE currency_balances SET `balance` = `balance` + ? WHERE `user` = ?",
                   (amount, to_uid))

        db.commit()

        if not silent:
            await source_user.send(f'Transferred {amount:,} VeggieBucks to {dest_user.mention} with note:\n>>> {note}')

        return True

    def get_user_rank(self, id, descending):
        if not self.user_signed_up(id):
            return -1

        cur = db.get_cursor()

        cmd = "SELECT COUNT(*) FROM currency_balances WHERE CAST(balance AS INTEGER)"
        cmd = cmd + (">" if descending else "<")
        cmd = cmd + "(SELECT CAST(balance AS INTEGER) FROM currency_balances WHERE user=?)"
        db.execute(cur, cmd, (id,))
        row = cur.fetchone()

        if row is None:
            return -1

        return row[0] + 1

    @commands.command(help="View your VeggieBucks balance")
    async def balance(self, ctx):
        await self.create_account(ctx.author.id)

        balance = self.get_user_balance(ctx.author.id)
        bonus = self.get_daily_bonus(ctx.author)
        rank = self.get_user_rank(ctx.author.id, True)
        await ctx.reply(f'Your balance is currently {balance:,} VeggieBucks. Your daily chatting bonus is {bonus:,}. You are currently position {rank} on the leaderboard.')

    @commands.command(hidden=True)
    async def fbalance(self, ctx, user):
        if ctx.author.id not in config.ADMINS:
            return

        targetid = util.argument_to_id(user)
        targetuser = ctx.guild.get_member(targetid)
        if targetuser is None:
            await ctx.reply('No such user')
            return

        await self.create_account(targetid)

        balance = self.get_user_balance(targetid)
        bonus = self.get_daily_bonus(targetuser)
        fullname = f'{targetuser.name}#{targetuser.discriminator}'
        await ctx.reply(f'{fullname}\'s balance is currently {balance:,} VeggieBucks. Their daily chatting bonus is {bonus:,}.')

    @commands.command(help="Send money to someone")
    async def transfer(self, ctx, destination, amount, *, note=""):
        destid = util.argument_to_id(destination)
        destuser = self.bot.get_user(destid)
        if destuser is None:
            await ctx.reply("That user doesn't exist!")
            return

        intamount = int(amount)
        if intamount < 1:
            await ctx.reply("You must transfer at least 1 VeggieBuck!")
            return

        if self.lawsuit is not None and (ctx.author.id in self.lawsuit or destuser.id in self.lawsuit):
            await ctx.reply("One party is currently involved in a lawsuit.")
            return

        result = await self.transfer_money(ctx.author.id, destuser.id, intamount, note, True)
        if result:
            await ctx.reply('The transfer was successful!')
        else:
            balance = self.get_user_balance(ctx.author.id)
            await ctx.reply(f'The transfer failed. Make sure you have enough VeggieBucks (your current balance is {balance:,})')

    @commands.command(hidden=True)
    async def ftransfer(self, ctx, source, destination, amount, *, note=""):
        if ctx.author.id not in config.ADMINS:
            return

        srcid = util.argument_to_id(source)
        srcuser = self.bot.get_user(srcid)
        if srcuser is None:
            await ctx.reply("Source user doesn't exist!")
            return

        destid = util.argument_to_id(destination)
        destuser = self.bot.get_user(destid)
        if destuser is None:
            await ctx.reply("Dest user doesn't exist!")
            return

        intamount = int(amount)
        if intamount < 1:
            await ctx.reply("You must transfer at least 1 VeggieBuck!")
            return

        result = await self.transfer_money(srcid, destuser.id, intamount, note, True, True)
        if result:
            await ctx.reply('The transfer was successful!')
        else:
            balance = self.get_user_balance(srcid)
            await ctx.reply(f'The transfer failed. Make sure the source has enough VeggieBucks (current balance is {balance:,})')

    @commands.command(help="Show the VeggieBuck leaderboard", aliases=["leaderboard"])
    async def leaderboards(self, ctx):
        await self.do_leaderboard(ctx, True)

    @commands.command(help="Show the poor people leaderboard", aliases=["poor"])
    async def poverty(self, ctx):
        await self.do_leaderboard(ctx, False)

    async def do_leaderboard(self, ctx, reverse):
        MAX_USERS = 10

        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM currency_balances")
        rows = cur.fetchall()

        countmap = {}
        total = 0

        for row in rows:
            user = int(row["user"])
            countmap[user] = row["balance"]

            if row["balance"] >= 0:
                total += row["balance"]

        sort = sorted(countmap, key=countmap.get, reverse=reverse)

        embed = discord.Embed(name="VeggieBuck Leaderboards", color=discord.Colour.green())
        embed.set_author(name="Montclair Community Bank")
        embed.set_footer(text=f'{total:,} VeggieBucks exist')

        topuser = self.bot.get_user(sort[0])
        if topuser is not None:
            embed.set_thumbnail(url=topuser.avatar_url)

        i = 0
        for user in sort:
            value = countmap[user]
            pos = self.get_user_rank(user, True)

            discorduser = self.bot.get_user(user)
            username = f"Unknown user {user}"
            if discorduser is not None:
                username = f"{discorduser.name}#{discorduser.discriminator}"

            embed.add_field(name=f"{pos}. {username}", value=f"{value:,}", inline=True)

            i += 1
            if i >= MAX_USERS:
                break

        msg = f"You are currently position {self.get_user_rank(ctx.author.id, True)} on the leaderboard."

        await ctx.send(msg, embed=embed)

    @commands.command(help="View your bank statement")
    async def statement(self, ctx):
        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM `currency_ledger` WHERE `from`=? OR `to`=? ORDER BY timestamp DESC",
                   (ctx.author.id, ctx.author.id))
        rows = cur.fetchall()

        if len(rows) < 1:
            await ctx.reply("Your bank statement is empty.")
        else:
            s = 'Here are your most recent transactions:\n'

            i = 0
            linkregex = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")
            for row in rows:
                amount = row["amount"]
                from_id = int(row["from"])
                to_id = int(row["to"])
                note = row["note"]
                timestamp = row["timestamp"]
                sts = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S %Z')

                fromuser = self.bot.get_user(from_id)
                touser = self.bot.get_user(to_id)

                s += f"**{sts} - {amount} VeggieBucks - from {fromuser.mention} to {touser.mention}**\n"
                if not note:
                    s += "*No note*\n"
                else:
                    s += "> " + linkregex.sub(r"<\1>", note) + "\n"

                i += 1
                if i >= 10:
                    break

            try:
                await ctx.author.send(s, allowed_mentions=discord.AllowedMentions.none())
            except:
                await ctx.reply("I couldn't send you your statement, ensure that I can DM you")


    async def upload_user_emoji(self, user):
        r = requests.get(user.avatar_url_as(format='png', static_format='png', size=64))
        im = Image.open(io.BytesIO(r.content))
        im.thumbnail((48, 48))

        bytearr = io.BytesIO()
        im.save(bytearr, format='PNG')

        guild = self.bot.get_guild(config.LAWSUIT_EMOJI_SERVER)
        emoji = await guild.create_custom_emoji(name=f'avatar_{user.id}', image=bytearr.getvalue())

        cur = db.get_cursor()
        db.execute(cur, "INSERT INTO `old_emoji` (`guild`, `id`) VALUES (?, ?)", (guild.id, emoji.id))
        db.commit()

        return emoji

    async def remove_old_emoji(self):
        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM `old_emoji`")

        for row in cur.fetchall():
            guild = self.bot.get_guild(int(row["guild"]))
            emoji = await guild.fetch_emoji(int(row["id"]))
            await emoji.delete()

        db.execute(cur, "DELETE FROM `old_emoji`")
        db.commit()

    @commands.command(help="Sue someone")
    async def sue(self, ctx, target=None, amountstr=None):
        if target is None or amountstr is None:
            await ctx.reply(f"**Syntax:** `{config.COMMAND_PREFIX}sue <user> <amount>`")
            return

        if self.lawsuit is not None:
            await ctx.reply("A lawsuit is currently in progress.")
            return

        if ctx.author.id in self.loss_cooldown:
            if time.time() > self.loss_cooldown[ctx.author.id] + config.LAWSUIT_LOSS_COOLDOWN :
                await ctx.reply(f"You must wait after losing a lawsuit before you can start a new one")
                return

        srcuser = ctx.author
        targetid = util.argument_to_id(target)
        targetuser = self.bot.get_user(targetid)
        if targetuser is None:
            await ctx.reply('That user doesn\'t exist!')
            return
        amount = int(amountstr)

        MIN_AMOUNT = 200
        if amount < MIN_AMOUNT:
            await ctx.reply(f"You must sue for at least {MIN_AMOUNT:,} VeggieBucks.")
            return

        if srcuser.id == targetuser.id:
            await ctx.reply("You can't sue yourself!")
            return

        if targetuser.id == self.bot.user.id:
            await ctx.reply("You can't sue the court!")
            return

        balance = self.get_user_balance(srcuser.id)
        if amount > balance:
            await ctx.reply(f"You can't sue for more than your current balance ({balance:,}.")
            return

        self.lawsuit = [srcuser.id, targetuser.id]

        try:
            loadmsg = await ctx.reply("<a:load:823714189901037579> Preparing lawsuit, please wait...",
                                      allowed_mentions=discord.AllowedMentions.none())
            await self.remove_old_emoji()

            sourceemoji = await self.upload_user_emoji(ctx.author)
            destemoji = await self.upload_user_emoji(targetuser)

            s = ":warning: **COURT IS NOW IN SESSION!** :warning:\n"
            s += f"{srcuser.mention} is suing {targetuser.mention} for {amount:,} VeggieBucks.\n"
            s += f"React with <:{sourceemoji.name}:{sourceemoji.id}> to side with {srcuser.mention}. "
            s += f"If {srcuser.mention} wins the lawsuit, then {targetuser.mention} will have to pay {amount:,} VeggieBucks to {srcuser.mention}.\n"
            s += f"React with <:{destemoji.name}:{destemoji.id}> to side with {targetuser.mention}. "
            s += f"If {srcuser.mention} loses the lawsuit, then {srcuser.mention} will have to pay {amount:,} VeggieBucks to {targetuser.mention}.\n"
            s += f"This lawsuit will last {config.LAWSUIT_DURATION} seconds before a verdict is reached. "
            s += f"If the minimum vote amount ({config.LAWSUIT_MINIMUM_VOTES}) is not reached, the lawsuit will be cancelled."

            await loadmsg.delete()
            msg = await ctx.send(s)

            await msg.add_reaction(sourceemoji)
            await msg.add_reaction(destemoji)

            self.bot.loop.create_task(
                self.lawsuit_callback(ctx, srcuser, targetuser, sourceemoji, destemoji, amount, msg.id))
        except Exception as ex:
            self.lawsuit = None
            await ctx.reply("An error occured while trying to start the lawsuit: `" + str(ex) + "`")

    def get_amount_paid(self, balance, amount):
        if balance < 0:
            balance = 0

        if amount > balance:
            return balance, amount - balance
        else:
            return amount, 0

    async def lawsuit_callback(self, ctx, srcuser, targetuser, sourceemoji, destemoji, amount, messageid):
        #source is yes
        #target/dest is no
        await asyncio.sleep(config.LAWSUIT_DURATION)

        try:
            message = await ctx.channel.fetch_message(messageid)
        except:
            await ctx.send("The fucking message disappeared???")
            self.lawsuit = None
            return

        self.lawsuit = None

        yesvotes = 0
        novotes = 0

        for reaction in message.reactions:
            meoff = 0
            if reaction.me:
                meoff = 1
            if not reaction.custom_emoji:
                continue

            emoji = reaction.emoji
            if emoji.id == sourceemoji.id:
                yesvotes += reaction.count - meoff
            elif emoji.id == destemoji.id:
                novotes += reaction.count - meoff

        print(f"plaintiff: {yesvotes} defendant: {novotes}")
        votes = f"<:{sourceemoji.name}:{sourceemoji.id}> {yesvotes} - {novotes} <:{destemoji.name}:{destemoji.id}>"

        await message.delete()

        totalvotes = yesvotes + novotes
        if totalvotes < config.LAWSUIT_MINIMUM_VOTES:
            await ctx.send(f":x: The lawsuit was cancelled as the minimum vote amount ({config.LAWSUIT_MINIMUM_VOTES}) was not reached.")
            return

        if yesvotes > novotes:
            # suit won
            to_plaintiff, to_court = self.get_amount_paid(self.get_user_balance(targetuser.id), amount)
            await self.transfer_money(targetuser.id, srcuser.id, to_plaintiff, "Lawsuit", True, True)
            await self.transfer_money(targetuser.id, self.bot.user.id, to_court, "Lawsuit", True, True)
            if to_court > 0:
                await ctx.send(f"{srcuser.mention} wins the lawsuit ({votes})! {targetuser.mention} is forced to pay them {to_plaintiff:,} VeggieBucks and {to_court:,} VeggieBucks to the court.")
            else:
                await ctx.send(f"{srcuser.mention} wins the lawsuit ({votes})! {targetuser.mention} is forced to pay them {to_plaintiff:,} VeggieBucks.")

            self.loss_cooldown[targetuser.id] = time.time()
        else:
            # suit lost
            to_defendant, to_court = self.get_amount_paid(self.get_user_balance(srcuser.id), amount)
            await self.transfer_money(srcuser.id, targetuser.id, to_defendant, "Lawsuit", True, True)
            await self.transfer_money(srcuser.id, self.bot.user.id, to_court, "Lawsuit", True, True)
            if to_court > 0:
                await ctx.send(f"{srcuser.mention} loses the lawsuit ({votes})! They are forced to pay {targetuser.mention} {to_defendant:,} VeggieBucks and {to_court:,} VeggieBucks to the court.")
            else:
                await ctx.send(f"{srcuser.mention} loses the lawsuit ({votes})! They are forced to pay {targetuser.mention} {to_defendant:,} VeggieBucks.")
            self.loss_cooldown[srcuser.id] = time.time()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        from_user = self.bot.get_user(payload.user_id)
        emoji = payload.emoji

        if emoji.id not in EMOJI_VALUES:
            return

        msg = await channel.fetch_message(payload.message_id)
        to_user = msg.author

        if from_user.id == to_user.id:
            return

        if self.lawsuit is not None and (from_user.id in self.lawsuit or to_user.id in self.lawsuit):
            return

        await self.transfer_money(from_user.id, to_user.id, EMOJI_VALUES[emoji.id], f"{msg.jump_url}")

    def get_daily_bonus(self, member):
        for role in member.roles:
            for roleid, amount in config.CURRENCY_DAILY_BONUSES:
                if role.id == roleid:
                    return amount

        return config.CURRENCY_DAILY_BONUS_DEFAULT

    @commands.Cog.listener()
    async def on_message(self, message):
        dest = message.author

        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM `currency_daily` WHERE user = ?", (str(dest.id),))
        row = cur.fetchone()

        if row is None:
            print(f'Giving first daily chat bonus to {dest.id}')
            await self.transfer_money(self.bot.user.id, dest.id, self.get_daily_bonus(message.author), "Daily chatting bonus (initial)", True)
            db.execute(cur, "INSERT INTO `currency_daily` (user, last_claimed) VALUES (?, ?)",
                       (str(dest.id), time.time()))
            db.commit()
        else:
            now = time.time()
            lastmod = math.floor(math.floor(row[1]) / 86400)
            nowmod = math.floor(math.floor(now) / 86400)

            if nowmod > lastmod:
                print(f'Giving daily chat bonus to {dest.id} as {nowmod} > {lastmod}')
                await self.transfer_money(self.bot.user.id, dest.id, self.get_daily_bonus(message.author),
                                          "Daily chatting bonus", True)
                db.execute(cur, "UPDATE `currency_daily` SET `last_claimed`=? WHERE `user`=?",
                           (now, str(dest.id)))
                db.commit()
