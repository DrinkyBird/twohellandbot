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