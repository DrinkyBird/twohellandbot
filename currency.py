import discord
from discord.ext import commands
import util
import random
import db
import config
import time
import math

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

    async def transfer_money(self, from_uid, to_uid, amount, note="", silent=False):
        if from_uid == to_uid:
            print(f'Transfer {from_uid} -> {to_uid} failed as same user')
            return False

        source_user = self.bot.get_user(from_uid)
        dest_user = self.bot.get_user(to_uid)
        if source_user is None or dest_user is None:
            print(f'Transfer {from_uid} ({source_user}) -> {to_uid} ({to_uid}) failed as one of them was None')
            return False

        await self.create_account(from_uid)
        await self.create_account(to_uid)

        if not self.user_can_afford(from_uid, amount):
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

    @commands.command()
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

        result = await self.transfer_money(srcid, destuser.id, intamount, note, True)
        if result:
            await ctx.reply('The transfer was successful!')
        else:
            balance = self.get_user_balance(srcid)
            await ctx.reply(f'The transfer failed. Make sure the source has enough VeggieBucks (current balance is {balance:,})')

    @commands.command(help="Show the VeggieBuck leaderboard", aliases=["leaderboard"])
    async def leaderboards(self, ctx):
        MAX_USERS = 10

        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM currency_balances")
        rows = cur.fetchall()

        countmap = {}
        total = 0

        for row in rows:
            user = int(row["user"])
            countmap[user] = row["balance"]

            if user != self.bot.user.id:
                total += row["balance"]

        sort = sorted(countmap, key=countmap.get, reverse=True)

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
