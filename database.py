"""
Модуль для инициализации базы данных.

Создаётся база данных из трёх таблиц.
I. Первая таблица содержит id, имя, логин, пароль, уровень допуска и email пользователя.
II. Вторая таблица содержит название комнаты и информацию о ней
III. Третья таблица сохраняет полную историю операций. Состоит из колонок: id, имя комнаты, тип операции,
            имя пользователя, выполнившего операцию, дата, время начала, время окончания
"""
import sqlite3


def initialize_database():
    connection = sqlite3.connect('my_database.db', check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    login TEXT NOT NULL,
    password TEXT NOT NULL,
    pass_level TEXT NOT NULL,
    email TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Rooms_Information (
    room_name TEXT NOT NULL PRIMARY KEY,
    area FLOAT NOT NULL,
    capacity INTEGER NOT NULL,
    equipment TEXT NOT NULL,
    description TEXT NOT NULL,
    room_image TEXT NOT NULL,
    location TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS History_of_Operations (   
    operation_id INTEGER PRIMARY KEY,
    room_name TEXT NOT NULL,
    type_of_operation TEXT NOT NULL,
    booker TEXT NOT NULL,
    date TEXT NOT NULL,
    time_from TEXT NOT NULL,
    time_to TEXT NOT NULL
    )
    ''')


