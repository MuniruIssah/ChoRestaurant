"""
DRF JSON API Views for Food Categories and Food Items.
Public read access for customers; Staff/Admin write access for menu administration.
Owned by Developer 1.
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffOrAdmin, ReadOnlyOrStaffAdmin, user_has_role

from .models import Category, FoodItem
from .serializers import CategoryDetailSerializer, CategorySerializer, FoodItemSerializer
from .services import get_featured_offers, toggle_food_availability


class CategoryListCreateAPIView(generics.ListCreateAPIView):
    """
    GET / POST /api/menu/categories/
    Publicly lists active categories; Staff/Admin can pass ?include_inactive=true and create categories.
    """

    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrStaffAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = Category.objects.ordered()
        include_inactive = self.request.query_params.get("include_inactive", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if include_inactive and user_has_role(self.request.user, "STAFF", "ADMIN"):
            return qs
        return qs.active()


class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE /api/menu/categories/<slug>/
    Retrieve a category with its food items, or update/delete it (Staff/Admin).
    """

    serializer_class = CategoryDetailSerializer
    permission_classes = [ReadOnlyOrStaffAdmin]
    lookup_field = "slug"

    def get_queryset(self):
        if user_has_role(self.request.user, "STAFF", "ADMIN"):
            return Category.objects.all()
        return Category.objects.active()


class FoodItemListCreateAPIView(generics.ListCreateAPIView):
    """
    GET / POST /api/menu/items/
    Supports filters:
      - ?category=<slug_or_id>
      - ?featured=true
      - ?search=<query>
      - ?include_unavailable=true (Staff/Admin)
    """

    serializer_class = FoodItemSerializer
    permission_classes = [ReadOnlyOrStaffAdmin]

    def get_queryset(self):
        qs = FoodItem.objects.select_related("category").all()
        include_unavailable = self.request.query_params.get("include_unavailable", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not (include_unavailable and user_has_role(self.request.user, "STAFF", "ADMIN")):
            qs = qs.available()

        category = self.request.query_params.get("category")
        if category:
            qs = qs.by_category(category)

        featured = self.request.query_params.get("featured", "").lower()
        if featured in ("1", "true", "yes"):
            qs = qs.filter(is_featured=True)

        search = self.request.query_params.get("search") or self.request.query_params.get("q")
        if search:
            qs = qs.search(search)

        return qs


class FoodItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE /api/menu/items/<slug>/
    """

    serializer_class = FoodItemSerializer
    permission_classes = [ReadOnlyOrStaffAdmin]
    lookup_field = "slug"

    def get_queryset(self):
        qs = FoodItem.objects.select_related("category")
        if user_has_role(self.request.user, "STAFF", "ADMIN"):
            return qs.all()
        return qs.available()


class ToggleFoodAvailabilityAPIView(APIView):
    """
    POST /api/menu/items/<slug>/toggle-availability/
    Staff/Admin endpoint to quickly toggle or set `is_available` on a food item.
    """

    permission_classes = [IsAuthenticated, IsStaffOrAdmin]

    def post(self, request, slug: str):
        food_item = get_object_or_404(FoodItem, slug=slug)
        explicit_val = request.data.get("is_available")
        if explicit_val is not None:
            if isinstance(explicit_val, str):
                explicit_val = explicit_val.lower() in ("1", "true", "yes")
            else:
                explicit_val = bool(explicit_val)
        food_item = toggle_food_availability(request.user, food_item, is_available=explicit_val)
        return Response(
            {
                "message": f"Availability for '{food_item.name}' set to {food_item.is_available}.",
                "item": FoodItemSerializer(food_item, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class FeaturedFoodItemsAPIView(generics.ListAPIView):
    """
    GET /api/menu/featured/
    Public endpoint returning special meals and daily offers (is_featured=True & available).
    """

    serializer_class = FoodItemSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return get_featured_offers()
