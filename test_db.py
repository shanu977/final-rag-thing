import sqlite3
conn = sqlite3.connect(r'C:\Users\pilli\Downloads\rag system\Rag-system\instance\app.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check users
cursor.execute('SELECT COUNT(*) FROM users')
print('Users count:', cursor.fetchone()[0])

# Check if chat tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'chat_%'")
chat_tables = cursor.fetchall()
print('Chat tables:', [t[0] for t in chat_tables])

conn.close()