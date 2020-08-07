import config
import sqlite3

database = sqlite3.connect(config.DB_PATH, check_same_thread=False)

def get_database():
    global database
    return database

def get_cursor():
    global database
    return database.cursor()

def commit():
    global database
    database.commit()