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
import stats
import secrets
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
        self.slots_emojis = []
        self.lottery_active = False
        self.lottery_end = 0
        self.lottery_id = None
        self.lottery_pool = 0

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(config.SLOTS_EMOJI_GUILD)
        for key in config.SLOTS_EMOJIS:
            emoji = await guild.fetch_emoji(key)
            self.slots_emojis.append(emoji)

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
            msg_note = "*No note*" if not note else note
            if source_user.id != self.bot.user.id:
                try:
                    await source_user.send(
                        f'You sent {amount:,} VeggieBucks to {dest_user.mention}:\n>>> {msg_note}')
                except:
                    pass
            if dest_user.id != self.bot.user.id:
                try:
                    await dest_user.send(
                        f'You received {amount:,} VeggieBucks from {source_user.mention}:\n>>> {msg_note}')
                except:
                    pass

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

    def member_old_enough(self, member):
        t = stats.get_member_first_join(member)
        if time.time() < t + config.CURRENT_MIN_AGE:
            return False
        return True

    @commands.command(help="View your VeggieBucks balance", aliases=["bal"])
    async def balance(self, ctx):
        await self.create_account(ctx.author.id)

        balance = self.get_user_balance(ctx.author.id)
        bonus = self.get_daily_bonus(ctx.author)
        rank = self.get_user_rank(ctx.author.id, True)
        await ctx.reply(f'Your balance is currently {balance:,} VeggieBucks. Your daily chatting bonus is {bonus:,}. You are currently position {rank} on the leaderboard.')

    @commands.command(hidden=True, aliases=["fbal"])
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
        destuser = ctx.guild.get_member(destid)
        if destuser is None:
            await ctx.reply("That user doesn't exist!")
            return

        if not self.member_old_enough(ctx.author):
            await ctx.reply("You have not been in the server long enough")
            return

        if not self.member_old_enough(destuser):
            await ctx.reply("Destination user has not been in the server long enough")
            return

        intamount = int(amount)
        if intamount < 1:
            await ctx.reply("You must transfer at least 1 VeggieBuck!")
            return

        fees = 0
        if intamount > 1000:
            fees = math.floor((intamount - 1000) * 0.02)
        totalamount = intamount + fees

        if self.lawsuit is not None and (ctx.author.id in self.lawsuit or destuser.id in self.lawsuit):
            await ctx.reply("One party is currently involved in a lawsuit.")
            return

        if not self.user_can_afford(ctx.author.id, totalamount):
            await ctx.reply(f"You can't afford this transaction of {intamount:,} VeggieBucks + {fees:,} in fees. Your current balance is {self.get_user_balance(ctx.author.id):,}.")
            return

        result = await self.transfer_money(ctx.author.id, destuser.id, intamount, note, False)
        await self.transfer_money(ctx.author.id, self.bot.user.id, fees, "Transfer fees", True)
        if result:
            await ctx.reply(f'The transfer was successful. You paid {fees:,} in transfer fees.', allowed_mentions=discord.AllowedMentions.none())
        else:
            balance = self.get_user_balance(ctx.author.id)
            await ctx.reply(f'The transfer failed.')

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

    @commands.command(help="Show the poor people leaderboard", aliases=["poor", "broke"])
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
                id = row["id"]
                amount = row["amount"]
                from_id = int(row["from"])
                to_id = int(row["to"])
                note = row["note"]
                timestamp = row["timestamp"]
                sts = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S %Z')

                fromuser = self.bot.get_user(from_id)
                touser = self.bot.get_user(to_id)

                s += f"**#{id} - {sts} - {amount} VeggieBucks - from {fromuser.mention} to {touser.mention}**\n"
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
    async def sue(self, ctx, defandant_mention=None, amountstr=None):
        if defandant_mention is None or amountstr is None:
            await ctx.reply(f"**Syntax:** `{config.COMMAND_PREFIX}sue <user> <amount>`")
            return

        if not self.member_old_enough(ctx.author):
            await ctx.reply("That user hasn't been here long enough")
            return

        if self.lawsuit is not None:
            await ctx.reply("A lawsuit is currently in progress.")
            return

        if ctx.author.id in self.loss_cooldown:
            if time.time() < self.loss_cooldown[ctx.author.id] + config.LAWSUIT_LOSS_COOLDOWN :
                await ctx.reply(f"You must wait after losing a lawsuit before you can start a new one")
                return

        plaintiff = ctx.author
        defendant_id = util.argument_to_id(defandant_mention)
        defendant = ctx.guild.get_member(defendant_id)
        if defendant is None:
            await ctx.reply('That user doesn\'t exist!')
            return
        if not self.member_old_enough(defendant):
            await ctx.reply("That user hasn't been here long enough")
            return
        amount = int(amountstr)

        defendant_balance = self.get_user_balance(defendant.id)

        MIN_AMOUNT = 200
        if amount < MIN_AMOUNT:
            await ctx.reply(f"You must sue for at least {MIN_AMOUNT:,} VeggieBucks.")
            return

        if plaintiff.id == defendant.id:
            await ctx.reply("You can't sue yourself!")
            return

        if defendant.id == self.bot.user.id:
            await ctx.reply("You can't sue the court!")
            return

        if defendant_balance - amount < -config.LAWSUIT_MAX_DEBT:
            max_amount = abs(-config.LAWSUIT_MAX_DEBT - defendant_balance)
            await ctx.reply(f"The most you can sue this user for is {max_amount:,} VeggieBucks.")
            return

        balance = self.get_user_balance(plaintiff.id)
        if amount > balance:
            await ctx.reply(f"You can't sue for more than your current balance ({balance:,}).")
            return

        self.lawsuit = [plaintiff.id, defendant.id]

        try:
            loadmsg = await ctx.reply("<a:load:823714189901037579> Preparing lawsuit, please wait...",
                                      allowed_mentions=discord.AllowedMentions.none())
            await self.remove_old_emoji()

            plaintiff_emoji = await self.upload_user_emoji(ctx.author)
            defendant_emoji = await self.upload_user_emoji(defendant)

            s = ":warning: **COURT IS NOW IN SESSION!** :warning:\n"
            s += f"{plaintiff.mention} is suing {defendant.mention} for {amount:,} VeggieBucks.\n"
            s += f"React with <:{plaintiff_emoji.name}:{plaintiff_emoji.id}> to side with {plaintiff.mention}. "
            s += f"If {plaintiff.mention} wins the lawsuit, then {defendant.mention} will have to pay {amount:,} VeggieBucks to {plaintiff.mention}.\n"
            s += f"React with <:{defendant_emoji.name}:{defendant_emoji.id}> to side with {defendant.mention}. "
            s += f"If {plaintiff.mention} loses the lawsuit, then {plaintiff.mention} will have to pay {amount:,} VeggieBucks to {defendant.mention}.\n"
            s += f"This lawsuit will last {config.LAWSUIT_DURATION} seconds before a verdict is reached. "
            s += f"If the minimum vote amount ({config.LAWSUIT_MINIMUM_VOTES}) is not reached, the lawsuit will be cancelled."

            await loadmsg.delete()
            msg = await ctx.send(s)

            await msg.add_reaction(plaintiff_emoji)
            await msg.add_reaction(defendant_emoji)

            self.bot.loop.create_task(
                self.lawsuit_callback(ctx, plaintiff, defendant, plaintiff_emoji, defendant_emoji, amount, msg.id))
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

    async def lawsuit_callback(self, ctx, plaintiff, defendant, plaintiff_emoji, defendant_emoji, amount, messageid):
        await asyncio.sleep(config.LAWSUIT_DURATION - 4)

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
            if emoji.id == plaintiff_emoji.id:
                yesvotes += reaction.count - meoff
            elif emoji.id == defendant_emoji.id:
                novotes += reaction.count - meoff

        print(f"plaintiff: {yesvotes} defendant: {novotes}")
        votes = f"<:{plaintiff_emoji.name}:{plaintiff_emoji.id}> {yesvotes} - {novotes} <:{defendant_emoji.name}:{defendant_emoji.id}>"

        await asyncio.sleep(4)
        await message.delete()

        totalvotes = yesvotes + novotes
        if totalvotes < config.LAWSUIT_MINIMUM_VOTES:
            await ctx.send(f":x: The lawsuit was cancelled as the minimum vote amount ({config.LAWSUIT_MINIMUM_VOTES}) was not reached.")
            return

        if yesvotes > novotes:
            # suit won
            to_plaintiff, to_court = self.get_amount_paid(self.get_user_balance(defendant.id), amount)
            await self.transfer_money(defendant.id, plaintiff.id, to_plaintiff, "Lawsuit", True, True)
            await self.transfer_money(defendant.id, self.bot.user.id, to_court, "Lawsuit", True, True)
            if to_court > 0:
                await ctx.send(f"{plaintiff.mention} wins the lawsuit ({votes})! {defendant.mention} is forced to pay them {to_plaintiff:,} VeggieBucks and {to_court:,} VeggieBucks to the court.")
            else:
                await ctx.send(f"{plaintiff.mention} wins the lawsuit ({votes})! {defendant.mention} is forced to pay them {to_plaintiff:,} VeggieBucks.")

            self.loss_cooldown[defendant.id] = time.time()
        else:
            # suit lost
            to_defendant, to_court = self.get_amount_paid(self.get_user_balance(plaintiff.id), amount)
            await self.transfer_money(plaintiff.id, defendant.id, to_defendant, "Lawsuit", True, True)
            await self.transfer_money(plaintiff.id, self.bot.user.id, to_court, "Lawsuit", True, True)
            if to_court > 0:
                await ctx.send(f"{plaintiff.mention} loses the lawsuit ({votes})! They are forced to pay {defendant.mention} {to_defendant:,} VeggieBucks and {to_court:,} VeggieBucks to the court.")
            else:
                await ctx.send(f"{plaintiff.mention} loses the lawsuit ({votes})! They are forced to pay {defendant.mention} {to_defendant:,} VeggieBucks.")
            self.loss_cooldown[plaintiff.id] = time.time()

    def slots_remove_emoji(self, ls, wanted, chance):
        if chance == 0 or random.randrange(0, chance) == 0:
            i = wanted
            while i == wanted:
                i = random.choice(ls)
            print("removed " + str(i))
            ls.remove(i)

    @commands.command()
    async def slots(self, ctx, amountstr=None):
        if amountstr is None:
            await ctx.reply(f"**Syntax:** `{config.COMMAND_PREFIX}slots <amount>`")
            return

        if not self.member_old_enough(ctx.author):
            await ctx.reply("You have not been here long enough")
            return

        if self.lawsuit is not None and ctx.author.id in self.lawsuit:
            await ctx.reply("You're currently involved in a lawsuit! Now is NOT the time to gamble!!")
            return

        balance = self.get_user_balance(ctx.author.id)

        amount = 0
        if amountstr == "all":
            amount = balance
        elif util.is_integer(amountstr):
            amount = int(amountstr)
        else:
            await ctx.reply(f"`{amountstr}` is not a number")
            return

        if amount < 1:
            await ctx.reply("You must use at least 1 VeggieBuck.")
            return

        if not self.user_can_afford(ctx.author.id, amount):
            await ctx.reply(f"You can't afford that much. Your current balance is {balance:,} VeggieBucks.")
            return

        await self.transfer_money(ctx.author.id, self.bot.user.id, amount, "Played slots", True)

        ls = self.slots_emojis.copy()

        a = random.choice(ls)
        print("ls1 " + str(ls))
        self.slots_remove_emoji(ls, a, 1)
        for i in range(random.randint(0, 1)):
            ls.append(a)
        print("ls2 " + str(ls))
        b = random.choice(ls)
        if a.id == b.id:
            self.slots_remove_emoji(ls, a, 2)
            for i in range(random.randint(0, 0)):
                ls.append(a)
        print("ls3 " + str(ls))
        c = random.choice(ls)

        machine = f"<:{a.name}:{a.id}><:{b.name}:{b.id}><:{c.name}:{c.id}>"

        multiplier = 0
        if a.id == b.id and a.id == c.id:
            multiplier = config.SLOTS_EMOJIS[a.id]

        if multiplier > 0:
            reward = math.floor(amount * multiplier)
            await self.transfer_money(self.bot.user.id, ctx.author.id, reward, "Won slots!", True)

            net_win = reward - amount
            await ctx.reply(f"{ctx.author.mention} put {amount:,} VeggieBucks in the slot machine..!\n{machine}\nand **won** {reward:,} in return! (Net win of {net_win:,})")
        else:
            await ctx.reply(f"{ctx.author.mention} put {amount:,} VeggieBucks in the slot machine..!\n{machine}\nand **lost** it all!")

    @commands.command(help="Shows information about the Montclair Lottery")
    async def lottery(self, ctx):
        s = ''
        if self.lottery_active:
            end_seconds = self.lottery_end - int(time.time())
            s += "**A lottery is currently active!** "
            s += f"It will end in {end_seconds:,} seconds. "
            s += f"The current pool is {self.lottery_pool:,} VeggieBucks.\n"
        s += f"You can use `{config.COMMAND_PREFIX}ticket` to buy a single ticket or `{config.COMMAND_PREFIX}ticket <amount>` to buy a certain number of tickets.\n"
        s += f"Each ticket costs {config.CURRENCY_LOTTERY_TICKET_PRICE:,} VeggieBucks.\n"
        s += f"The cost of each ticket is added to the prize pool. When the lottery ends, a ticket is chosen at random and whoever that ticket belongs to will win the entire prize pool!"

        await ctx.reply(s)

    @commands.command(help="Purchase tickets for the Montclair Lottery", syntax="[amount=1]")
    async def ticket(self, ctx, amount=1):
        try:
            amount = int(amount)
        except:
            await ctx.reply("Amount must be a number")
            return

        if amount < 1:
            await ctx.reply("You must buy at least one ticket")
            return

        price = amount * config.CURRENCY_LOTTERY_TICKET_PRICE

        if not self.user_can_afford(ctx.author.id, price):
            await ctx.reply(f"You can't afford {amount:,} tickets (costs {price:,} VeggieBucks)")
            return

        if self.lawsuit is not None and ctx.author.id in self.lawsuit:
            await ctx.reply("You're currently involved in a lawsuit!")
            return

        cchannel = self.bot.get_channel(config.CURRENCY_CHANNEL)
        if not self.lottery_active:
            self.lottery_active = True
            self.lottery_id = secrets.token_hex(8)
            self.lottery_end = int(time.time() + (config.CURRENCY_LOTTERY_DURATION * 60))
            self.lottery_pool = 0
            await cchannel.send(f"The lottery has begun! Tickets will be drawn in {config.CURRENCY_LOTTERY_DURATION} minutes.")
            self.bot.loop.create_task(self.lottery_callback())

        await self.transfer_money(ctx.author.id, self.bot.user.id, price, f"Bought {amount:,} lottery tickets ({self.lottery_id})", True)
        self.lottery_pool += price

        cur = db.get_cursor()
        for i in range(amount):
            cur.execute("INSERT INTO currency_lottery (lottery_id, user, price) VALUES (?, ?, ?)",
                        (self.lottery_id, ctx.author.id, config.CURRENCY_LOTTERY_TICKET_PRICE))

        db.commit()

        await ctx.reply(f"You purchased {amount:,} lottery tickets for {price:,} VeggieBucks.")

    async def cancel_lottery(self, lottery_id):
        cur = db.get_cursor()

        user_values = {}

        cur.execute("SELECT * FROM currency_lottery WHERE lottery_id=?", (self.lottery_id,))
        for row in cur:
            uid = int(row['user'])
            price = row['price']

            if uid in user_values:
                user_values[uid] += price
            else:
                user_values[uid] = price

        for user in user_values:
            value = user_values[user]
            await self.transfer_money(self.bot.user.id, user, value, f"Ticket refund from cancelled lottery ({lottery_id})")
            cur.execute("DELETE FROM currency_lottery WHERE lottery_id=? AND user=?", (lottery_id, user))

        db.commit()

    async def lottery_callback(self):
        await asyncio.sleep(config.CURRENCY_LOTTERY_DURATION * 60)

        cchannel = self.bot.get_channel(config.CURRENCY_CHANNEL)
        cur = db.get_cursor()

        lottery_id = self.lottery_id
        self.lottery_active = False

        user_values = {}
        ticket_uids = []
        total_value = 0

        cur.execute("SELECT * FROM currency_lottery WHERE lottery_id=?", (lottery_id,))
        for row in cur:
            uid = row['user']
            price = row['price']

            total_value += price
            ticket_uids.append(uid)

            if uid in user_values:
                user_values[uid] += price
            else:
                user_values[uid] = price

        if len(user_values) < 2:
            await cchannel.send("Not enough people entered the lottery, tickets have been refunded.")
            await self.cancel_lottery(lottery_id)
            return

        while len(ticket_uids) > 1:
            ticket_uids.pop(random.randrange(len(ticket_uids)))

        winner = int(ticket_uids[0])

        await self.transfer_money(self.bot.user.id, winner, total_value, f"Won lottery ({lottery_id})")
        await cchannel.send(f"And the winner of the Montclair Lottery is <@{winner}>, who gets {total_value:,} VeggieBucks!")

        cur.execute("DELETE FROM currency_lottery WHERE lottery_id=?", (lottery_id,))
        db.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        from_user = guild.get_member(payload.user_id)
        emoji = payload.emoji

        if emoji.id not in EMOJI_VALUES:
            return

        if not self.member_old_enough(from_user):
            return

        msg = await channel.fetch_message(payload.message_id)
        to_user = msg.author

        if from_user.id == to_user.id:
            return

        if self.lawsuit is not None and (from_user.id in self.lawsuit or to_user.id in self.lawsuit):
            return

        await self.transfer_money(from_user.id, to_user.id, EMOJI_VALUES[emoji.id], f"{msg.jump_url}")

    def get_daily_bonus(self, member):
        amt = config.CURRENCY_DAILY_BONUS_DEFAULT

        for role in member.roles:
            for roleid, amount in config.CURRENCY_DAILY_BONUSES:
                if role.id == roleid:
                    amt = max(amt, amount)

        return amt

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
