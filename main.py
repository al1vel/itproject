from fastapi import FastAPI
import sqlite3

connection = sqlite3.connect('my_database.db', check_same_thread=False)
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
room_name TEXT NOT NULL,
Information TEXT NOT NULL
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

app = FastAPI()


@app.get("/")
async def root():
    return "MAIN PAGE"


@app.post("/book")
def book(user: str, room_name: str, date: str, time_from: str, time_to: str):
    cursor.execute(f'INSERT INTO History_of_Operations (room_name, type_of_operation, booker, date, time_from, time_to)'
                   f' VALUES ("{room_name}", "booked", "{user}", "{date}", "{time_from}", "{time_to}")')


@app.get("/get_info")
def get_info(room_name: str):
    cursor.execute(f'SELECT Information FROM Rooms_information WHERE room_name = "{room_name}"')
    res = cursor.fetchall()
    return res


@app.get("/check")
def check(user: str):
    cursor.execute(f'SELECT * FROM History_of_Operations WHERE booker = "{user}"')
    res = cursor.fetchall()
    return res


def split_time_gaps(res, data):
    for booking in data:
        r_name = booking[0]
        temp1 = booking[1].split(":")
        time_from = int(temp1[0]) * 60 + int(temp1[1])
        temp2 = booking[2].split(":")
        time_to = int(temp2[0]) * 60 + int(temp2[1])

        current_gaps = res[r_name]
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
        res[r_name] = current_gaps
        return res


def format_time_to_string(res):
    for room in res.keys():
        temp = res[room]
        new = []
        for item in temp:
            time = (f'{item[0] // 60}:{item[0] % 60 if (item[0] % 60) != 0 else "00"} - {item[1] // 60}:'
                    f'{item[1] % 60 if (item[1] % 60) != 0 else "00"}')
            new.append(time)
        res[room] = new
    return res


@app.get("/freerooms")
def get_free_rooms(date: str):
    cursor.execute(f'SELECT room_name FROM Rooms_Information')
    all_room_names = cursor.fetchall()
    cursor.execute(f'SELECT room_name, time_from, time_to FROM History_of_Operations WHERE date = "{date}"')
    data = cursor.fetchall()

    res = dict()
    for r_name in all_room_names:
        res[r_name[0]] = [[540, 1080], ]
    split_time_gaps(res, data)
    format_time_to_string(res)
    return res


@app.post("/add_room")
def add_room(room_name: str, inf: str):
    cursor.execute(f'INSERT INTO Rooms_Information (room_name, Information) VALUES ("{room_name}", "{inf}")')


@app.get("/free_room")
def get_when_room_is_free(date: str, room_name: str):
    cursor.execute(f'SELECT room_name, time_from, time_to FROM History_of_Operations WHERE date = "{date}" AND '
                   f'room_name = "{room_name}"')
    data = cursor.fetchall()
    res = dict()
    res[room_name] = [[540, 1080], ]
    split_time_gaps(res, data)
    format_time_to_string(res)
    return res


print('test')
