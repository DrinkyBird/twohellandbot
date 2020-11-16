import discord
from discord.ext import commands
import requests
import urllib.parse
from dateutil import parser
import random

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

        for i in range(len(text)):
            c = text[i]

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

        return out

    @commands.command(help="Returns the definition for a word or phrase on the Urban Dictionary", aliases=["ud", "urban"])
    async def urbandictionary(self, ctx, *words):
        if len(words) < 1:
            await ctx.send_help(ctx.command)
            return

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
            if len(text) > 1020:
                text = text[:1020] + "..."

            timestamp = parser.parse(definition['written_on'])

            embed = discord.Embed(title=definition['word'], url=definition['permalink'], timestamp=timestamp, color=self.get_word_colour(definition['defid']))
            embed.add_field(name="Definition", value=text, inline=False)
            embed.add_field(name="Likes", value=f'{definition["thumbs_up"]:,}')
            embed.add_field(name="Dislikes", value=f'{definition["thumbs_down"]:,}')
            embed.set_author(name=definition['author'])
            embed.set_footer(text=f"Definition #{definition['defid']}")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("Failed to look up `" + phrase + "`: " + str(e))
