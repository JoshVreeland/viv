from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin        = Column(Boolean, default=False, nullable=False)
    is_superadmin   = Column(Boolean, default=False, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)

    # Relationships
    client_additions = relationship(
        "ClientAddition",
        back_populates="admin",
        cascade="all, delete-orphan"
    )
    files = relationship(
        "FileRecord",
        back_populates="uploader",
        cascade="all, delete-orphan"
    )
