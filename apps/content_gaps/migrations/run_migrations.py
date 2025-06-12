import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migrations():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return

    # Parse database URL
    # Format: postgresql://username:password@host:port/database
    db_parts = database_url.split('/')
    db_name = db_parts[-1]
    db_connection = '/'.join(db_parts[:-1])

    try:
        # Connect to default database to create new database if it doesn't exist
        conn = psycopg2.connect(db_connection)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database: {db_name}")
            cur.execute(f'CREATE DATABASE {db_name}')
        
        cur.close()
        conn.close()

        # Connect to the target database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Read and execute migration files
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        for migration_file in migration_files:
            print(f"Running migration: {migration_file}")
            with open(os.path.join(migrations_dir, migration_file)) as f:
                sql = f.read()
                cur.execute(sql)
        
        conn.commit()
        print("Migrations completed successfully")

    except Exception as e:
        print(f"Error running migrations: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    run_migrations() 