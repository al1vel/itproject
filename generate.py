import sqlite3
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()


def initialize_database():
    # Подключение к базе данных
    connection = sqlite3.connect('my_database.db', check_same_thread=False)
    cursor = connection.cursor()

    # Создание таблицы Users
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

    # Создание таблицы Rooms_Information
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

    # Создание таблицы History_of_Operations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS History_of_Operations (   
    operation_id INTEGER PRIMARY KEY,
    room_name TEXT NOT NULL,
    type_of_operation TEXT NOT NULL,
    date TEXT NOT NULL,
    time_from TEXT NOT NULL,
    time_to TEXT NOT NULL
    )
    ''')

    # Создание списка уникальных идентификаторов комнат
    room_ids = [f"{fake.word()}-{fake.random_number(digits=3)}" for _ in range(6)]

    # Заполнение таблицы Users
    fill_users_table(cursor)

    # Заполнение таблицы Rooms_Information
    fill_rooms_information_table(cursor, room_ids)

    # Заполнение таблицы History_of_Operations
    fill_history_of_operations_table(cursor, room_ids)

    # Сохранение изменений и закрытие подключения
    connection.commit()
    connection.close()
    return "Good"


def fill_users_table(cursor, num_users=10):
    for _ in range(num_users):
        username = fake.user_name()
        login = fake.user_name()
        password = fake.password()
        pass_level = fake.random_element(elements=('admin', 'user'))
        email = fake.email()
        cursor.execute("INSERT INTO Users (username, login, password, pass_level, email) VALUES (?, ?, ?, ?, ?)",
                       (username, login, password, pass_level, email))


def fill_rooms_information_table(cursor, room_ids):
    room_image_choices = ['room1.jpg', 'room2.jpg', 'room3.jpg', 'room4.jpg', 'room5.jpg',
                          'room6.jpg']
    random.shuffle(room_image_choices)
    for room_id in room_ids:
        area = fake.random_number(digits=2)
        capacity = fake.random_number(digits=2)
        equipment = fake.sentence()
        description = fake.text()
        room_image = room_image_choices.pop()  # Берем последний путь из списка (и удаляем его)
        location = fake.address()
        cursor.execute("INSERT INTO Rooms_Information (room_name, area, capacity, equipment, description, room_image, "
                       "location) VALUES (?, ?, ?, ?, ?, ?, ?)", (room_id, area, capacity, equipment, description,
                                                                  room_image, location))


def fill_history_of_operations_table(cursor, room_ids, num_users=10):
    for user_id in range(1, num_users + 1):
        table_name = f"History_of_Operations_{user_id}"
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (   
        operation_id INTEGER PRIMARY KEY,
        room_name TEXT NOT NULL,
        type_of_operation TEXT NOT NULL,
        date TEXT NOT NULL,
        time_from TEXT NOT NULL,
        time_to TEXT NOT NULL
    )
    ''')
        for room_id in room_ids:
            for _ in range(fake.random_int(min=1, max=5)):
                type_of_operation = fake.random_element(elements=('book', 'cancel'))
                date = (datetime.now() + timedelta(days=random.choice([-1, 1]) * fake.random_number(digits=2))).strftime('%Y-%m-%d')
                time_from = fake.time()
                time_to = fake.time()
                cursor.execute(
                    f"INSERT INTO {table_name} (room_name, type_of_operation, date, time_from, time_to) VALUES ("
                    f"?, ?, ?, ?, ?)",
                    (room_id, type_of_operation, date, time_from, time_to))


initialize_database()