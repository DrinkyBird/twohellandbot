# 2HELLANDBOT

Python rewrite of TOHELLANDBOT

## Dependencies

```
python3 -m pip install -U discord.py pydenticon
```

## Example config

```python
# Your Discord bot token
BOT_TOKEN=""

# Your sqlite database path
DB_PATH='C:/Users/DrinkyBird/Dev/twohellandbot/tohellandbot.sqlite'

# List of user IDs of bot admins
ADMINS=[
    195246948847058954
]

# IDs of roles to welcome when people gain them or join with them
WELCOME_ROLES=[
    563405285050548235,
    563405372476358678
]
WELCOME_CHANNEL = 563395608489099267    # ID of the channel to announce new members
WELCOME_MESSAGE = "Welcome aboard the Ark, %s! Thanks for supporting the show. Check the <#713188449469071371> channel to get notified of updates."

# Bot command prefix
COMMAND_PREFIX = '!'

# Your web directory and URL prefix
WWWDATA_PATH = "C:/Users/DrinkyBird/Dev/twohellandbot/s3"
WWWDATA_URL = "https://tohellandbot.s3-eu-west-1.amazonaws.com"
```

## Database schema
```sql
CREATE TABLE IF NOT EXISTS "quotes" (
        `id`    INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        `text`  TEXT,
        `date`  INTEGER,
        `submitter`     TEXT,
        `submitter_name`        TEXT
);
```