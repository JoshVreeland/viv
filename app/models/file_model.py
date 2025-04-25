from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func
import uuid
from app.database import Base

# ✅ Admin Table
class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FileRecord(Base):
    __tablename__ = "file_records"

    id          = Column(String, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    file_path   = Column(String, nullable=True)   # use String, not LargeBinary
    pdf_path    = Column(String, nullable=False)
    excel_path  = Column(String, nullable=False)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    uploader    = relationship("User", back_populates="files")
