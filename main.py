import datetime
import sqlite3
import matplotlib.pyplot as plt
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


class TooManyParticipants(HTTPException):
    pass


class ThisTimeHasAlreadyBeenBooked(HTTPException):
    pass


class ThereIsNoNecessaryEquipment(HTTPException):
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


class BookingCancellation(BaseModel):
    login: str
    room_name: str
    date: str
    time_from: str
    time_to: str


@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/book")
async def book(
    login: str = Form(...),
    room_name: str = Form(...),
    date: str = Form(...),
    time_from: str = Form(...),
    time_to: str = Form(...),
    number_of_participants: int = Form(...),
):
    try:
        access_permission("booking", login)
        capacity_check(room_name, number_of_participants)
        the_list_of_free_time = get_free_gaps_for_one_room(date, room_name)[room_name]
        time_check(the_list_of_free_time, time_from, time_to)
    except NotEnoughRights:
        print("This User doesn't have enough rights")
        return "This User doesn't have enough rights"
    except TooManyParticipants:
        print("Too many participants")
        return "Too many participants"
    except ThisTimeHasAlreadyBeenBooked:
        print("The meeting room is occupied at this time")
        return "The meeting room is occupied at this time"
    except ThereIsNoNecessaryEquipment:
        print("There is no necessary equipment")
        return "There is no necessary equipment"
    cursor.execute(
        f'INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, time_to)'
        f' VALUES ("{room_name}", "booking", "{login}", "{date}", "{time_from}", "{time_to}")'
    )
    return "The room has been successfully booked"


def capacity_check(room_name, number_of_participants):
    """
    Функция для проверки вместимости.

    Функция сравнивает вместимость комнаты с количеством поданных человек

    Args:
        room_name:  string
        number_of_participants: int
    Returns:
        nothing
    """
    cursor.execute(f'SELECT capacity FROM Rooms_Information WHERE room_name = "{room_name}"')
    capacity = cursor.fetchall()
    if capacity[0][0] < number_of_participants:
        raise TooManyParticipants(status_code=400, detail="Too many participants")


def time_check(the_list_of_free_time, time_from, time_to):
    """
    Функция для проверки времени.

    Функция проверяет свободна ли комната в поданный определённый промежуток времени

    Args:
        the_list_of_free_time: list
        time_from: string
        time_to: string
    Returns:
        nothing
    """
    fl = 0
    for time in the_list_of_free_time:
        time = time.replace(' ', '').replace('-', ' ').replace(':', ' ')
        hours_from_free, min_from_free, hours_to_free, min_to_free = map(int, time.split())
        hours_from, min_from = map(int, time_from.split(':'))
        hours_to, min_to = map(int, time_to.split(':'))
        if hours_from_free > hours_from or hours_to_free < hours_to:
            continue
        elif hours_from_free == hours_from and min_from_free > min_from:
            continue
        elif hours_to_free == hours_to and min_to_free < min_to:
            continue
        fl = 1
        break
    if fl == 0:
        raise ThisTimeHasAlreadyBeenBooked(status_code=400, detail="This time has already been booked")


