"""
Web URL routes for Menu (mounted at /menu/).
Owned by Developer 1.
"""
from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("", views.menu_list_view, name="menu-list"),
    path("categories/<slug:slug>/", views.category_detail_view, name="category-detail"),
    path("items/<slug:slug>/", views.food_item_detail_view, name="food-detail"),
    path(
        "manage/items/<slug:slug>/toggle-availability/",
        views.staff_toggle_availability_view,
        name="toggle-availability",
    ),
]
