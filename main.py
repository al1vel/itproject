import sqlite3
from fastapi import Request, Form
from fastapi import FastAPI, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from database import initialize_database
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

initialize_database()
connection = sqlite3.connect('my_database.db', check_same_thread=False)
cursor = connection.cursor()
templates = Jinja2Templates(directory="templates")

app = FastAPI()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegistration(BaseModel):
    username: str
    password: str
    login: str
    email: EmailStr


@app.get("/")
async def root():
    """
    Точка входа API

    Returns:
        MAIN PAGE
    """
    return "MAIN PAGE"


@app.post("/book")
def book(login: str, room_name: str, date: str, time_from: str, time_to: str):
    """
    Функция API для бронирования комнаты.

    Функция создаёт бронь комнаты в базе данных в таблице "История операций".

    Args:
        login: string
        room_name:  string
        date: string in format **.**.****
        time_from: string in format **:**
        time_to: string in format **:**

    Returns:
        nothing
    """
    cursor.execute(f'INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, time_to)'
                   f' VALUES ("{room_name}", "booked", "{login}", "{date}", "{time_from}", "{time_to}")')


@app.get("/get_info")
def get_info(room_name: str):
    """
    Функция API, получающая информацию о комнате.

    Args:
        room_name: string

    Returns:
        array of strings
    """
    cursor.execute(f'SELECT Information FROM Rooms_information WHERE room_name = "{room_name}"')
    return cursor.fetchall()


@app.get("/check")
def check(login: str):
    """
    Функция для проверки бронирования

    Args:
        login: string

    Returns:
        array of values: [id, room_name, user, date, time_from, time_to]
    """
    cursor.execute(f'SELECT * FROM History_of_Operations WHERE booker = "{login}"')
    return cursor.fetchall()


def split_time_gaps(free_gaps, current_bookings):
    """
    Функция для получения свободных временных промежутков

    Изначально считает каждую комнату полностью свободной. Затем убирает занятые отрезки времени.

    Args:
        free_gaps: dict, keys = room names, values = array of gaps in minutes
        current_bookings: dict, keys = date, values = array of values [room_name, time_from, time_to]

    Returns:
        dict, keys = room names, values = array of free gaps in minutes (int)
    """
    for booking in current_bookings:
        r_name = booking[0]
        temp1 = booking[1].split(":")
        time_from = int(temp1[0]) * 60 + int(temp1[1])
        temp2 = booking[2].split(":")
        time_to = int(temp2[0]) * 60 + int(temp2[1])

        current_gaps = free_gaps[r_name]
        for i in range(len(current_gaps)):
            if current_gaps[i][0] <= time_from and current_gaps[i][1] >= time_to:
                if current_gaps[i][0] == time_from:
                    if current_gaps[i][1] == time_to:
                        del current_gaps[i]
                    else:
                        current_gaps[i][0] = time_to
                    break
                elif current_gaps[i][1] == time_to:
                    current_gaps[i][0] = time_from
                    break
                else:
                    current_gaps.append([time_to, current_gaps[i][1]])
                    current_gaps[i][1] = time_from
                    break
        current_gaps.sort()
        free_gaps[r_name] = current_gaps
    return free_gaps


def format_time_to_string(free_gaps):
    """
    Функция приведения промежутка времени к строке

    Args:
        free_gaps: dict, keys = room names, values = array of free gaps in minutes (int)

    Returns:
        dict, keys = room names, values = array of strings [**:** - **:**, ...]
    """
    for room in free_gaps.keys():
        temp = free_gaps[room]
        new = []
        for item in temp:
            time = (f'{item[0] // 60}:{item[0] % 60 if (item[0] % 60) != 0 else "00"} - {item[1] // 60}:'
                    f'{item[1] % 60 if (item[1] % 60) != 0 else "00"}')
            new.append(time)
        free_gaps[room] = new
    return free_gaps


@app.get("/free_gaps")
def get_free_gaps_for_rooms(date: str):
    """
    Функция API для получения свободных окон для всех комнат на конкретную дату

    Функция совершает запрос в базу для получения всех броней на конкретную дату для всех комнаты. Затем помечает
    эти промежутки недоступными, возвращая словарь, где ключами является названия комнат, а значениями - массивы строк,
    каждая из которых содержит свободный временной промежуток.

    Args:
        date: string

    Returns:
        dict, keys = room names, values = array of strings ["**:** - **:**, ...]
    """
    cursor.execute(f'SELECT room_name FROM Rooms_Information')
    all_room_names = cursor.fetchall()
    cursor.execute(f'SELECT room_name, time_from, time_to FROM History_of_Operations WHERE date = "{date}"')
    current_bookings = cursor.fetchall()

    free_gaps = {}
    for r_name in all_room_names:
        free_gaps[r_name[0]] = [[540, 1080], ]
    split_time_gaps(free_gaps, current_bookings)
    format_time_to_string(free_gaps)
    return free_gaps


