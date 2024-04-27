from fastapi import FastAPI
import sqlite3

connection = sqlite3.connect('my_database.db')
cursor = connection.cursor()

app = FastAPI()


@app.get("/")
async def root():
    return "POHUI"


@app.post("/book/")
def book(user: str, room_name: str, date: str, time_from: int, time_to: int):
    cursor.execute(f'INSERT INTO History_of_Operations (room_id, type_of_operation, booker, date, time_from, time_to)'
                   f' VALUES ({room_name}, booked, {user}, {date}, {time_from}, {time_to})')
