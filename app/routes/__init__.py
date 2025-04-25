from app.database import engine, Base
from app.models import user_model  # ⬅️ import all models here

def init_db():
    Base.metadata.create_all(bind=engine)
