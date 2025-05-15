import mysql.connector
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

class Database:
    def __init__(self):
        self.connection_config = {
            'host': os.getenv("DB_HOST"),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD"),
            'database': os.getenv("DB_NAME")
        }
    
    @contextmanager
    def get_connection(self):
        connection = mysql.connector.connect(**self.connection_config)
        try:
            yield connection
        finally:
            connection.close()
    
    @contextmanager
    def get_cursor(self, dictionary=False):
        with self.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary)
            try:
                yield cursor, connection
            finally:
                # Make sure all results are consumed before closing
                try:
                    if cursor.with_rows:
                        cursor.fetchall()
                except:
                    pass
                cursor.close()

db = Database()