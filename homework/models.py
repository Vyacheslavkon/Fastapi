from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from homework.database import Base


class Recipe(Base):
    __tablename__ = "Recipe"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    cook_time: Mapped[int] = mapped_column(index=True)
    description: Mapped[str] = mapped_column()
    ingredients: Mapped[JSON] = mapped_column()
    views: Mapped[int] = mapped_column(index=True, default=0)
