"""
JSON API URL routes for Menu (mounted at /api/menu/).
Owned by Developer 1.
"""
from django.urls import path

from . import api_views

app_name = "menu-api"

urlpatterns = [
    path("categories/", api_views.CategoryListCreateAPIView.as_view(), name="category-list"),
    path(
        "categories/<slug:slug>/",
        api_views.CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),
    path("items/", api_views.FoodItemListCreateAPIView.as_view(), name="fooditem-list"),
    path(
        "items/<slug:slug>/",
        api_views.FoodItemDetailAPIView.as_view(),
        name="fooditem-detail",
    ),
    path(
        "items/<slug:slug>/toggle-availability/",
        api_views.ToggleFoodAvailabilityAPIView.as_view(),
        name="fooditem-toggle-availability",
    ),
    path("featured/", api_views.FeaturedFoodItemsAPIView.as_view(), name="featured-items"),
]
