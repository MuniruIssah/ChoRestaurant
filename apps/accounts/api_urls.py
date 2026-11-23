"""
JSON API URL routes for Accounts (mounted at /api/accounts/).
Owned by Developer 1.
"""
from django.urls import path

from . import api_views

app_name = "accounts-api"

urlpatterns = [
    path("register/", api_views.RegisterAPIView.as_view(), name="register"),
    path("login/", api_views.LoginAPIView.as_view(), name="login"),
    path("logout/", api_views.LogoutAPIView.as_view(), name="logout"),
    path("change-password/", api_views.PasswordChangeAPIView.as_view(), name="change-password"),
    path("profile/", api_views.ProfileAPIView.as_view(), name="profile"),
    path("addresses/", api_views.AddressListCreateAPIView.as_view(), name="address-list"),
    path("addresses/<int:pk>/", api_views.AddressDetailAPIView.as_view(), name="address-detail"),
    path(
        "addresses/<int:pk>/set-default/",
        api_views.SetDefaultAddressAPIView.as_view(),
        name="address-set-default",
    ),
    path("rider-profile/", api_views.RiderProfileSelfAPIView.as_view(), name="rider-profile"),
    path("riders/", api_views.RiderListAPIView.as_view(), name="rider-list"),
    path("users/", api_views.UserListAPIView.as_view(), name="user-list"),
    path("users/<int:pk>/role/", api_views.UserRoleUpdateAPIView.as_view(), name="user-role-update"),
]
