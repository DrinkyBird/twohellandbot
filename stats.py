import discord
from discord.ext import commands
import config
import db
import psutil
import os
import time
import math

start_time = time.time()

def increment_stat(name):
    cur = db.get_cursor()

    cur.execute('UPDATE stats SET %s=%s+1' % (name, name))

    db.commit()

def to_hhmmss(num_seconds):
    hours   = math.floor(num_seconds / 3600)
    minutes = math.floor((num_seconds - (hours * 3600)) / 60)
    seconds = math.floor(num_seconds - (hours * 3600) - (minutes * 60))

    time = str(hours) + 'h ' + str(minutes) + 'm ' + str(seconds) + 's'

    return time

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows bot statistics")
    async def stats(self, ctx):
        process = psutil.Process(os.getpid())
        uptime = time.time() - start_time

        cur = db.get_cursor()
        db.execute(cur, 'SELECT * FROM stats')

        row = cur.fetchone()
        result = dict(row)

        result['memory_usage'] = "{:.3f} MB".format(process.memory_info().rss / 1024 / 1024)
        result['database_size'] = "{:.3f} MB".format(os.path.getsize(config.DB_PATH) / 1024 / 1024)
        result['uptime'] = to_hhmmss(uptime)

        embed = discord.Embed(title='Bot Statistics', colour=0x3498DB)
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        for col in result:
            val = result[col]
            valstr = str(result[col])
            if isinstance(val, int):
                valstr = f'{val:,}'

            embed.add_field(name=str(col), value=valstr, inline=True)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't count our own messages
        if message.author.id == self.bot.user.id:
            return

        increment_stat("messages_received")

def on_command(ctx):
    increment_stat("commands_executed")