@app.delete("/user_info")
async def unnbook(login: str, room_name: str, date: str, time_from: str, time_to: str):
    """
    Функция API для отмены бронирования комнаты.
    Функция удаляет бронь комнаты из базы данных в таблице "История операций".
    Args:
        login: string
        room_name:  string
        date: string in format **.**.****
        time_from: string in format **:**
        time_to: string in format **:**
    Returns:
        JSON response
    """
    cursor.execute('''
        SELECT type_of_operation FROM History_of_Operations 
        WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
    ''', (room_name, date, time_from, time_to))
    type_op = cursor.fetchall()

    if type_op:
        if type_op[0][0] != "booking":
            return {"message": "Unsupportable for this operation"}
    else:
        return {"message": "No records found"}

    try:
        cursor.execute('''
            SELECT booker FROM History_of_Operations 
            WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
        ''', (room_name, date, time_from, time_to))
        booker = cursor.fetchall()

        if login == booker[0][0]:
            access_permission("unbooking", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return {"message": "This User hasn`t enough rights"}

    cursor.execute('''
        DELETE FROM History_of_Operations 
        WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
    ''', (room_name, date, time_from, time_to))
    cursor.execute(f'INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, time_to)'
                   f' VALUES ("{room_name}", "unbooking", "{login}", "{date}", "{time_from}", "{time_to}")')

    return {"message": "Booking successfully cancelled"}


@app.delete("/all_history")
async def unbook(login: str, room_name: str, date: str, time_from: str, time_to: str):
    """
    Функция API для отмены бронирования комнаты.
    Функция удаляет бронь комнаты из базы данных в таблице "История операций".
    Args:
        login: string
        room_name:  string
        date: string in format **.**.****
        time_from: string in format **:**
        time_to: string in format **:**
    Returns:
        JSON response
    """
    cursor.execute('''
        SELECT type_of_operation FROM History_of_Operations 
        WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
    ''', (room_name, date, time_from, time_to))
    type_op = cursor.fetchall()

    if type_op:
        if type_op[0][0] != "booking":
            return {"message": "Unsupportable for this operation"}
    else:
        return {"message": "No records found"}

    try:
        cursor.execute('''
            SELECT booker FROM History_of_Operations 
            WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
        ''', (room_name, date, time_from, time_to))
        booker = cursor.fetchall()

        if login == booker[0][0]:
            access_permission("unbooking", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return {"message": "This User hasn`t enough rights"}

    cursor.execute('''
        DELETE FROM History_of_Operations 
        WHERE room_name = ? AND date = ? AND time_from = ? AND time_to = ?
    ''', (room_name, date, time_from, time_to))

    return {"message": "Booking successfully cancelled"}


@app.get("/all_history", response_class=HTMLResponse)
def all_history(request: Request, login: str):
    """
    Функция для визуализации истории операций.

    Функция возвращает все данные из таблицы History_of_Operations.

    Args:
        request:
        login: string

    Returns:
        list of values tuple = (operation id = integer, room name = string, type of operation = string, booker = string,
         date = string, time from = string, time to = string)
    """
    try:
        access_permission("check all history", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return "This User hasn`t enough rights"
    cursor.execute("SELECT * FROM History_of_Operations WHERE type_of_operation = 'booking'")
    history_data = cursor.fetchall()
    cursor.execute("SELECT room_name FROM Rooms_Information")
    room_data = cursor.fetchall()
    return templates.TemplateResponse("levelC.html",
                                      {"request": request, "history_data": history_data, "room_data": room_data})


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
        "eq_proj": room_info[3],
        "eq_board": room_info[4],
        "description": room_info[5],
        "room_image": room_info[6],
        "location": room_info[7]
    }
    return templates.TemplateResponse("room.html", {"request": request, **room_data})


@app.post("/search")
async def search_rooms(request: str, date: str):
    """
    Функция для поиска комнат.

    Функция получает комнаты, в которых встречается введенный запрос, а также незанятые промежутки времени
     на выбранную дату.

    Args:
        request: string
        date: string(**.**.****)

    Returns:
        dict, key = room name, value = array of free gaps in minutes (int)
    """
    cursor.execute("SELECT room_name FROM Rooms_information")
    rooms = cursor.fetchall()
    result = {}
    for room in rooms:
        if request in room[0]:
            result |= get_free_gaps_for_one_room(date, room[0])
    return result


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


def conjunction_of_list(*lists):
    res = []
    for ls in lists:
        for el in ls:
            flag = 1
            for list1 in lists:
                if el not in list1:
                    flag = 0
            if flag == 1:
                res.append(el)
    res = set(res)
    return list(res)


@app.post("/filters")
def filter_rooms(capacity=0, location=None, eq_proj=None, eq_board=None):
    """
    Функция для фильтрации переговорных комнат
    Args:
        capacity:
        location:
        eq_proj:
        eq_board:

    Returns:

    """
    cursor.execute(f'SELECT room_name FROM Rooms_Information WHERE capacity >= "{capacity}"')
    cap_names = cursor.fetchall()

    if location is not None:
        cursor.execute(f'SELECT room_name FROM Rooms_Information WHERE location = "{location}"')
        loc_names = cursor.fetchall()
    else:
        cursor.execute(f'SELECT room_name FROM Rooms_Information')
        loc_names = cursor.fetchall()

    if eq_proj is not None:
        if eq_proj == "NO":
            cursor.execute(f'SELECT room_name FROM Rooms_Information')
            eq_pr_names = cursor.fetchall()
        else:
            cursor.execute(f'SELECT room_name FROM Rooms_Information WHERE eq_proj = "{eq_proj}"')
            eq_pr_names = cursor.fetchall()
    else:
        cursor.execute(f'SELECT room_name FROM Rooms_Information')
        eq_pr_names = cursor.fetchall()

    if eq_board is not None:
        if eq_board == "NO":
            cursor.execute(f'SELECT room_name FROM Rooms_Information')
            eq_b_names = cursor.fetchall()
        else:
            cursor.execute(f'SELECT room_name FROM Rooms_Information WHERE eq_board = "{eq_board}"')
            eq_b_names = cursor.fetchall()
    else:
        cursor.execute(f'SELECT room_name FROM Rooms_Information')
        eq_b_names = cursor.fetchall()
    capacity_names = [el[0] for el in cap_names]
    location_names = [el[0] for el in loc_names]
    eq_proj_names = [el[0] for el in eq_pr_names]
    eq_board_names = [el[0] for el in eq_b_names]
    all_room_names = conjunction_of_list(capacity_names, location_names, eq_proj_names, eq_board_names)
    return all_room_names


@app.get("/free_gaps")
def get_free_gaps_for_rooms(date: str, capacity=0, location=None, eq_proj=None, eq_board=None):
    """
    Функция API для получения свободных окон для всех комнат на конкретную дату

    Функция совершает запрос в базу для получения всех броней на конкретную дату для всех комнаты. Затем помечает
    эти промежутки недоступными, возвращая словарь, где ключами является названия комнат, а значениями - массивы строк,
    каждая из которых содержит свободный временной промежуток.

    Args:
        date: string
        capacity: int
        location: string
        eq_proj: string
        eq_board: string
    Returns:
        dict, keys = room names, values = array of strings ["**:** - **:**, ...]
    """

    all_room_names = filter_rooms(capacity, location, eq_proj, eq_board)
    print(all_room_names)
    if len(all_room_names) > 0:
        cursor.execute(f'SELECT room_name, time_from, time_to FROM History_of_Operations WHERE date = "{date}" AND'
                       f' type_of_operation = "booking"')
        all_bookings = cursor.fetchall()

        current_bookings = [booking for booking in all_bookings if booking[0] in all_room_names]

        free_gaps = dict()
        for r_name in all_room_names:
            free_gaps[r_name] = [[540, 1080], ]
        split_time_gaps(free_gaps, current_bookings)
        format_time_to_string(free_gaps)
        return free_gaps
    else:
        return "NO SUCH ROOM"


@app.post("/add_room")
def add_room(room_name: str, login: str, area: float, capacity: int, inf: str, img: str, loc: str, eq_proj="NO",
             eq_board="NO"):
    """
    Функция API, добавляющая новую комнату

    Args:
        room_name: string
        area: float
        capacity: int
        inf: string. Contains description of the room
        img: string. Contains link to image
        loc: string. Location of the room
        eq_proj: "YES" or "NO" if projector exists or not
        eq_board: "YES" or "NO" if board exists or not
        login: string

    Returns:ф
        nothing
    """
    try:
        access_permission("adding room", login)
    except NotEnoughRights:
        print("This User hasn`t enough rights")
        return "This User hasn`t enough rights"
    cursor.execute(f'INSERT INTO Rooms_Information (room_name, area, capacity, description, room_image, '
                   f'location, eq_proj, eq_board) VALUES ("{room_name}", "{area}", "{capacity}", "{inf}", "{img}", '
                   f'"{loc}", "{eq_proj}", "{eq_board}")')


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
                   f'room_name = "{room_name}" AND type_of_operation = "booking"')
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
    # Список для хранения сообщений об ошибках
    errors = []
    # Проверки данных
    if len(password) < 8:
        errors.append("Пароль должен содержать не менее 8 символов")
    if not any(char.isdigit() for char in password):
        errors.append("Пароль должен содержать хотя бы одну цифру")
    if not any(char.isalpha() for char in password):
        errors.append("Пароль должен содержать хотя бы одну букву")
    if not any(char in "!@#$%^&*()-_+=<>?/.,:;" for char in password):
        errors.append("Пароль должен содержать хотя бы один специальный символ: "
                      "!@#$%^&*()-_+=<>?/.,:;")
    if password != doublepassword:
        errors.append("Пароли не совпадают")

    # Если есть ошибки, возвращаем страницу регистрации с сообщениями об ошибках
    if errors:
        return templates.TemplateResponse("register.html", {"request": request, "errors": errors})

    # Проверка наличия пользователя с таким же email в базе данных
    cursor.execute('SELECT * FROM Users WHERE email = ?', (email,))
    existing_user = cursor.fetchone()
    if existing_user:
        errors.append("Пользователь с таким адресом электронной почты уже зарегистрирован")
        return templates.TemplateResponse("register.html", {"request": request, "errors": errors})

    # Проверка наличия пользователя с таким же логином в базе данных
    cursor.execute('SELECT * FROM Users WHERE login = ?', (login,))
    existing_login = cursor.fetchone()
    if existing_login:
        errors.append("Пользователь с таким логином уже зарегистрирован")
        return templates.TemplateResponse("register.html", {"request": request, "errors": errors})

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
        errors = ["Неправильный логин или пароль"]
        return templates.TemplateResponse("login.html", {"request": request, "errors": errors})
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/user_info", response_class=HTMLResponse)
async def get_user_info(request: Request, login: str):
    cursor.execute('SELECT * FROM Users WHERE login = ?', (login,))
    user_data = cursor.fetchone()
    if user_data is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    active_bookings = []
    booking_history = []
    cur_date = datetime.datetime.now().strftime("%d.%m.%Y")
    cur_day = cur_date.split(".")[0]
    cur_mon = cur_date.split(".")[1]
    cur_year = cur_date.split(".")[2]
    cursor.execute(f'''
        SELECT * FROM History_of_Operations 
        WHERE booker = ? AND type_of_operation = ?
    ''', (login, 'booking'))
    bookings = cursor.fetchall()

    for booking in bookings:
        book_date = booking[4]
        book_day, book_mon, book_year = book_date.split(".")
        if cur_year > book_year:
            booking_history.append(booking)
        elif cur_year == book_year:
            if cur_mon > book_mon:
                booking_history.append(booking)
            elif cur_mon == book_mon:
                if cur_day > book_day:
                    booking_history.append(booking)
                else:
                    active_bookings.append(booking)
            else:
                active_bookings.append(booking)
        else:
            active_bookings.append(booking)

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
    print(role)
    if type_of_operation in ("booking", "unbooking") and role[0] < 'B':
        raise NotEnoughRights(status_code=404, detail="User hasn`t enough rights")
    elif type_of_operation in ("unbooking other user", "adding room") and role[0] < 'C':
        raise NotEnoughRights(status_code=404, detail="User hasn`t enough rights")
    return "Operation is allowed"


@app.post("/get_info", response_class=HTMLResponse)
async def show_graphics(request: Request, month: str, room_name: str):
    months = {"January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06", "July": "07",
              "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"}
    cur_mon = months[month]

    if int(cur_mon) == 2:
        x = [i for i in range(1, 30)]
    elif int(cur_mon) % 2 == 0:
        x = [i for i in range(1, 31)]
    else:
        x = [i for i in range(1, 32)]

    y = []
    for day in range(1, len(x) + 1):
        s = str(day)
        if len(s) == 1:
            cur_day = f'0{s}.{cur_mon}.2024'
        elif len(s) == 2:
            cur_day = f'{s}.{cur_mon}.2024'
        else:
            print("TROUBLE")

        gaps = get_free_gaps_for_one_room(cur_day, room_name)[room_name]
        free_time = 0
        for time in gaps:
            time_from = time.split("-")[0]
            time_to = time.split("-")[1]
            time_from_int = int(time_from.split(":")[0]) * 60 + int(time_from.split(":")[1])
            time_to_int = int(time_to.split(":")[0]) * 60 + int(time_to.split(":")[1])
            free_time += time_to_int - time_from_int
        book_time = 540 - free_time
        percent = round((book_time / 540) * 100)
        y.append(percent)
    # Создаем график
    plt.bar(x, y, label='Занятость')
    plt.xlabel('День')
    plt.ylabel('Занятость')
    plt.title('Занятость комнаты на протяжении месяца')
    plt.legend()

    plt.savefig("templates/static/xd.png")
    plt.close()
    return templates.TemplateResponse("room.html", {"request": request, "graph_image": "xd.png"})


@app.get("/main_page", response_class=HTMLResponse)
async def booking_recommendation(request: Request, login: str, date: str = None):
    """
    Функция для рекомендации комнат по предыдущим бронированиям.

    Функция проверяет сколько раз пользователь бронировал определённую комнату, вычисляет среднее время бронирований и
     проверяет свободна ли данная комната в этот промежуток времени. Если все условия выполнены, комната и окна,
     в которые она свободна, запоминаются в переменную recommended_rooms. Максимум рекомендуется 3 комнаты.

    Args:
        request:
        login: string
        date: string (**.**.****)

    Returns:
        dict, keys = room names, values = array of strings ["**:** - **:**, ...]
    """
    if date is None:
        date = datetime.now().strftime("%d.%m.%Y")
    cursor.execute('SELECT room_name, time_from, time_to FROM History_of_Operations WHERE booker = ?'
                   ' AND type_of_operation = ?', (login, "booking"))
    info = cursor.fetchall()
    stats = {}
    for operation in info:
        if operation[0] in stats.keys():
            stats[operation[0]]["cnt"] += 1
            stats[operation[0]]["time_from"].append(list(map(int, operation[1].split(':'))))
            stats[operation[0]]["time_to"].append(list(map(int, operation[2].split(':'))))
        else:
            stats[operation[0]] = {"cnt": 1, "time_from": [list(map(int, operation[1].split(':')))],
                                   "time_to": [list(map(int, operation[2].split(':')))]}
    stats = dict(sorted(stats.items()))
    recommended_rooms = {}
    for room in stats.keys():
        free_time = get_free_gaps_for_one_room(date, room)[room]
        cnt = stats[room]["cnt"]
        time_from = sum([i[0] * 60 + i[1] for i in stats[room]["time_from"]]) // cnt
        time_to = sum([i[0] * 60 + i[1] for i in stats[room]["time_to"]]) // cnt
        time_from_str = str(time_from // 60) + ':' + str(time_from % 60)
        time_to_str = str(time_to // 60) + ':' + str(time_to % 60)
        try:
            time_check(free_time, time_from_str, time_to_str)
        except ThisTimeHasAlreadyBeenBooked:
            continue
        recommended_rooms[room] = free_time
        if len(recommended_rooms) == 3:
            break
        cursor.execute('SELECT DISTINCT location FROM Rooms_Information')
        locations = cursor.fetchall()
        location_options = [loc[0] for loc in locations]
        cursor.execute("SELECT room_name FROM Rooms_Information")
        room_data = cursor.fetchall()
    return templates.TemplateResponse("main_page.html",
                                      {"request": request, "login": login, "recommended_rooms": recommended_rooms,
                                       "location_options": location_options, "room_data": room_data})


@app.get("/notifications")
async def notifications(login: str):
    today = datetime.date.today()
    d = str(today).split("-")
    cur_day = d[2]
    cur_mon = d[1]
    cur_year = d[0]

    cursor.execute(f'SELECT room_name, date, time_from, time_to FROM History_of_Operations WHERE booker = "{login}" '
                   f'AND type_of_operation = "booking"')
    bookings = cursor.fetchall()

    nfs = []
    for booking in bookings:
        r_name = booking[0]
        b_date = booking[1]
        time_from = booking[2]
        time_to = booking[3]

        b_day = booking[1].split(".")[0]
        b_month = booking[1].split(".")[1]
        b_year = booking[1].split(".")[2]
        if (0 <= (int(b_day) - int(cur_day)) <= 2) and (cur_mon == b_month) and (cur_year == b_year):
            notif = f'You have booked room {r_name} from {time_from} to {time_to} on {b_date}'
            nfs.append(notif)
    return nfs
