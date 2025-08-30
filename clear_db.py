import sqlite3

conn = sqlite3.connect('bot.db')
cur = conn.cursor()

# List of tables to clear
for table in ['users', 'payments', 'posts']:
    cur.execute(f'DELETE FROM {table}')
    cur.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')  # Reset autoincrement

conn.commit()
conn.close()
print('All tables cleared.')
