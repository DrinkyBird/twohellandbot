import config
import time

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def argument_to_id(arg):
    if is_integer(arg):
        return int(arg)

    if (arg[:2] == '<@' or arg[:3] == '<@!') and arg[-1:] == '>':
        off = 2
        if arg[:3] == '<@!':
            off = 3
        id = arg[off:-1]
        if is_integer(id):
            return int(id)

    return None

def user_in_guild(user, guild):
    return guild.get_member(user.id) is not None

    print(f'I see {len(guild.members)} members')
    for member in guild.members:
        print(f'{member.name} = {member.id}')
        if member.id == user.id:
            return True

    return False

rate_data = {}

def clean_ratelimiting(user):
    global rate_data

    if not user in rate_data:
        return

    newlist = []
    now = int(time.time())
    for t in rate_data[user]:
        if t + config.RATELIMIT_PERIOD > now:
            newlist.append(t)

    rate_data[user] = newlist

def check_ratelimiting(ctx):
    global rate_data

    user = ctx.author.id

    if ctx.channel.id == config.SPAM_CHANNEL or user in config.ADMINS:
        return True

    if user not in rate_data:
        rate_data[user] = []

    clean_ratelimiting(user)

    if len(rate_data[user]) >= config.RATELIMIT_MESSAGES:
        return False

    now = int(time.time())
    rate_data[user].append(now)

    return True

async def log(bot, value):
    text = str(value)
    print(text)

    channel = bot.get_channel(config.LOG_CHANNEL)
    if channel is not None:
        await channel.send(text)
