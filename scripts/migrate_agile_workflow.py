import os
from sqlalchemy import text
from app.database import engine

def run_migration():
    print("Starting Agile Workflow schema migration...")
    
    # Use isolation_level="AUTOCOMMIT" for ALTER TYPE statements
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # 1. Update workflowstate enum
        for val in ['REPORTED', 'TRIAGED', 'QA_VERIFICATION']:
            try:
                conn.execute(text(f"ALTER TYPE workflowstate ADD VALUE IF NOT EXISTS '{val}';"))
                print(f"Added '{val}' to workflowstate enum")
            except Exception as e:
                print(f"Notice on workflowstate {val}: {e}")

        # 2. Update issuepriority enum
        try:
            conn.execute(text("ALTER TYPE issuepriority ADD VALUE IF NOT EXISTS 'URGENT';"))
            print("Added 'URGENT' to issuepriority enum")
        except Exception as e:
            print(f"Notice on issuepriority URGENT: {e}")

        # 3. Update issueseverity enum
        for val in ['MAJOR', 'MINOR', 'TRIVIAL']:
            try:
                conn.execute(text(f"ALTER TYPE issueseverity ADD VALUE IF NOT EXISTS '{val}';"))
                print(f"Added '{val}' to issueseverity enum")
            except Exception as e:
                print(f"Notice on issueseverity {val}: {e}")

    # Now standard DDL in transaction block
    with engine.begin() as conn:
        # 4. User skills column
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS skills VARCHAR(500) DEFAULT NULL;
        """))
        print("Ensured users.skills column exists")

        # 5. Create sprints table
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE sprintstatus AS ENUM ('PLANNING', 'ACTIVE', 'COMPLETED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sprints (
                id SERIAL PRIMARY KEY,
                project_id INT REFERENCES projects(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                goal VARCHAR(500),
                start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP WITH TIME ZONE,
                status sprintstatus DEFAULT 'ACTIVE' NOT NULL,
                velocity INT DEFAULT 0 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        print("Ensured sprints table exists")

        # 6. Add sprint_id, category, priority_score to issues
        conn.execute(text("""
            ALTER TABLE issues 
            ADD COLUMN IF NOT EXISTS sprint_id INT REFERENCES sprints(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'General',
            ADD COLUMN IF NOT EXISTS priority_score FLOAT DEFAULT NULL;
        """))
        print("Ensured issues columns (sprint_id, category, priority_score) exist")

        # 7. Create comments table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                issue_id INT REFERENCES issues(id) ON DELETE CASCADE NOT NULL,
                user_id INT REFERENCES users(id) ON DELETE SET NULL,
                content VARCHAR(2000) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        print("Ensured comments table exists")

        # 8. Create attachments table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                issue_id INT REFERENCES issues(id) ON DELETE CASCADE NOT NULL,
                user_id INT REFERENCES users(id) ON DELETE SET NULL,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_type VARCHAR(100),
                file_size INT DEFAULT 0,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        print("Ensured attachments table exists")

        # 9. Create depart and students tables requested by user
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS depart (
                dept_id SERIAL PRIMARY KEY,
                dept_name VARCHAR(50) NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                student_id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE,
                enrollment_date DATE DEFAULT CURRENT_DATE,
                dept_id INT REFERENCES depart(dept_id) ON DELETE SET NULL
            );
        """))
        print("Ensured depart and students tables exist")

    print("Agile Workflow migration completed successfully!")

if __name__ == "__main__":
    run_migration()
