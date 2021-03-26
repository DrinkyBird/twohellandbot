import discord
from discord.ext import commands
import config
import db
import psutil
import os
import time
import math
import util

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

def update_user(user):
    cur = db.get_cursor()

    db.execute(cur, 'SELECT id FROM users WHERE id=?', (user.id,))
    row = cur.fetchone()

    if row is None:
        cur.execute('INSERT INTO users (id, username, discriminator, avatar_url) VALUES (?,?,?,?)',
                    (user.id, user.name, user.discriminator, str(user.avatar_url)))
    else:
        cur.execute('UPDATE users SET id=?, username=?, discriminator=?, avatar_url=? WHERE id=?',
                    (user.id, user.name, user.discriminator, str(user.avatar_url), user.id))

    db.commit()

def record_member_first_join(member):
    if member.guild.id != 688192420013146140:
        return

    cur = db.get_cursor()

    db.execute(cur, 'SELECT COUNT(*) FROM seamen_joins WHERE user=?', (member.id,))
    row = cur.fetchone()

    if row[0] == 0:
        db.execute(cur, "INSERT INTO seamen_joins (user, earliestdate) VALUES (?, ?)",
                   (member.id, member.joined_at.timestamp()))
        print(f"Update join date for {member.name}")

def get_member_first_join(member):
    cur = db.get_cursor()

    db.execute(cur, 'SELECT earliestdate FROM seamen_joins WHERE user=?', (member.id,))
    row = cur.fetchone()

    if row is None:
        record_member_first_join(member)
        return member.joined_at.timestamp()

    return row["earliestdate"]

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows bot statistics")
    async def stats(self, ctx):
        if not util.check_ratelimiting(ctx):
            return
            
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

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        update_user(after)

    @commands.Cog.listener()
    async def on_user_join(self, member):
        record_member_first_join(member)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(688192420013146140)
        if guild is not None:
            for member in guild.members:
                record_member_first_join(member)

def on_command(ctx):
    increment_stat("commands_executed")