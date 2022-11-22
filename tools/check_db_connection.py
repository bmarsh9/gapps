import psycopg2
import os

SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
def can_we_connect_to_postgres():
    try:
        connection = psycopg2.connect(SQLALCHEMY_DATABASE_URI)
        connection.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}".strip())
        return False

print(f"[INFO] Checking if we can connect to the database server: {SQLALCHEMY_DATABASE_URI}")
if not can_we_connect_to_postgres():
    print(f"[ERROR] Unable to connect to the database server")
    exit(1)
print(f"[INFO] Successfully connected to the database server")
exit(0)
