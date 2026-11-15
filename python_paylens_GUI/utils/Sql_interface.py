import pyodbc
from config import load_settings

def create_sql_connection():
    settings = load_settings()
    connection_string = settings.sql_connection_string
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    return cursor