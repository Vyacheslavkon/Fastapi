import os
from contextlib import asynccontextmanager
from typing import List, Sequence

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import ColumnElement
from starlette.staticfiles import StaticFiles

import homework.models
import homework.schemas
from homework.database import async_session, engine, get_db
from homework.models import Recipe

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
models = homework.models
schemas = homework.schemas


@asynccontextmanager
async def lifespan(
    application: FastAPI, eng=engine, session: AsyncSession = Depends(get_db)
):
    async with eng.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    yield

    await session.close()
    await eng.dispose()


app = FastAPI(lifespan=lambda app_instance: lifespan(app_instance, engine))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.post("/recipes", response_model=schemas.AddRecipe)
async def add_recipe(
    recipe: schemas.AddRecipe, session: AsyncSession = Depends(get_db)
) -> Recipe:
    new_recipe = models.Recipe(**recipe.model_dump())
    async with session.begin():
        session.add(new_recipe)
    return new_recipe


@app.get("/recipes/", response_model=List[schemas.Recipes])
async def recipes(session: AsyncSession = Depends(get_db)) -> Sequence[Recipe]:
    res = await session.execute(
        select(Recipe).order_by(Recipe.views.desc(), Recipe.cook_time)
    )

    return res.scalars().all()


@app.get("/recipe/{recipe_id}", response_model=schemas.Recipe)
async def recipe_one(recipe_id: int, session: AsyncSession = Depends(get_db)) -> Recipe:
    res = await session.execute(select(Recipe).filter(Recipe.id == recipe_id))
    recipe = res.scalars().one_or_none()

    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe.views += 1
    await session.commit()

    return recipe


@app.get("/table_recipes", response_class=HTMLResponse)
async def recipes_html(request: Request):
    recipe_s = []
    error_message = None

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            response = await client.get("/recipes/")
            response.raise_for_status()
            recipe_s = response.json()
            recipe_s = [schemas.Recipes(**recipe_data) for recipe_data in recipe_s]

    except httpx.RequestError as exc:
        error_message = f"Error in internal API request: {exc}"

    except httpx.HTTPStatusError as exc:
        error_message = f"The internal API returned an error: {exc.response.status_code} - {exc.response.text}"

    except Exception as exc:
        error_message = f"An unknown error occurred while processing recipes: {exc}"

    return templates.TemplateResponse(
        "table_recipes.html",
        {"request": request, "recipes": recipe_s, "error": error_message},
    )


@app.get("/recipe_details/{recipe_id}", response_class=HTMLResponse)
async def recipe_html(request: Request, recipe_id: int):
    error_message = None
    recipe = None
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            response = await client.get(f"/recipe/{recipe_id}")
            response.raise_for_status()
            recipe = response.json()
            recipe = schemas.Recipe(**recipe)

    except httpx.RequestError as exc:
        error_message = f"Error in internal API request: {exc}"

    except httpx.HTTPStatusError as exc:
        error_message = f"The internal API returned an error: {exc.response.status_code} - {exc.response.text}"

    except Exception as exc:
        error_message = f"An unknown error occurred while processing recipes: {exc}"

    return templates.TemplateResponse(
        "recipe_details.html",
        {"request": request, "recipe": recipe, "error": error_message},
    )
