import mysql.connector
from mysql.connector import Error

passwords = ['', 'root', 'password', 'mysql', 'Dhanu@143', 'Dhanu143', 'dhanu@143', '123456', 'admin', 'root123']

for pwd in passwords:
    try:
        conn = mysql.connector.connect(host='localhost', user='root', password=pwd)
        print(f'SUCCESS with password: "{pwd}"')
        cursor = conn.cursor()
        cursor.execute('CREATE DATABASE IF NOT EXISTS ai_project')
        print('Database ai_project created/verified')
        conn.database = 'ai_project'
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('Users table created/verified')
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        print(f'Users count: {count}')
        conn.close()
        break
    except Error as e:
        pass
else:
    print('No common password worked')