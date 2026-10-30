# koneksi.py
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()  # optional, kalau pakai .env

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "estruktical_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT,
            autocommit=True
        )
        return conn
    except Error as e:
        print("Error connecting to MySQL:", e)
        raise
    
if __name__ == "__main__":
    print("DB_HOST =", DB_HOST)
    print("DB_USER =", DB_USER)
    print("DB_PASS =", DB_PASS)
    print("DB_NAME =", DB_NAME)
    print("DB_PORT =", DB_PORT)
