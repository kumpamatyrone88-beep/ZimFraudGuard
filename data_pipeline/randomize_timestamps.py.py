import random
from datetime import datetime, timedelta
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="ZIMFRAUDGUARD",
    user="postgres",
    password="MY_DATABASE_PASSWORD"
)
cursor = conn.cursor()

start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
total_seconds = int((end_date - start_date).total_seconds())

cursor.execute("SELECT transaction_id FROM transactions")
transaction_ids = cursor.fetchall()

for (tid,) in transaction_ids:
    random_seconds = random.randint(0, total_seconds)
    random_timestamp = start_date + timedelta(seconds=random_seconds)
    cursor.execute(
        "UPDATE transactions SET created_at = %s WHERE transaction_id = %s",
        (random_timestamp, tid)
    )

conn.commit()
cursor.close()
conn.close()
print("Done — timestamps updated")