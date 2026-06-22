from django.urls import path
from .views import IngredientListView, IngredientCreateView, RecipeListView, manage_recipe_view

app_name = 'recipes'

urlpatterns = [
    path('ingredients/', IngredientListView.as_view(), name='ingredient_list'),
    path('ingredients/create/', IngredientCreateView.as_view(), name='ingredient_create'),
    path('', RecipeListView.as_view(), name='recipe_list'),
    path('create/', manage_recipe_view, name='recipe_create'),
    path('<int:pk>/edit/', manage_recipe_view, name='recipe_edit'),
]