import config
import sqlite3
import stats

database = sqlite3.connect(config.DB_PATH, check_same_thread=False)
database.row_factory = sqlite3.Row

def get_database():
    global database
    return database

def get_cursor():
    global database
    return database.cursor()

def commit():
    global database
    database.commit()

def execute(cursor, *args, **kwargs):
    stats.increment_stat("sql_queries_executed")
    return cursor.execute(*args, **kwargs)