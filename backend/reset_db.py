import psycopg
from psycopg import sql

# Connect to 'postgres' database to drop 'fusionems'
conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/postgres", autocommit=True)
cur = conn.cursor()

# Terminate existing connections
cur.execute(sql.SQL("""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'fusionems'
    AND pid <> pg_backend_pid();
"""))

# Drop and Recreate
cur.execute("DROP DATABASE IF EXISTS fusionems")
cur.execute("CREATE DATABASE fusionems")
print("Database fusionems reset successfully.")

conn.close()
