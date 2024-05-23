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
    pass_level TEXT CHECK(pass_level IN ('A', 'B', 'C')) NOT NULL,
    email TEXT NOT NULL
    )
    ''')

    # Создание таблицы Rooms_Information
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Rooms_Information (
    room_name TEXT NOT NULL PRIMARY KEY,
    area FLOAT NOT NULL,
    capacity INTEGER NOT NULL,
    eq_proj TEXT NOT NULL,
    eq_board TEXT NOT NULL,
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
    type_of_operation TEXT CHECK(type_of_operation IN ('book', 'cancel', 'cancel_any')) NOT NULL,
    booker TEXT NOT NULL,
    date TEXT NOT NULL,
    time_from TEXT NOT NULL,
    time_to TEXT NOT NULL,
    FOREIGN KEY (room_name) REFERENCES Rooms_Information(room_name),
    FOREIGN KEY (booker) REFERENCES Users(username)
    )
    ''')

    # Заполнение таблицы Users
    fill_users_table(cursor)

    # Заполнение таблицы Rooms_Information
    fill_rooms_information_table(cursor)

    # Заполнение таблицы History_of_Operations
    fill_history_of_operations_table(cursor)

    # Сохранение изменений и закрытие подключения
    connection.commit()
    connection.close()


def fill_users_table(cursor, num_users=10):
    for _ in range(num_users):
        username = fake.user_name()
        login = fake.user_name()
        password = fake.password()
        pass_level = fake.random_element(elements=('A', 'B', 'C'))
        email = fake.email()
        cursor.execute("INSERT INTO Users (username, login, password, pass_level, email) VALUES (?, ?, ?, ?, ?)",
                       (username, login, password, pass_level, email))


def fill_rooms_information_table(cursor):
    room_image_choices = ['room1.jpg', 'room2.jpg', 'room3.jpg', 'room4.jpg', 'room5.jpg',
                          'room6.jpg']
    random.shuffle(room_image_choices)
    for _ in range(6):
        room_name = fake.word()
        area = fake.random_number(digits=2)
        capacity = fake.random_number(digits=2)
        eq_proj = random.choice(['YES', 'NO'])
        eq_board = random.choice(['YES', 'NO'])
        description = fake.text()
        room_image = room_image_choices.pop()
        location = fake.address()
        cursor.execute("INSERT INTO Rooms_Information (room_name, area, capacity, eq_proj, eq_board, description, "
                       "room_image,"
                       "location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (room_name, area, capacity, eq_proj, eq_board,
                                                                     description, room_image, location))


def fill_history_of_operations_table(cursor, num_users=10):
    for _ in range(100):
        room_name = cursor.execute("SELECT room_name FROM Rooms_Information ORDER BY RANDOM() LIMIT 1").fetchone()[0]
        pass_level = fake.random_element(elements=('B', 'C'))  # Рандомный выбор уровня доступа
        if pass_level == 'C':
            type_of_operation = fake.random_element(elements=('book', 'cancel', 'cancel_any'))
        elif pass_level == 'B':
            type_of_operation = fake.random_element(elements=('book', 'cancel'))
        booker = cursor.execute(
            "SELECT login FROM Users WHERE pass_level = ? ORDER BY RANDOM() LIMIT 1", (pass_level,)).fetchone()
        if booker:
            booker_name = booker[0]  # Получаем имя пользователя
        date = ((datetime.now() + timedelta(days=random.choice([-1, 1]) * fake.random_number(digits=2))).
                strftime('%d.%m.%Y'))
        while True:
            time_from = fake.time()[0:5]
            if 8 <= int(time_from[0:2]) <= 17:
                break
        while True:
            time_to = fake.time()[0:5]
            if 19 > int(time_to[0:2]) > int(time_from[0:2]):
                break
            elif int(time_to[0:2] == time_from[0:2]):
                if int(time_to[3:5] > time_from[3:5]):
                    break
        cursor.execute(
            "INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, "
            "time_to) VALUES ("
            "?, ?, ?, ?, ?, ?)",
            (room_name, type_of_operation, booker_name, date, time_from, time_to))


initialize_database()
