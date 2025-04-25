from app.database import SessionLocal
from app.models.file_model import Admin
from passlib.hash import bcrypt
import uuid

# === EDIT THIS SECTION ===
email = "merizoai.team@gmail.com"
password = "Joshvreeland28"

# === Hash password ===
hashed_password = bcrypt.hash(password)

# === Start DB session ===
db = SessionLocal()

# === Check if admin already exists ===
existing = db.query(Admin).filter(Admin.email == email).first()
if existing:
    print(f"⚠️ Admin with email '{email}' already exists.")
else:
    # === Create new admin ===
    new_admin = Admin(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        is_superadmin=True
    )
    db.add(new_admin)
    db.commit()
    db.close()
    print("✅ Admin created successfully!")
