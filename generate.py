import sqlite3
from faker import Faker

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
    booker TEXT NOT NULL,
    date TEXT NOT NULL,
    time_from TEXT NOT NULL,
    time_to TEXT NOT NULL
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


def fill_rooms_information_table(cursor, num_rooms=10):
    for _ in range(num_rooms):
        room_name = f"{fake.word()}-{fake.random_number(digits=3)}"
        area = fake.random_number(digits=2)
        capacity = fake.random_number(digits=2)
        equipment = fake.sentence()
        description = fake.text()
        room_image = fake.image_url()
        location = fake.address()
        cursor.execute("INSERT INTO Rooms_Information (room_name, area, capacity, equipment, description, room_image, "
                       "location) VALUES (?, ?, ?, ?, ?, ?, ?)", (room_name, area, capacity, equipment, description,
                                                                  room_image, location))


def fill_history_of_operations_table(cursor, num_users=10):
    for user_id in range(1, num_users + 1):
        table_name = f"History_of_Operations_{user_id}"
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (   
        operation_id INTEGER PRIMARY KEY,
        room_name TEXT NOT NULL,
        type_of_operation TEXT NOT NULL,
        booker TEXT NOT NULL,
        date TEXT NOT NULL,
        time_from TEXT NOT NULL,
        time_to TEXT NOT NULL
    )
    ''')
        for _ in range(fake.random_int(min=1, max=5)):
            room_name = fake.word()
            type_of_operation = fake.random_element(elements=('book', 'cancel'))
            booker = fake.word()
            date = fake.date()
            time_from = fake.time()
            time_to = fake.time()
            cursor.execute(
                f"INSERT INTO {table_name} (room_name, type_of_operation, date, booker, time_from, time_to) VALUES ("
                f"?, ?, ?,"
                f"?, ?, ?)",
                (room_name, type_of_operation, date, booker, time_from, time_to))


initialize_database()
