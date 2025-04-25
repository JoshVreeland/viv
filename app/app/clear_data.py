# clear_data.py (place this alongside your `app/` folder)
from app.database import SessionLocal
from app.models.client_addition import ClientAddition
from app.models.file_model import FileRecord
from app.models.user_model import User

def main():
    db = SessionLocal()
    try:
        # delete in the correct order to satisfy foreign keys
        deleted_events = db.query(ClientAddition).delete()
        deleted_files  = db.query(FileRecord).delete()
        deleted_users  = db.query(User).delete()
        db.commit()
        print(f"Cleared {deleted_events} client_additions, "
              f"{deleted_files} file_records, and {deleted_users} users.")
    finally:
        db.close()

if __name__ == "__main__":
    main()

