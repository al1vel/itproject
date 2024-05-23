import sqlite3
from fastapi import Request, Form
from fastapi import FastAPI, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from database import initialize_database
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

initialize_database()
connection = sqlite3.connect('my_database.db', check_same_thread=False)
cursor = connection.cursor()
templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates/static"), name="static")


class NotEnoughRights(HTTPException):
    pass


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegistration(BaseModel):
    username: str
    password: str
    doublepassword: str
    login: str
    pass_level: str
    email: EmailStr


@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


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
    try:
        access_permission("booking", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return "This User hasn`t enough rights"
    cursor.execute(f'INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, time_to)'
                   f' VALUES ("{room_name}", "booking", "{login}", "{date}", "{time_from}", "{time_to}")')


@app.delete("/unnbook")
def unnbook(login: str, operation_id: int):
    """
    Функция API для отмены бронирования комнаты.

    Функция удаляет бронь комнаты из базе данных в таблице "История операций".

    Args:
        login: string
        operation_id:  int

    Returns:
        nothing
    """
    try:
        cursor.execute(f'SELECT booker FROM Rooms_information WHERE operation_id = ?', (operation_id, ))
        if login == cursor.fetchall():
            access_permission("unnbooking", login)
        else:
            access_permission("unnbooking other user", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return "This User hasn`t enough rights"
    cursor.execute(f'DELETE FROM History_of_Operations WHERE operation_id = ?', (operation_id, ))


@app.get("/get_info", response_class=HTMLResponse)
def get_info(request: Request, room_name: str):
    """
    Функция API, получающая информацию о комнате.

    Args:
        request:
        room_name: string

    Returns:
        HTML страницу с информацией о комнате
    """
    cursor.execute(f'SELECT * FROM Rooms_information WHERE room_name = "{room_name}"')
    room_info = cursor.fetchone()
    if room_info is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_name}' not found")
    room_data = {
        "room_name": room_info[0],
        "area": room_info[1],
        "capacity": room_info[2],
        "equipment": room_info[3],
        "description": room_info[4],
        "room_image": room_info[5],
        "location": room_info[6]
    }
    return templates.TemplateResponse("room.html", {"request": request, **room_data})


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
def add_room(room_name: str, inf: str, login: str):
    """
    Функция API, добавляющая новую комнату

    Args:
        room_name: string
        inf: string
        login: string

    Returns:
        nothing
    """
    try:
        access_permission("adding room", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return "This User hasn`t enough rights"
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
async def register_user(request: Request, username: str = Form(...), password: str = Form(...),
                        doublepassword: str = Form(), email: str = Form(...), pass_level: str = 'A',
                        login: str = Form(...)):
    """
    Функция для регистрации пользователя

    Функция проверяет данные пользователя, хэширует пароль, проверяет уникальность адреса электронной почты,
    а затем добавляет нового пользователя в базу данных

    Args:
        pass_level:
        doublepassword:
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
    if password != doublepassword:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

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
    cursor.execute('INSERT INTO Users (username, password, email, pass_level, login) VALUES (?, ?, ?, ?, ?)',
                   (username, hashed_password, email, pass_level, login))
    connection.commit()

    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def show_login_form(request: Request):
    """

    Args:
        request:

    Returns:

    """
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, login: str = Form(...), password: str = Form(...)):
    """
    Функция для авторизации пользователя
    Функция предназначена для того, чтобы аутентифицировать пользователя, используя предоставленные им логин и пароль
    Args:
        request:
        login:
        password:

    Returns:

    """
    authenticated = await authenticate_user(login, password, cursor)
    if not authenticated:
        raise HTTPException(status_code=401, detail="Неправильный логин или пароль")

    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/user_info", response_class=HTMLResponse)
async def get_user_info(request: Request, login: str):
    cursor.execute('SELECT * FROM Users WHERE login = ?', (login,))
    user_data = cursor.fetchone()

    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Form the name of the history table dynamically based on the login
    history_table_name = f'History_of_Operations_{user_data[0]}'  # Assuming user_data[0] is the operation_id

    # Fetch active bookings for the user
    cursor.execute(f'SELECT * FROM {history_table_name} WHERE date >= date("now")')
    active_bookings = cursor.fetchall()

    # Fetch booking history for the user
    cursor.execute(f'SELECT * FROM {history_table_name} WHERE date < date("now")')
    booking_history = cursor.fetchall()
    cursor.execute("SELECT room_name FROM Rooms_Information")
    room_data = cursor.fetchall()

    return templates.TemplateResponse("lk.html", {"request": request, "user_data": user_data,
                                                  "active_bookings": active_bookings,
                                                  "booking_history": booking_history, "room_data": room_data})


def access_permission(type_of_operation: str, login: str):
    """
    Функция для проверки наличия прав пользователя
    Функция презднзначена для того, чтобы проверить, может ли пользователь совершить данную операцию
    Args:
        type_of_operation:
        login:

    Returns:
    string = "Operation is allowed"
    """
    cursor.execute('SELECT pass_level FROM Users WHERE login = ?', (login,))
    role = cursor.fetchone()
    if type_of_operation in ("booking", "unnbooking") and role[0] < 'B':
        raise NotEnoughRights(status_code=404, detail="User hasn`t enough rights")
    elif type_of_operation in ("unnbooking other user", "adding room") and role[0] < 'C':
        raise NotEnoughRights(status_code=404, detail="User hasn`t enough rights")
    return "Operation is allowed"
