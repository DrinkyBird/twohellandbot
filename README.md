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
ANNOUNCE_CHANNEL = 688527547113537644
ANNOUNCE_SERVER = 688192420013146140
WELCOME_MESSAGE = "Welcome aboard the Ark, %s! Thanks for supporting the show. Check the <#713188449469071371> channel to get notified of updates."
BOOST_MESSAGE = "Thank you %s for boosting our holy server! <:richardfedora:698367173185503302> More donations like that, and you might just make your way into heaven. Namaste. :pray:"
BOOST_LEVEL1_MESSAGE = "Bless you %s for boosting our server to Level 1! :pray: :fireworks: :partying_face:"
BOOST_LEVEL2_MESSAGE = "Bless you %s for boosting our server to Level 2! :pray: :fireworks: :partying_face:"
BOOST_LEVEL3_MESSAGE = "Bless you %s for boosting our server to Level 3! :pray: :fireworks: :partying_face:"

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

CREATE TABLE IF NOT EXISTS "stats" (
        `commands_executed`     INTEGER,
        `messages_received`     INTEGER,
        `sql_queries_executed`  INTEGER
);
```