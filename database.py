import sqlite3

connection = sqlite3.connect('my_database.db')
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
id INTEGER PRIMARY KEY,
username TEXT NOT NULL,
login TEXT NOT NULL,
password TEXT NOT NULL,
pass_level INTEGER,
email TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Rooms_Information (
room_id INTEGER PRIMARY KEY,
room_name TEXT NOT NULL,
Information TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS History_of_Operations (   
operation_id INTEGER PRIMARY KEY,
room_id INTEGER,
type_of_operation TEXT NOT NULL,
booker TEXT NOT NULL,
date INTEGER,
time_from INTEGER,
time_to INTEGER
)
''')