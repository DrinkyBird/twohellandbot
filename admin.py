import discord
from discord.ext import commands
import config
import sys
import db
from tabulate import tabulate
import os
import psutil
import gc
from guppy import hpy
import asyncio
import subprocess

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Speaks a thing", usage="<text>", hidden=True)
    async def say(self, ctx, target, *, text=None):
        if ctx.author.id in config.ADMINS:
            if not text:
                await ctx.send('<@%d> Syntax: `%ssay <channel ID> <text>`' % (ctx.author.id, config.COMMAND_PREFIX))
                return

            try:
                channel = self.bot.get_channel(int(target))
                await channel.send(text)
            except Exception as e:
                await ctx.send('An error occured (`' + str(e) + '`) - channel doesn\'t exist, is in invalid format, or isn\'t accessible by the bot')

    @commands.command(help="Kills the bot", hidden=True)
    async def exit(self, ctx):
        if ctx.author.id in config.ADMINS:
            await ctx.reply("A BOT IS DEAD", mention_author=False)
            await asyncio.sleep(1)
            await self.bot.close()
            sys.exit()

    @commands.command(help="Invokes the garbage collector", usage="[generation=2]", hidden=True)
    async def gc(self, ctx, generation=2):
        if ctx.author.id in config.ADMINS:
            process = psutil.Process(os.getpid())
            before = process.memory_info().rss

            gc.collect(generation)

            process = psutil.Process(os.getpid())
            after = process.memory_info().rss

            await ctx.send("Before: {:.3f} MB; After: {:.3f} MB".format(before / 1024 / 1024, after / 1024 / 1024))

    @commands.command(help="Execute an SQLite query", usage="<query>", hidden=True)
    async def sql(self, ctx, *, text=None):
        if ctx.author.id in config.ADMINS:
            if not text:
                await ctx.send('<@%d> Syntax: `%ssql <SQLite query>`' % (ctx.author.id, config.COMMAND_PREFIX))
                return

            cur = db.get_cursor()
            try:
                db.execute(cur, text)
            except Exception as e:
                await ctx.send('Error: ' + str(e))
                return

            affected = cur.rowcount

            rows = cur.fetchall()

            if len(rows) < 1:
                await ctx.send('0 rows returned, '  +str(affected) + ' affected.')
                return

            table = []
            headers = []
            i = 0
            for row in rows:
                d = dict(row)

                trow = []
                for col in d:
                    if  i == 0:
                        headers.append(col)
                    trow.append(d[col])

                table.append(trow)

                i += 1

            tabulated = tabulate(table, headers, tablefmt="presto", numalign="left", stralign="left")
            out = '%d row%s returned, %d affected.\n' % (len(rows), "" if len(rows) == 1 else "s", affected)

            if len(tabulated) < 1800:
                out += '```\n'
                out += tabulated
                out += '```'
                await ctx.send(out)
            else:
                filepath = "sql_" + str(ctx.message.id) + ".txt"
                with open(filepath, 'w') as f:
                    f.write(tabulated)
                    f.flush()

                    await ctx.send(out, file=discord.File(filepath))

                os.remove(filepath)

    @commands.command(hidden=True)
    async def ver(self, ctx):
        s = ''
        s += 'Python: `%s`\n' % (sys.version,)
        s += 'discord.py: `%s`\n' % (discord.__version__,)
        s += 'Commit: `%s`' % (subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode(),)
        s += 'cwd: `%s`\n' % (os.getcwd(),)
        s += 'Dir: `%s`\n' % (os.path.dirname(os.path.realpath(__file__)),)
        s += 'S3 Dir: `%s`\n' % (config.WWWDATA_PATH,)
        s += 'S3 URL: `%s`\n' % (config.WWWDATA_URL,)

        if hasattr(os, 'uname'):
            s += 'uname: `%s`\n' % (str(os.uname()))

        await ctx.send(s)

    @commands.command(hidden=True)
    async def botinfo(self, ctx):
        if not ctx.author.id in config.ADMINS:
            return

        intent_names = []
        for intent in self.bot.intents:
            if intent[1]:
                intent_names.append(f'`{intent[0]}`')

        application = await self.bot.application_info()
        s = '__**Bot Information**__\n'
        s += f'**Application ID:** `{application.id}`\n'
        s += f'**Application Name:** {application.name}\n'
        s += f'**Application Owner:** {application.owner.mention}\n'
        s += f'**Application Icon:** <{application.icon_url}>\n'
        s += f'**Application Public Bot:** {application.bot_public}\n'
        s += f'**Application Bot Requires Code Grant:** {application.bot_require_code_grant}\n'
        s += f'**Intents:** {", ".join(intent_names)}\n'
        s += f'**Latency:** {self.bot.latency}\n'
        s += f'**User ID:** `{self.bot.user.id}`\n'
        s += f'**User Name:** {self.bot.user.name}#{self.bot.user.discriminator}\n'
        s += f'**User Avatar:** <{self.bot.user.avatar_url}>\n'
        s += f'**User Locale:** {self.bot.user.locale}\n'

        await ctx.send(s)

        for guild in self.bot.guilds:
            member = guild.get_member(self.bot.user.id)

            channel_names = []
            for channel in guild.channels:
                myperms = channel.permissions_for(member)
                if channel.type == discord.ChannelType.text and myperms.read_messages:
                    channel_names.append(f'#{channel.name}')

            perm_names = []
            for perm in member.guild_permissions:
                if perm[1]:
                    perm_names.append(f'`{perm[0]}`')

            s = ''
            s += f'__**Guild {guild.id}: `{guild.name}`**__\n'
            s += f'**{len(channel_names)} channels:** {", ".join(channel_names)}\n'
            s += f'**{len(guild.members)} members**\n'
            s += f'**Display Name:** {member.display_name}\n'
            s += f'**Guild permissions:** {", ".join(perm_names)}\n'

            await ctx.send(s)

    @commands.command(hidden=True)
    async def adminlist(self, ctx):
        ls = []
        for id in config.ADMINS:
            ls.append(f"<@!{id}>")

        await ctx.reply(", ".join(ls), allowed_mentions=discord.AllowedMentions.none())

    @commands.command(help="Show heap analysis", hidden=True)
    async def heap(self, ctx):
        if ctx.author.id in config.ADMINS:
            h = hpy()
            val = h.heap()

            print(val)

    @commands.command(help="Set bot nickname", hidden=True)
    async def nickname(self, ctx, *, text=None):
        if ctx.author.id in config.ADMINS:
            member = ctx.message.guild.get_member(self.bot.user.id)
            await member.edit(nick=text)

            try:
                await ctx.message.delete()
            except:
                print("Couldn't delete !nickname message")

    @commands.command(hidden=True)
    async def delmsg(self, ctx, cid, mid):
        if ctx.author.id in config.ADMINS:
            chan = await self.bot.fetch_channel(cid)
            msg = await chan.fetch_message(mid)
            if msg is None:
                ctx.reply('msg is `None`')
            else:
                await msg.delete()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == 770727540691959819:
            target = self.bot.get_channel(688527547113537644)
            if target == None:
                message.channel.send("Failed to send")
                return

            await target.send(message.content)