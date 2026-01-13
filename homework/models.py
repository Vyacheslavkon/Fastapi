from sqlalchemy import Column, String, Integer, JSON
from homework.database import Base

class Recipe(Base):
    __tablename__ = 'Recipe'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cook_time = Column(Integer, index=True)
    description = Column(String)
    ingredients = Column(JSON)
    views = Column(Integer, index=True, default=0)


