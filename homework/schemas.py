from pydantic import BaseModel, ConfigDict



class BaseRecipe(BaseModel):
    name: str
    cook_time: int



class AddRecipe(BaseRecipe):
    description: str
    ingredients: str


class Recipes(BaseRecipe):
    id: int
    views: int

    model_config = ConfigDict(from_attributes=True)


class Recipe(Recipes):
    description: str
    ingredients: str

    model_config = ConfigDict(from_attributes=True)