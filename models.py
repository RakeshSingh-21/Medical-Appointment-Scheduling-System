from sqlalchemy import Column, Integer, String, ForeignKey, Time, Date,Boolean
from sqlalchemy.orm import relationship
from database import Base

#User Model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    email = Column(String(20), unique=True, index=True)
    password_hash = Column(String(50))
    role = Column(Boolean, nullable=False)
    
    