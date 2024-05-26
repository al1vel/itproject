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
    type_of_operation TEXT CHECK(type_of_operation IN ("booking", "unbooking", "unnbooking other user")) NOT NULL,
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
    room_image_choices = ['room1.jpg', 'room2.jpg', 'room3.jpg', 'room4.jpg', 'room5.jpg', 'room6.jpg']
    random.shuffle(room_image_choices)
    existing_room_names = set()  # To store existing room names

    for _ in range(6):
        room_name = fake.word()
        while room_name in existing_room_names:  # Check if room name already exists
            room_name = fake.word()
        existing_room_names.add(room_name)  # Add room name to the set of existing room names

        area = fake.random_number(digits=2)
        capacity = fake.random_number(digits=2)
        eq_proj = random.choice(['YES', 'NO'])
        eq_board = random.choice(['YES', 'NO'])
        description = fake.text()
        room_image = room_image_choices.pop()
        location = fake.address()

        cursor.execute("INSERT INTO Rooms_Information (room_name, area, capacity, eq_proj, eq_board, description, "
                       "room_image, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (room_name, area, capacity, eq_proj, eq_board, description, room_image, location))


def generate_time_in_range(start_time, end_time):
    # Generate a time string in the format HH:MM within the specified range
    hour = random.randint(int(start_time[:2]), int(end_time[:2]))
    if hour < 10:
        hour_str = '0' + str(hour)
    else:
        hour_str = str(hour)
    minute = random.randint(0, 59)
    if minute < 10:
        minute_str = '0' + str(minute)
    else:
        minute_str = str(minute)
    return hour_str + ':' + minute_str


def fill_history_of_operations_table(cursor, num_users=10):
    for _ in range(100):
        room_name = cursor.execute("SELECT room_name FROM Rooms_Information ORDER BY RANDOM() LIMIT 1").fetchone()[0]
        pass_level = fake.random_element(elements=('B', 'C'))  # Рандомный выбор уровня доступа
        if pass_level == 'C':
            type_of_operation = fake.random_element(elements=("booking", "unbooking", "unnbooking other user"))
        elif pass_level == 'B':
            type_of_operation = fake.random_element(elements=("booking", "unbooking"))
        booker = cursor.execute(
            "SELECT login FROM Users WHERE pass_level = ? ORDER BY RANDOM() LIMIT 1", (pass_level,)).fetchone()
        if booker:
            booker_name = booker[0]  # Получаем имя пользователя
        date = ((datetime.now() + timedelta(days=random.choice([-1, 1]) * fake.random_number(digits=2))).
                strftime('%d.%m.%Y'))

        # Генерация времени только с 9 утра до 18 вечера
        time_from = generate_time_in_range("09:00", "17:59")
        time_to = generate_time_in_range(time_from, "17:59")

        cursor.execute(
            "INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, "
            "time_to) VALUES ("
            "?, ?, ?, ?, ?, ?)",
            (room_name, type_of_operation, booker_name, date, time_from, time_to))


initialize_database()
