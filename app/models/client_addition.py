from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class ClientAddition(Base):
    __tablename__ = "client_additions"

    id = Column(String, primary_key=True, index=True)
    admin_id = Column(String, ForeignKey("users.id"), nullable=False)
    client_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # optional backref
    admin = relationship("User", back_populates="client_additions")
