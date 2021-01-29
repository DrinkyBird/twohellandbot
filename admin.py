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

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Speaks a thing", usage="<text>", hidden=True)
    async def say(self, ctx, target, *, args=None):
        if args is None:
            args = []

        if ctx.author.id in config.ADMINS:
            if len(args) < 1:
                await ctx.send('<@%d> Syntax: `%ssay <channel ID> <text>`' % (ctx.author.id, config.COMMAND_PREFIX))
                return

            text = ' '.join(args)

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
    async def sql(self, ctx, *, args=None):
        if args is None:
            args = []

        if ctx.author.id in config.ADMINS:
            if len(args) < 1:
                await ctx.send('<@%d> Syntax: `%ssql <SQLite query>`' % (ctx.author.id, config.COMMAND_PREFIX))
                return

            text = ' '.join(args)

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
        s += 'Python: `%s`\n' % (sys.version)
        s += 'discord.py: `%s`\n' % (discord.__version__)

        if hasattr(os, 'uname'):
            s += 'uname: `%s`\n' % (str(os.uname()))

        await ctx.send(s)

    @commands.command(help="Show heap analysis", hidden=True)
    async def heap(self, ctx):
        if ctx.author.id in config.ADMINS:
            h = hpy()
            val = h.heap()

            print(val)

    @commands.command(help="Set bot nickname", hidden=True)
    async def nickname(self, ctx, *, args=None):
        if args is None:
            args = []

        if ctx.author.id in config.ADMINS:
            member = ctx.message.guild.get_member(self.bot.user.id)
            await member.edit(nick=' '.join(args))

            try:
                await ctx.message.delete()
            except:
                print("Couldn't delete !nickname message")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == 770727540691959819:
            target = self.bot.get_channel(688527547113537644)
            if target == None:
                message.channel.send("Failed to send")
                return

            await target.send(message.content)