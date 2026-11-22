"""
DRF Serializers for Category and FoodItem.
Exposes category metadata, prices, formatted currency strings, availability,
and aggregate review rating placeholders for Developer 2 and Developer 5.
Owned by Developer 1.
"""
from rest_framework import serializers

from .models import Category, FoodItem


class CategorySerializer(serializers.ModelSerializer):
    available_items_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image",
            "sort_order",
            "is_active",
            "available_items_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "available_items_count", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False},
        }

    def get_available_items_count(self, obj: Category) -> int:
        if hasattr(obj, "available_count"):
            return obj.available_count
        return obj.food_items.filter(is_available=True).count()


class FoodItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    is_orderable = serializers.BooleanField(read_only=True)
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = FoodItem
        fields = (
            "id",
            "category",
            "category_name",
            "category_slug",
            "name",
            "slug",
            "description",
            "price",
            "formatted_price",
            "image",
            "is_available",
            "is_featured",
            "is_orderable",
            "prep_time_minutes",
            "avg_rating",
            "review_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_name",
            "category_slug",
            "formatted_price",
            "is_orderable",
            "avg_rating",
            "review_count",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "slug": {"required": False},
        }

    def get_avg_rating(self, obj: FoodItem):
        return getattr(obj, "avg_food_rating", None)

    def get_review_count(self, obj: FoodItem) -> int:
        return getattr(obj, "review_count", 0)


class CategoryDetailSerializer(CategorySerializer):
    food_items = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ("food_items",)

    def get_food_items(self, obj: Category):
        request = self.context.get("request")
        include_unavailable = False
        if request and request.user.is_authenticated and getattr(request.user, "is_restaurant_staff", False):
            include_unavailable = request.query_params.get("include_unavailable", "").lower() in (
                "1",
                "true",
                "yes",
            )
        qs = obj.food_items.all() if include_unavailable else obj.food_items.filter(is_available=True)
        return FoodItemSerializer(qs, many=True, context=self.context).data