@app.post("/add_room")
def add_room(room_name: str, inf: str):
    """
    Функция API, добавляющая новую комнату

    Args:
        room_name: string
        inf: string

    Returns:
        nothing
    """
    cursor.execute(f'INSERT INTO Rooms_Information (room_name, Information) VALUES ("{room_name}", "{inf}")')


@app.get("/free_gaps_for_room")
def get_free_gaps_for_one_room(date: str, room_name: str):
    """
    Функция API для получения свободных окон для конкретной комнаты на конкретную дату

    Функция совершает запрос в базу для получения всех броней на конкретную дату для конкретной комнаты. Затем помечает
    эти промежутки недоступными, возвращая словарь, где ключом является названия комнаты, а значением - массивы строк,
    каждая из которых содержит свободный временной промежуток.

    Args:
        date: string
        room_name: string

    Returns:
        dict, keys = room names, values = array of strings ["**:** - **:**, ...]
    """
    cursor.execute(f'SELECT room_name, time_from, time_to FROM History_of_Operations WHERE date = "{date}" AND '
                   f'room_name = "{room_name}"')
    current_bookings = cursor.fetchall()
    free_gaps = dict()
    free_gaps[room_name] = [[540, 1080], ]
    split_time_gaps(free_gaps, current_bookings)
    format_time_to_string(free_gaps)
    return free_gaps
  

# Хэширование пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Функция для хэширования пароля
def get_password_hash(password):
    return pwd_context.hash(password)


# Функция для аутентификации пользователя
async def authenticate_user(login: str, password: str, cursor1):
    """
    Функция для аутентификации пользователя
    Функция принимает электронную почту и пароль пользователя, выполняет поиск пользователя в базе данных
    Args:
        login:
        password:
        cursor1:

    Returns:

    """
    cursor1.execute('SELECT * FROM Users WHERE login = ?', (login,))
    user = cursor1.fetchone()
    if user is None:
        return False
    if not pwd_context.verify(password, user[3]):
        return False
    return True


@app.get("/register", response_class=HTMLResponse)
async def show_registration_form(request: Request):
    """

    Args:
        request:

    Returns:

    """
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...),
                        login: str = Form(...)):
    """
    Функция для регистрации пользователя

    Функция проверяет данные пользователя, хэширует пароль, проверяет уникальность адреса электронной почты,
    а затем добавляет нового пользователя в базу данных

    Args:
        request:
        login:
        username:
        password:
        email:
        login:

    Returns:

    """
    # Проверки данных
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен содержать не менее 8 символов")
    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы одну цифру")
    if not any(char.isalpha() for char in password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы одну букву")
    if not any(char in "!@#$%^&*()-_+=<>?/.,:;" for char in password):
        raise HTTPException(status_code=400, detail="Пароль должен содержать хотя бы один специальный символ: "
                                                    "!@#$%^&*()-_+=<>?/.,:;")

    # Проверка наличия пользователя с таким же email в базе данных
    cursor.execute('SELECT * FROM Users WHERE email = ?', (email,))
    existing_user = cursor.fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким адресом электронной почты "
                                                    "уже зарегистрирован")

    # Проверка наличия пользователя с таким же логином в базе данных
    cursor.execute('SELECT * FROM Users WHERE login = ?', (login,))
    existing_login = cursor.fetchone()
    if existing_login:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже зарегистрирован")

    # Хэширование пароля и добавление пользователя в базу данных
    hashed_password = get_password_hash(password)
    cursor.execute('INSERT INTO Users (username, password, email, login) VALUES (?, ?, ?, ?)',
                   (username, hashed_password, email, login))
    connection.commit()

    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/login/", response_class=HTMLResponse)
async def login_user(login: str, password: str):
    """
    Функция для авторизации пользователя
    Функция предназначена для того, чтобы аутентифицировать пользователя, используя предоставленные им логин и пароль
    Args:
        login:
        password:

    Returns:

    """
    authenticated = await authenticate_user(login, password, cursor)
    if not authenticated:
        raise HTTPException(status_code=401, detail="Неправильный логин или пароль")
    return Response(content="register.html", media_type="text/html")
