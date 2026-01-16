import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from homework import models
from homework.database import Base, get_db
from homework.models import Recipe
from homework.routes import app

DATABASE_TEST_URL = "sqlite+aiosqlite:///./sql_test.db"

test_engine = create_async_engine(DATABASE_TEST_URL, echo=True)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def test_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db

    original_lifespan_context = app.router.lifespan_context
    app.router.lifespan_context = None

    yield

    app.router.lifespan_context = original_lifespan_context
    app.dependency_overrides = {}

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
async def data_base(test_session: AsyncSession):
    response = await test_session.execute(
        select(Recipe).order_by(Recipe.views.desc(), Recipe.cook_time)
    )
    result = response.scalars().all()

    yield len(result)


@pytest.fixture(scope="function")
async def add_recipe(test_session: AsyncSession):
    recipe_data = models.Recipe(
        name="Test Recipe 1",
        cook_time=30,
        description="Description 1",
        ingredients="Ingredients 1",
    )
    test_session.add(recipe_data)
    await test_session.commit()
    await test_session.refresh(recipe_data)
    created_item_id = recipe_data.id

    yield recipe_data

    item_to_delete = await test_session.get(Recipe, created_item_id)

    if item_to_delete:
        await test_session.delete(item_to_delete)
        await test_session.commit()


@pytest.mark.asyncio
async def test_get_all_recipes(client: AsyncClient, data_base):

    response = await client.get("/recipes/")

    assert response.status_code == 200
    assert len(response.json()) == data_base


@pytest.mark.asyncio
async def test_get_all_recipes_single(
    client: AsyncClient, add_recipe, test_session: AsyncSession
):
    response = await client.get("/recipes/")
    created_rec = await test_session.execute(
        select(models.Recipe).filter(Recipe.id == add_recipe.id)
    )
    created_recipe = created_rec.scalars().one()
    expected_object = [
        {
            "cook_time": created_recipe.cook_time,
            "id": created_recipe.id,
            "name": created_recipe.name,
            "views": created_recipe.views,
        }
    ]
    assert response.status_code == 200
    assert created_recipe
    assert expected_object == response.json()


@pytest.mark.asyncio
async def test_get_recipe_by_id_found(client: AsyncClient, add_recipe):

    response = await client.get(f"/recipe/{add_recipe.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Recipe 1"
    assert response.json()["description"] == "Description 1"
    assert response.json()["id"] == add_recipe.id
    assert response.json()["ingredients"] == "Ingredients 1"
    assert response.json()["cook_time"] == 30


@pytest.mark.asyncio
async def test_get_recipe_by_id_not_found(client: AsyncClient):
    non_existent_id = 999

    response = await client.get(f"/recipe/{non_existent_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Recipe not found"}


@pytest.mark.asyncio
async def test_create_recipe(client: AsyncClient):
    recipe_payload = {
        "name": "New Awesome Recipe",
        "cook_time": 45,
        "description": "A delicious new dish.",
        "ingredients": "[Ingredient A, Ingredient B]",
    }

    response = await client.post("/recipes", json=recipe_payload)

    assert response.status_code == 200
    response_data = response.json()

    assert response_data["name"] == recipe_payload["name"]
    assert response_data["cook_time"] == recipe_payload["cook_time"]
    assert response_data["description"] == recipe_payload["description"]
    assert response_data["ingredients"] == recipe_payload["ingredients"]
