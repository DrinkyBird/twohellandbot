import discord
from discord.ext import commands
import random
import re

EIGHTBALL_PREFIX = [
    ":white_check_mark: ",
    ":thinking: ",
    ":x: "
]

EIGHTBALL_RESPONSES = [
    [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes – definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Yes.",
        "Signs point to yes.",
    ],

    [
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
    ],

    [
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
]
class EightBallCog(commands.Cog):
    @commands.command(help="Ask the Magic 8-Ball a question", aliases=["8ball"])
    async def eightball(self, ctx, *words):
        if len(words) < 1:
            await ctx.reply('You need to ask me a question.')
            return

        hashstr = ' '.join(words).lower()
        hashstr = re.sub(r'[\W_]+', '', hashstr)
        seed = hash(hashstr)

        random.seed(seed)
        result = random.randrange(0, len(EIGHTBALL_RESPONSES))
        random.seed()

        response = EIGHTBALL_RESPONSES[result][random.randrange(0, len(EIGHTBALL_RESPONSES[result]))]

        await ctx.reply(EIGHTBALL_PREFIX[result] + response)