import socketio
import discord
from discord.ext import commands
import time
import asyncio

THAB_API_URL = 'https://tohellandback.herokuapp.com'
DOORS_IMAGE_URL = 'https://tohellandbot.s3-eu-west-1.amazonaws.com/static/doors.png'

sio = socketio.AsyncClient()
healths = ['','','']
is_connected = False

@sio.event
async def connect():
    global is_connected

    is_connected = True
    print("Connected to " + THAB_API_URL)

@sio.event
async def connect_error(err):
    global is_connected

    is_connected = False
    print("Failed connection to " + THAB_API_URL)

    await asyncio.sleep(15)
    await sio.connect(THAB_API_URL)

@sio.event
async def disconnect():
    global is_connected

    is_connected = False
    print("Disconnected from " + THAB_API_URL)

    await asyncio.sleep(15)
    await sio.connect(THAB_API_URL)

@sio.on('system1health')
async def on_system1health(data):
    healths[0] = data

@sio.on('system2health')
async def on_system1health(data):
    healths[1] = data

@sio.on('system3health')
async def on_system1health(data):
    healths[2] = data

class SystemsCog(commands.Cog):
    def __init__(self):
        self.timeouts = {}

        asyncio.get_event_loop().run_until_complete(sio.connect(THAB_API_URL))

    def cog_unload(self):
        asyncio.get_event_loop().run_until_complete(sio.disconnect())

    @commands.command(help="Shows the current system status", usage="")
    async def systems(self, ctx):
        global is_connected

        if not is_connected:
            await ctx.send("Not connected to API server <" + THAB_API_URL + ">")
            return

        for st in healths:
            if st == '':
                await ctx.send("Couldn't get system information")
                return

        embed = discord.Embed(title="System Status", url=THAB_API_URL, color=0xFF0000)
        embed.set_thumbnail(url=DOORS_IMAGE_URL)
        embed.add_field(name="System 1 (Alarms)", value=healths[0], inline=False)
        embed.add_field(name="System 2 (Locks)", value=healths[1], inline=False)
        embed.add_field(name="System 3 (Doors)", value=healths[2], inline=False)

        await ctx.send(embed=embed)

    @commands.command(help="Sends a hack to the system")
    async def hack(self, ctx):
        global is_connected

        if not is_connected:
            await ctx.send("Not connected to API server <" + THAB_API_URL + ">")
            return

        now = time.time()

        if ctx.author.id in self.timeouts and now - self.timeouts[ctx.author.id] < 10:
            await ctx.send("You're hacking way too fast!")
            return

        self.timeouts[ctx.author.id] = now
        await sio.emit('hack')

        await ctx.send("Your hack has been sent.")
