from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./recipes.py.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as test_session:
         yield test_session