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

    # attempt to parse mention tag
    if len(arg) == 21:
        if arg[:2] == '<@' and arg[-1:] == '>':
            id = arg[2:-1]
            if is_integer(id):
                return int(id)
    if len(arg) == 22:
        if arg[:3] == '<@!' and arg[-1:] == '>':
            id = arg[3:-1]
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

    if not user in rate_data:
        rate_data[user] = []

    clean_ratelimiting(user)

    if len(rate_data[user]) > config.RATELIMIT_MESSAGES:
        return False

    now = int(time.time())
    rate_data[user].append(now)

    return True