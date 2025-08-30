import sqlite3

conn = sqlite3.connect('bot.db')
cur = conn.cursor()

cur.execute("SELECT user_id, username, role FROM users")
rows = cur.fetchall()

print(f"Total users: {len(rows)}")
for user_id, username, role in rows:
    print(f"User ID: {user_id}, Username: {username}, Role: {role}")

def print_table(name):
    print(f'\nTable: {name}')
    cur.execute(f'PRAGMA table_info({name})')
    columns = [col[1] for col in cur.fetchall()]
    print(' | '.join(columns))
    cur.execute(f'SELECT * FROM {name}')
    for row in cur.fetchall():
        print(' | '.join(str(x) for x in row))

tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for (table_name,) in tables:
    print_table(table_name)

conn.close()