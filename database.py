import os
import psycopg2
import urllib.parse as up
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from app import db

load_dotenv()

up.uses_netloc.append("postgres")
url = up.urlparse(os.getenv("DATABASE_URL"))

# Connect to database
try :
    conn = psycopg2.connect(database=url.path[1:],
                            user = url.username,
                            password= url.password,
                            host=url.hostname,
                            port=url.port)
    print(f"Connected to database: {url.path[1:]}")
except :
    print(f"Error connecting to database: {os.getenv('DATABASE_URL')}")


# Open a cursor to perform database operations
cur = conn.cursor()
def init_db():
    db.create_all()
    return True
   

# Execute a command: this creates a new table
# cur.execute('DROP TABLE IF EXISTS books;')

# cur.execute('DROP TABLE IF EXISTS users;')

# cur.execute('CREATE TABLE users (id serial PRIMARY KEY,'
#                                  'title varchar (150) NOT NULL,'
#                                  'author varchar (50) NOT NULL,'
#                                  'pages_num integer NOT NULL,'
#                                  'review text,'
#                                  'date_added date DEFAULT CURRENT_TIMESTAMP);'
#                                  )

# # Insert data into the table

# cur.execute('INSERT INTO books (title, author, pages_num, review)'
#             'VALUES (%s, %s, %s, %s)',
#             ('A Tale of Two Cities',
#              'Charles Dickens',
#              489,
#              'A great classic!')
#             )


# cur.execute('INSERT INTO books (title, author, pages_num, review)'
#             'VALUES (%s, %s, %s, %s)',
#             ('Anna Karenina',
#              'Leo Tolstoy',
#              864,
            #  'Another great classic!')
            # )

# conn.commit()

cur.close()
conn.close()