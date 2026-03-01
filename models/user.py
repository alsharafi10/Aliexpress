from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10)) # Male/Female
    height = Column(Float)      # cm
    weight = Column(Float)      # kg
    age = Column(Integer)
    city = Column(String(50))   # Chinese city name
    body_type = Column(String(50)) # e.g. H-shape, O-shape, etc.
