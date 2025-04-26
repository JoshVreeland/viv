import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# 1) Grab your DATABASE_URL from env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in your shell before running")

# 2) Choose a new password
new_password = "Merizo123$"  # ← change this

# 3) Hash it
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash(new_password)

# 4) Connect and update
engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    conn.execute(
        text("""
            UPDATE users
            SET hashed_password = :hp,
                is_temp_password = true
            WHERE email = :em
        """),
        {"hp": hashed, "em": "merizoai.team@gmail.com"}
    )

print(f"✅ Password for merizoai.team@gmail.com reset to: {new_password}")

