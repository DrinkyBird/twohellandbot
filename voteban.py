import discord
from discord.ext import commands
import config
import asyncio
import util
import db
import time
import math
import datetime

class VoteBanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_votes = []

        self.bot.loop.create_task(self.check_unban_loop())

    def is_member_banned(self, member):
        cur = db.get_cursor()
        db.execute(cur, 'SELECT COUNT(*) FROM bans WHERE user = ? AND guild = ?', (str(member.id), str(member.guild.id)))
        num = cur.fetchone()[0]

        return num > 0

    async def check_unban_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.check_unban()
            await asyncio.sleep(config.VOTEBAN_CHECK_UNBAN_PERIOD)

    async def check_unban(self):
        cur = db.get_cursor()
        db.execute(cur, 'SELECT user, guild, time FROM bans')

        rows = cur.fetchall()

        for row in rows:
            userid = int(row[0])
            guildid = int(row[1])
            bannedtime = row[2]

            if time.time() >= bannedtime + config.VOTEBAN_BAN_DURATION:
                print(f'Remove banned user {userid} in guild {guildid}')
                db.execute(cur, 'DELETE FROM bans WHERE user = ? AND guild = ?', (str(userid), str(guildid)))
                db.commit()

    async def vote_callback(self, ctx, victimid, channelid, msgid):
        await asyncio.sleep(config.VOTEBAN_VOTE_DURATION)
        self.active_votes.remove(victimid)

        channel = self.bot.get_channel(channelid)
        guild = channel.guild
        msg = await channel.fetch_message(msgid)
        victim = guild.get_member(victimid)

        await msg.delete()

        print(msg.reactions)

        yesvotes = 0
        novotes = 0

        for reaction in msg.reactions:
            meoff = 0
            if reaction.me:
                meoff = 1

            emoji = reaction.emoji
            if emoji.id == config.VOTEBAN_YES_EMOJI:
                yesvotes += reaction.count - meoff
            elif emoji.id == config.VOTEBAN_NO_EMOJI:
                novotes += reaction.count - meoff

        if yesvotes > novotes:
            cur = db.get_cursor()
            db.execute(cur, 'INSERT INTO bans (user, guild, time) VALUES (?,?,?)', (victim.id, guild.id, time.time()))
            db.commit()

            await ctx.send(f'**VOTE PASSED!** ({yesvotes}-{novotes}) {victim.mention} has been banned for {math.floor(config.VOTEBAN_BAN_DURATION / 60)} minutes.')
        else:
            await ctx.send(f'**VOTE FAILED!** ({yesvotes}-{novotes}) {victim.mention} is spared... for now.')

    @commands.command(help="Starts a vote to ban a user")
    async def voteban(self, ctx, user=None, *, reason=None):
        if not user:
            await ctx.reply("**Syntax:** `%svoteban <user> [reason]`" % (config.COMMAND_PREFIX,))
            return

        userid = util.argument_to_id(user)
        if userid is None:
            await ctx.reply('Invalid user format. Try mentioning them.')
            return

        user = self.bot.get_user(userid)
        if user is None:
            await ctx.reply('Could not find a user with ID ' + str(userid))
            return

        if user.id == self.bot.user.id:
            await ctx.reply('No.')
            return

        member = ctx.guild.get_member(user.id)
        if member is None:
            await ctx.reply('That user is not in this server')
            return

        if member not in ctx.channel.members:
            await ctx.reply('That user is not in this channel.')
            return

        if member.bot:
            await ctx.reply('That user is a bot!')
            return

        if self.is_member_banned(member):
            await ctx.reply('That user is already banned!')
            return

        if member.id in self.active_votes:
            await ctx.reply('A vote is already underway for this user')
            return

        yesemoji = self.bot.get_emoji(config.VOTEBAN_YES_EMOJI)
        noemoji = self.bot.get_emoji(config.VOTEBAN_NO_EMOJI)

        if not reason:
            reason = "*No reason given*"

        embed = discord.Embed(title="VOTE NOW!", colour=discord.Colour.red())
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Victim", value=user.mention, inline=True)
        embed.add_field(name="Action", value="Ban", inline=True)
        embed.add_field(name="Vote Duration", value=f"{config.VOTEBAN_VOTE_DURATION} seconds", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="To vote yes:", value=f"react with <:{yesemoji.name}:{yesemoji.id}>", inline=True)
        embed.add_field(name="To vote no:", value=f"react with <:{noemoji.name}:{noemoji.id}>", inline=True)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction(yesemoji)
        await msg.add_reaction(noemoji)

        self.active_votes.append(user.id)
        self.bot.loop.create_task(self.vote_callback(ctx, user.id, msg.channel.id, msg.id))

    @commands.command(help="Shows all banned users", aliases=["bans", "wallofshame"])
    async def banlist(self, ctx):
        cur = db.get_cursor()
        db.execute(cur, 'SELECT user, time FROM bans WHERE guild = ?', (str(ctx.guild.id),))
        rows = cur.fetchall()

        if len(rows) < 1:
            await ctx.reply('Nobody is banned... right now.')
        else:
            s = '__**Wall of Shame**__\n'

            for row in rows:
                userid = int(row[0])
                user = self.bot.get_user(userid)
                bantime = row[1]
                unbantime = bantime + config.VOTEBAN_BAN_DURATION

                username = f'Unknown user {userid}'
                if user is not None:
                    username = f'{user.name}#{user.discriminator}'

                formattedtime = datetime.datetime.utcfromtimestamp(unbantime).strftime('%Y-%m-%d %H:%M:%S %Z')
                s += f'{username} until {formattedtime}\n'

            await ctx.reply(s)
