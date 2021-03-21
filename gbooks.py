import discord
from discord.ext import commands
import requests
import urllib.parse
import config

class GoogleBooksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_isbns(self, volumeInfo):
        if 'industryIdentifiers' not in volumeInfo:
            return ''

        text = ''
        for id in volumeInfo['industryIdentifiers']:
            if id['type'].startswith('ISBN'):
                if len(text) > 0:
                    text += ', '
                text += str(f"`{id['identifier']}`")
        return text

    @commands.command(help="Returns the first result for a search on Google Books", aliases=["gbooks", "books", "book"])
    async def googlebooks(self, ctx, *, query=None):
        if not query:
            await ctx.reply(
                '**Syntax: `%sgooglebooks <query>`**\n'
                'This command returns the top result for the given search query on Google Books.\n\n'
                'You can use certain keywords in your query, e.g.:\n'
                '`isbn:9780943151168` - search by ISBN, similarly `lccn:` and `oclc:` are supported\n'
                '`intitle:JTHM` - search by title\n'
                '`inauthor:"Jhonen Vasquez"` - search by author\n'
                '`inpublisher:SLG` - search by publisher\n\n'
                'See also: <https://developers.google.com/books/docs/v1/using#PerformingSearch>'
                % (config.COMMAND_PREFIX))
            return

        url = 'https://www.googleapis.com/books/v1/volumes?q=' + urllib.parse.quote(query)

        try:
            r = requests.get(url)
            json = r.json()
            totalItems = json['totalItems']

            if totalItems < 1:
                await ctx.reply('There were no results for that query.')
            else:
                volume = json['items'][0]
                volumeInfo = volume['volumeInfo']
                link = 'https://books.google.co.uk/books?id=' + volume['id']

                title = volumeInfo['title']
                if 'subtitle' in volumeInfo:
                    title += ': ' + volumeInfo['subtitle']

                embed = discord.Embed(title=title, url=link)

                if 'imageLinks' in volumeInfo:
                    imageLinks = volumeInfo['imageLinks']
                    if 'thumbnail' in imageLinks:
                        embed.set_thumbnail(url=imageLinks['thumbnail'])
                    elif 'smallThumbnail' in imageLinks:
                        embed.set_thumbnail(url=imageLinks['smallThumbnail'])

                if 'authors' in volumeInfo:
                    name = 'Author' if len(volumeInfo['authors']) == 1 else 'Authors'
                    embed.add_field(name=name, value=', '.join(volumeInfo['authors']), inline=True)

                if 'pageCount' in volumeInfo:
                    embed.add_field(name='Pages', value=str(volumeInfo['pageCount']), inline=True)

                if 'publisher' in volumeInfo:
                    embed.add_field(name='Published by', value=volumeInfo['publisher'], inline=True)

                if 'publishedDate' in volumeInfo:
                    embed.add_field(name='Publication date', value=volumeInfo['publishedDate'], inline=True)

                if 'averageRating' in volumeInfo and 'ratingsCount' in volumeInfo:
                    embed.add_field(name='Rating', value=f"{volumeInfo['averageRating']}/5 stars (from {volumeInfo['ratingsCount']} ratings)", inline=True)

                isbns = self.get_isbns(volumeInfo)
                if len(isbns) > 0:
                    embed.add_field(name='ISBN', value=isbns, inline=True)

                if 'description' in volumeInfo:
                    text = volumeInfo['description']
                    if len(text) > 500:
                        text = text[:500] + '...'
                    embed.add_field(name='Description', value=text, inline=False)

                await ctx.reply(f'Your query returned {totalItems} result{"" if totalItems == 1 else "s"}.', embed=embed)
        except Exception as e:
                await ctx.reply("Failed to look up `" + query + "`: " + str(e))