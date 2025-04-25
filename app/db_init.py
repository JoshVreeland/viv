from app.database import Base, engine
# Make sure to import your models so they get registered on Base
from app.models.user_model import User
from app.models.file_model import FileRecord
from app.models.client_addition import ClientAddition


def init_db():
    Base.metadata.create_all(bind=engine)
