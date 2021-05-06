import asyncio
import math
import time

import aiohttp.web
import discord
from discord.ext import commands
import requests
import urllib.parse
import config
import secrets
import base64
import hashlib
import db
from aiohttp import web
from http.server import BaseHTTPRequestHandler, HTTPServer

USER_AGENT = 'Zirconum/5.0'
COMPANION_ENDPOINTS = {
    'main':     '',
    'pts':      'pts-',
    'odyssey':  'asp-test-'
}
ELITE_RANKS = {
    'combat': [
        'Harmless', 'Mostly Harmless', 'Novice', 'Competent', 'Expert', 'Master', 'Dangerous', 'Deadly', 'Elite'
    ],
    'trade': [
        'Penniless', 'Mostly Penniless', 'Peddler', 'Dealer', 'Merchant', 'Broker', 'Entrepreneur', 'Tycoon', 'Elite'
    ],
    'explore': [
        'Aimless', 'Mostly Aimless', 'Scout', 'Surveyor', 'Trailblazer', 'Pathfinder', 'Ranger', 'Pioneer', 'Elite'
    ],
    'soldier': [
        'Defenceless', 'Mostly Defenceless', 'Rookie', 'Soldier', 'Gunslinger', 'Warrior', 'Gladiator', 'Deadeye', 'Elite'
    ],
    'exobiologist': [
        'Directionless', 'Mostly Directionless', 'Compiler', 'Collector', 'Cataloguer', 'Taxonomist', 'Ecologist', 'Geneticist', 'Elite'
    ],
    'cqc': [
        'Helpless', 'Mostly Helpless', 'Amateur', 'Semi Professional', 'Professional', 'Champion', 'Hero', 'Legend', 'Elite'
    ],
    'federation': [
        'None', 'Recruit', 'Cadet', 'Midshipman', 'Petty Officer', 'Chief Petty Officer', 'Warrant Officer', 'Ensign', 'Lieutenant', 'Lieutenant Commander', 'Post Commander', 'Post Captain', 'Rear Admiral', 'Vice Admiral', 'Admiral'
    ],
    'empire': [
        'None', 'Outsider', 'Serf', 'Master', 'Squire', 'Knight', 'Lord', 'Baron', 'Viscount', 'Count', 'Earl', 'Marquis', 'Duke', 'Prince', 'King'
    ]
}
SHIP_NAMES = {
    "SideWinder": "Sidewinder",
    "Eagle": "Eagle",
    "Hauler": "Hauler",
    "Adder": "Adder",
    "Viper": "Viper MkIII",
    "CobraMkIII": "Cobra MkIII",
    "Type6": "Type-6 Transporter",
    "Dolphin": "Dolphin",
    "Type7": "Type-7 Transporter",
    "Asp": "Asp Explorer",
    "Vulture": "Vulture",
    "Empire_Trader": "Imperial Clipper",
    "Federation_Dropship": "Federal Dropship",
    "Orca": "Orca",
    "Type9": "Type-9 Heavy",
    "Python": "Python",
    "BelugaLiner": "Beluga Liner",
    "FerDeLance": "Fer-de-Lance",
    "Anaconda": "Anaconda",
    "Federation_Corvette": "Federal Corvette",
    "Cutter": "Imperial Cutter",
    "DiamondBack": "Diamondback Scout",
    "Empire_Courier": "Imperial Courier",
    "DiamondBackXL": "Diamondback Explorer",
    "Empire_Eagle": "Imperial Eagle",
    "Federation_Dropship_MkII": "Federal Assault Ship",
    "Federation_Gunship": "Federal Gunship",
    "Viper_MkIV": "Viper MkIV",
    "CobraMkIV": "Cobra MkIV",
    "Independant_Trader": "Keelback",
    "Asp_Scout": "Asp Scout",
    "Type9_Military": "Type-10 Defender",
    "Krait_MkII": "Krait MkII",
    "TypeX": "Alliance Chieftain",
    "TypeX_2": "Alliance Crusader",
    "TypeX_3": "Alliance Challenger",
    "Krait_Light": "Krait Phantom",
    "Mamba": "Mamba"
}


class EliteDangerousCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.httpd_started = False
        self.stateMap = {}
        self.stateChallenges = {}
        self.site = None

    async def handler(self, request):
        query = request.query

        if 'code' not in query or 'state' not in query:
            raise aiohttp.web.HTTPBadRequest()

        code = query['code']
        state = query['state']

        if state not in self.stateMap:
            print("invalid state")
            raise aiohttp.web.HTTPBadRequest()

        formdata = {
            'grant_type':       'authorization_code',
            'client_id':        config.ED_FDEV_CLIENT_ID,
            'code_verifier':    self.stateChallenges[state],
            'code':             code,
            'redirect_uri':     'http://' + config.ED_FDEV_REDIRECT_HOST + ':' + str(config.ED_FDEV_REDIRECT_PORT) + '/fd'
        }

        headers = {
            'User-Agent':       USER_AGENT,
            'Accept':           'application/json'
        }

        r = requests.post('https://auth.frontierstore.net/token', data=formdata, headers=headers)
        json = r.json()

        if 'message' in json:
            return web.Response(status=500, text=f"Auth server returned error: {json['message']}")

        access_token = json['access_token']
        token_type = json['token_type']
        refresh_token = json['refresh_token']
        expiry = math.floor(time.time()) + json['expires_in']

        discord_user_id = self.stateMap[state]

        cur = db.get_cursor()
        db.execute(cur, "SELECT COUNT(*) FROM `fdev_tokens` WHERE discord_user = ?", (discord_user_id,))
        num = cur.fetchone()[0]
        if num > 0:
            db.execute(cur, "DELETE FROM `fdev_tokens` WHERE `discord_user`=?", (discord_user_id,))

        db.execute(cur, "INSERT INTO `fdev_tokens` (`discord_user`, `access_token`, `expiry`, `refresh_token`, `token_type`) VALUES (?,?,?,?,?)",
                   (discord_user_id, access_token, expiry, refresh_token, token_type))
        db.commit()

        discord_user = self.bot.get_user(discord_user_id)
        try:
            headers = {
                'User-Agent':       USER_AGENT,
                'Accept':           'application/json',
                'Authorization':    token_type + ' ' + access_token
            }
            r = requests.get('https://auth.frontierstore.net/me', headers=headers)
            user_info = r.json()
            await discord_user.send(f"Successfully linked to Frontier account `{user_info['email']}`. Use {config.COMMAND_PREFIX}edunlink to unlink.")
        except:
            pass

        return web.Response(text='Logged in. You can close this tab now.')

    async def start_webserver(self):
        if not self.httpd_started:
            self.httpd_started = True

            app = web.Application()
            app.router.add_get('/fd', self.handler)

            runner = web.AppRunner(app)
            await runner.setup()

            self.site = web.TCPSite(runner, '', config.ED_FDEV_REDIRECT_PORT)
            await self.site.start()

    def get_fdev_auth_token(self, user_id):
        cur = db.get_cursor()
        db.execute(cur, "SELECT * FROM `fdev_tokens` WHERE discord_user = ?", (user_id,))
        row = cur.fetchone()
        if row is None:
            raise Exception(f'You have not linked a Frontier account, use {config.COMMAND_PREFIX}edlink to do so')

        now = math.floor(time.time())
        if now + 10 > row['expiry']:
            formdata = {
                'grant_type':           'refresh_token',
                'client_id':            config.ED_FDEV_CLIENT_ID,
                'refresh_token':        row['refresh_token']
            }

            headers = {
                'User-Agent':           USER_AGENT,
                'Accept':               'application/json',
                'Authorization':        row['token_type'] + ' ' + row['access_token']
            }

            r = requests.post('https://auth.frontierstore.net/token', headers=headers, data=formdata)
            json = r.json()
            if 'message' in json:
                raise Exception('Server error: ' + json['message'])

            access_token = json['access_token']
            token_type = json['token_type']
            refresh_token = json['refresh_token']
            expiry = math.floor(time.time()) + json['expires_in']

            db.execute(cur, "UPDATE fdev_tokens SET access_token=?, expiry=?, refresh_token=?, token_type=? WHERE discord_user=?",
                       (access_token, expiry, refresh_token, token_type, user_id))
            db.commit()

            return token_type + ' ' + access_token
        else:
            return row['token_type'] + ' ' + row['access_token']

    def cog_unload(self):
        asyncio.ensure_future(self.site.stop())

    @commands.command(help="Link your Frontier account")
    async def edlink(self, ctx):
        await self.start_webserver()

        state = secrets.token_hex(20)
        self.stateMap[state] = ctx.author.id
        challenge = base64.urlsafe_b64encode(secrets.token_bytes(20)).decode('utf-8').replace('=', '')
        self.stateChallenges[state] = challenge

        challengesha = base64.urlsafe_b64encode(hashlib.sha256(challenge.encode('utf-8')).digest()).decode('utf-8').replace('=', '')

        url = 'https://auth.frontierstore.net/auth'
        url += '?scope=' + urllib.parse.quote('capi')
        url += '&audience=frontier'
        url += '&response_type=code'
        url += '&client_id=' + urllib.parse.quote(config.ED_FDEV_CLIENT_ID)
        url += '&code_challenge=' + urllib.parse.quote(challengesha)
        url += '&code_challenge_method=S256'
        url += '&state=' + urllib.parse.quote(state)
        url += '&redirect_uri=' + urllib.parse.quote('http://' + config.ED_FDEV_REDIRECT_HOST + ':' + str(config.ED_FDEV_REDIRECT_PORT) + '/fd')

        try:
            await ctx.author.send(url + '\n**This link is unique to you. Do not share it.**')
            await ctx.reply('I have sent you a direct message containing a link that will allow you to log in to your Frontier account.')
        except:
            await ctx.reply('Failed to send you a direct message. Ensure that you allow DMs from members of this server.')

    @commands.command(help="Unlink your Frontier account")
    async def edunlink(self, ctx):
        cur = db.get_cursor()

        db.execute(cur, "SELECT COUNT(*) FROM `fdev_tokens` WHERE discord_user = ?", (ctx.author.id,))
        num = cur.fetchone()[0]

        if num > 0:
            db.execute(cur, "DELETE FROM `fdev_tokens` WHERE `discord_user`=?", (ctx.author.id,))
            db.commit()

            await ctx.reply('Your Frontier account has been unlinked.')
        else:
            await ctx.reply('You haven\'t linked a Frontier account.')

    def get_cmdr_rank(self, json, field):
        if field in ELITE_RANKS:
            return ELITE_RANKS[field][json['rank'][field]]
        else:
            return json['rank'][field]

    @commands.command(help="Shows information about your Elite Dangerous commander")
    async def edprofile(self, ctx, endpoint='main'):
        if endpoint not in COMPANION_ENDPOINTS:
            await ctx.reply('Invalid endpoint `' + endpoint + '`')
            return

        try:
            token = self.get_fdev_auth_token(ctx.author.id)
        except Exception as e:
            await ctx.reply('Failed to get auth token: ' + str(e))
            return

        if token is None:
            await ctx.reply('Failed to get auth token')
            return

        headers = {
            'User-Agent':       USER_AGENT,
            'Authorization':    token
        }

        r = requests.get('https://' + COMPANION_ENDPOINTS[endpoint] + 'companion.orerve.net/profile', headers=headers)
        try:
            json = r.json()
        except:
            await ctx.reply('Failed to decode API response. The server returned: `' + r.text + '`')
            return

        commander = json['commander']
        last_system = json['lastSystem']
        last_station = json['lastStarport']
        ship = json['ship']

        state = 'In Space'
        if not commander['alive']:
            state = 'Dead'
        elif commander['docked']:
            state = 'Docked'
        elif 'onfoot' in commander and commander['onfoot']:
            state = 'On Foot'

        location = 'Unknown'
        if last_system:
            if last_station:
                location = f"{last_station['name']}, {last_system['name']}"
            else:
                location = last_system['name']

        ship_location = None
        if 'starsystem' in ship:
            if 'station' in ship:
                ship_location = f"{ship['station']['name']}, {ship['starsystem']['name']}"
            else:
                ship_location = ship['starsystem']['name']

        embed = discord.Embed(title=f"CMDR {commander['name']}")
        embed.add_field(name="ID", value=f"`{commander['id']}`", inline=True)
        embed.add_field(name="State", value=state, inline=True)
        embed.add_field(name="Location", value=location, inline=True)
        embed.add_field(name="Credits", value=f"{commander['credits']:,}", inline=True)
        embed.add_field(name="Debt", value=f"{commander['debt']:,}", inline=True)
        embed.add_field(name="Combat", value=self.get_cmdr_rank(commander, 'combat'), inline=True)
        embed.add_field(name="Trade", value=self.get_cmdr_rank(commander, 'trade'), inline=True)
        embed.add_field(name="Exploration", value=self.get_cmdr_rank(commander, 'explore'), inline=True)
        if 'soldier' in commander['rank']:
            embed.add_field(name="Mercenary", value=self.get_cmdr_rank(commander, 'soldier'), inline=True)
        if 'Exobiologist' in commander['rank']:
            embed.add_field(name="Mercenary", value=self.get_cmdr_rank(commander, 'exobiologist'), inline=True)
        embed.add_field(name="CQC", value=self.get_cmdr_rank(commander, 'cqc'), inline=True)
        embed.add_field(name="Federation", value=self.get_cmdr_rank(commander, 'federation'), inline=True)
        embed.add_field(name="Empire", value=self.get_cmdr_rank(commander, 'empire'), inline=True)

        if 'shipID' in ship:
            embed.add_field(name="Ship ID", value=f"`{ship['shipID'].upper()}`", inline=True)
        if 'shipName' in ship:
            embed.add_field(name="Ship Name", value=ship['shipName'], inline=True)
        if 'name' in ship:
            embed.add_field(name="Ship Type", value=SHIP_NAMES[ship['name']], inline=True)
        if ship_location is not None:
            embed.add_field(name="Ship Location", value=ship_location, inline=True)


        await ctx.reply(embed=embed)

    @commands.command(help="Returns active Elite Dangerous community goals")
    async def edcgs(self, ctx, endpoint='main'):

        if endpoint not in COMPANION_ENDPOINTS:
            await ctx.reply('Invalid endpoint `' + endpoint + '`')
            return

        try:
            token = self.get_fdev_auth_token(ctx.author.id)
        except Exception as e:
            await ctx.reply('Failed to get auth token: ' + str(e))
            return

        if token is None:
            await ctx.reply('Failed to get auth token')
            return

        headers = {
            'User-Agent':       USER_AGENT,
            'Authorization':    token
        }

        r = requests.get('https://' + COMPANION_ENDPOINTS[endpoint] + 'companion.orerve.net/communitygoals', headers=headers)
        try:
            json = r.json()
        except:
            await ctx.reply('Failed to decode API response. The server returned: `' + r.text + '`')
            return

        cgs = json['activeCommunityGoals']

        if 'activeCommunityGoals' not in json or len(cgs) < 1:
            await ctx.reply("No active Community Goals at the moment.")
            return

        for cg in cgs:
            bulletin = cg['bulletin']
            if len(bulletin) > 1000:
                bulletin = bulletin[:1000] + "..."

            percentage = cg['qty'] / cg['target_qty'] * 100

            embed = discord.Embed(title=cg['title'])
            embed.add_field(name="Location", value=f"{cg['market_name']}, {cg['starsystem_name']}", inline=True)
            embed.add_field(name="Ends", value=cg['expiry'], inline=True)
            embed.add_field(name="Objective", value=cg['objective'], inline=False)
            embed.add_field(name="Bulletin", value=bulletin, inline=False)
            embed.add_field(name="Progress", value=f"{cg['qty']:,}", inline=True)
            embed.add_field(name="Target", value=f"{cg['target_qty']:,} ({percentage:.0f}%)", inline=True)

            if 'commander_progress' in cg:
                progress = cg['commander_progress']
                embed.add_field(name="Your Contribution", value=f"{progress['contributionQty']:,} (top {progress['percentile']}%)")
            else:
                embed.add_field(name="Your Contribution", value=f"You have not made any contribution to this Community Goal.")

            await ctx.send(embed=embed)