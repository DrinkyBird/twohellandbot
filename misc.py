import discord
from discord.ext import commands
import requests
import urllib.parse
from dateutil import parser
import random
import time
import asyncio

class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def blachool(self, ctx):
        emoji = self.bot.get_emoji(727669022065295382)
        if emoji is not None:
            try:
                await ctx.message.add_reaction(emoji)
            except:
                pass

    def get_word_colour(self, id):
        random.seed(hash(id))

        r = random.randrange(32, 224)
        g = random.randrange(32, 224)
        b = random.randrange(32, 224)

        random.seed() # reseed, prevents gaming !sex

        val = (((r & 0xFF) << 16) + ((g & 0xFF) << 8) + (b & 0xFF)) & 0xFFFFFF
        return val

    def get_word_permalink(self, word):
        url = "https://api.urbandictionary.com/v0/define?term=" + urllib.parse.quote(word)
        try:
            r = requests.get(url)
            json = r.json()
            list = json['list']

            return list[0]['permalink']
        except:
            return None

    # expands links
    def parse_definition(self, text):
        inlink = False
        linkbuf = ''
        out = ''

        for c in text:
            if c == '[':
                inlink = True
            elif c == ']':
                inlink = False

                url = self.get_word_permalink(linkbuf)
                if url is None:
                    out += linkbuf
                else:
                    out += '[' + linkbuf + '](' + url + ')'

                linkbuf = ''
            elif inlink:
                linkbuf += c
            else:
                out += c

        if len(out) > 1020:
            out = out[:1020] + "..."

        return out

    @commands.command(help="Returns the definition for a word or phrase on the Urban Dictionary", aliases=["ud", "urban"])
    async def urbandictionary(self, ctx, *words):
        if len(words) < 1:
            await ctx.send_help(ctx.command)
            return

        async with ctx.typing():
            start = time.time()
            phrase = ' '.join(words)
            url = "https://api.urbandictionary.com/v0/define?term=" + urllib.parse.quote(phrase)

            try:
                r = requests.get(url)
                json = r.json()
                list = json['list']

                if len(list) < 1:
                    await ctx.send("No results for `" + phrase + "`")
                    return

                definition = list[0]
                text = self.parse_definition(definition['definition'])
                example = self.parse_definition(definition['example'])

                timestamp = parser.parse(definition['written_on'])

                embed = discord.Embed(title=definition['word'], url=definition['permalink'], timestamp=timestamp,
                                      color=self.get_word_colour(definition['defid']))
                embed.add_field(name="Definition", value=text, inline=False)
                if example:
                    embed.add_field(name="Example", value=example, inline=False)
                embed.set_author(name=definition['author'])
                embed.set_footer(text=f"Definition #{definition['defid']} • 👍 {definition['thumbs_up']:,} / 👎 {definition['thumbs_down']:,}")

                end = time.time()
                delta = end - start
                print("delta: " + str(delta))
                if delta < 0.5:
                    await asyncio.sleep(0.5 - delta)

                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send("Failed to look up `" + phrase + "`: " + str(e))
