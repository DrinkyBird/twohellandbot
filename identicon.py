import pydenticon
import discord
from discord.ext import commands
import config
import hashlib
import sys
import os
import util

class IdenticonCog(commands.Cog):
    def __init__(self):
        foreground = ["rgb(45,79,255)",
                      "rgb(254,180,44)",
                      "rgb(226,121,234)",
                      "rgb(30,179,253)",
                      "rgb(232,77,65)",
                      "rgb(49,203,115)",
                      "rgb(141,69,170)"]
        background = "rgb(224,224,224)"

        self.generator = pydenticon.Generator(5, 5, foreground=foreground, background=background)

    @commands.command(help="Generates an identicon for a string", usage="[string]")
    async def identicon(self, ctx, *, args=None):
        if args is None:
            args = []

        if not util.check_ratelimiting(ctx):
            return

        name = ctx.author.name
        if len(args) > 0:
            name = ' '.join(args)

        hash = hashlib.sha256(name.encode()).hexdigest()

        app = '/identicon/' + hash + '.png'
        url = config.WWWDATA_URL + app
        path = os.path.realpath(config.WWWDATA_PATH + app)
        if not os.path.isfile(path):
            img = self.generator.generate(name, 250, 250, output_format="png")

            with open(path, "wb") as f:
                f.write(img)

        embed = discord.Embed(title="Identicon for `" + name + "`", colour=0xFFE97F, description=url)
        embed.set_image(url=url)

        await ctx.send(embed=embed)
