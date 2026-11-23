"""
Web URL routes for Accounts (mounted at /accounts/).
Owned by Developer 1.
"""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("addresses/", views.address_list_create_view, name="addresses"),
    path("addresses/<int:pk>/edit/", views.address_edit_view, name="address-edit"),
    path("addresses/<int:pk>/delete/", views.address_delete_view, name="address-delete"),
    path(
        "addresses/<int:pk>/set-default/",
        views.address_set_default_view,
        name="address-set-default",
    ),
]
