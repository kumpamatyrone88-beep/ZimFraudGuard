import psycopg2
from sqlalchemy import create_engine


DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "ZIMFRAUDGUARD"
DB_USER = "postgres"
DB_PASSWORD = "MY_DATABASE_PASSWORD"


def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


def get_engine():
    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    return engine


# Test the connection
if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"✅ Connected successfully to: {db_name}")

        cursor.execute("SELECT COUNT(*) FROM locations;")
        count = cursor.fetchone()[0]
        print(f"✅ Locations in database: {count}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")