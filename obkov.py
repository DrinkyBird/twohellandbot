import discord
from discord.ext import commands
import config
import util
import random
import json
import os
import time

# Obkov - The sequel to sbkov!
# It now records word appearance frequencies, and it's named after my new name. Cool.
# There's probably already a name for what I've "invented" here - in which case Obkov is the name of my implementation
class Obkov:
    def __init__(self, path=None):
        self.words = {}
        self.path = path
        self.last_generation_duration = -1

        if self.path is not None and os.path.isfile(self.path):
            self.load(self.path)

    def filter_input(self, text):
        text = " ".join(text.split())
        text = text.strip()

        return text

    def train(self, line):
        line = self.filter_input(line)
        words = line.split(' ')

        if len(words) < 2:
            return

        for i in range(len(words) - 1):
            word = words[i]
            next = words[i + 1]

            self.train_word(word, next)

        if self.path is not None:
            self.save(self.path)

    def train_word(self, word, next_word):
        word = word.lower()
        next_word = next_word.lower()

        data = [next_word, 1]

        if word not in self.words:
            self.words[word] = [data]
        else:
            already_in = False
            for i in range(len(self.words[word])):
                next = self.words[word][i]
                if next[0] == next_word:
                    self.words[word][i][1] += 1
                    already_in = True
                    break

            if not already_in:
                self.words[word].append(data)

    def find_next_word(self, word):
        word = word.lower()

        if word not in self.words:
            return None

        if len(self.words[word]) == 1:
            return self.words[word][0][0]

        num_next = len(self.words[word])
        total_chances = 0
        max_chances = 0
        for next in self.words[word]:
            total_chances += next[1]
            max_chances = max(max_chances, next[1])

        if total_chances == num_next:
            w = random.choice(self.words[word])
            return w[0]

        value = random.randrange(0, max_chances)
        sorted_words = sorted(self.words[word], key=lambda tup: tup[1], reverse=False)

        for word in sorted_words:
            if value < word[1]:
                return word[0]

        return None

    def generate_sentence(self, root=None, max_words=70):
        start = time.time()

        if root is None:
            root = random.choice(list(self.words.keys()))
        else:
            root = root.lower()

        if not root in self.words:
            return None

        words = [root]
        next_root = root
        i = 0

        while i < max_words:
            next = self.find_next_word(next_root)
            if next is None:
                break

            words.append(next)
            next_root = next
            i += 1

        result = ' '.join(words)

        end = time.time()
        self.last_generation_duration = end - start

        return result

    def save(self, path):
        data = json.dumps({
            'words': self.words
        }, separators=(',', ':'))

        with open(path, 'w') as f:
            f.write(data)

    def load(self, path):
        with open(path, 'r') as f:
            data = json.loads(f.read())

            self.words = data['words']

class ObkovCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.obkov = Obkov(config.OBKOV_PATH)

    def filter_names(self, text):
        words = text.split(' ')

        for i in range(len(words)):
            word = words[i]
            id = util.argument_to_id(word)

            if id is None:
                continue

            user = self.bot.get_user(id)
            if user is None:
                words[i] = "##" + str(id) + "##"
            else:
                word = user.name + '#' + str(user.discriminator)

            words[i] = word

        text = ' '.join(words)

        return text

    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't count our own messages
        if message.author.id == self.bot.user.id or message.author.bot:
            return

        if message.author.id in config.OBKOV_IGNORE_LIST:
            return

        text = message.content
        if not text:
            return

        # Ensure the first character is alphanumeric before learning
        if not text[0].isalnum():
            return

        text = self.filter_names(text)

        # Learn it!
        self.obkov.train(text)

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.obkov.save(config.OBKOV_PATH)

    @commands.command(help="Generate a sentence", syntax="rootWord", aliases=["obkov"])
    async def sentence(self, ctx, root_word=None):
        message = self.obkov.generate_sentence(root_word)

        if message is None and root_word is not None:
            await ctx.send(f'I have nothing to say about "{root_word}".')
            return

        if message:
            if len(message) > 1950:
                message = message[:1950]
                message += "..."
                
            await ctx.send(message)

    @commands.command(help="Train from a file", hidden=True)
    async def trainfile(self, ctx, path):
        if ctx.author.id in config.ADMINS:
            with open(path, 'r') as f:
                text = f.read()
                text = " ".join(text.split())
                words = text.split(' ')

                for i in range(len(words) - 1):
                    self.obkov.train_word(words[i], words[i + 1])

                self.obkov.save(config.MARKOV_PATH)

                await ctx.send(f'Trained on {len(words)} words')

    @commands.command(help="Show stats about the database")
    async def obkovstats(self, ctx):
        embed = discord.Embed(title="Stats")
        embed.add_field(name="Root Words", value=f'{len(self.obkov.words):,}')
        embed.add_field(name="Last Generation Duration", value=f'{self.obkov.last_generation_duration * 1000:.3f} ms')
        embed.add_field(name="Database Size", value=f'{os.path.getsize(config.OBKOV_PATH) / 1024:.3f} kB')

        await ctx.send(embed=embed)