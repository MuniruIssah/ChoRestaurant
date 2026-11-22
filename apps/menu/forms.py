"""
Django forms for Category and FoodItem administration.
Can be used in Developer 5's admin/staff management templates.
Owned by Developer 1.
"""
from django import forms

from .models import Category, FoodItem


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = (
            "name",
            "slug",
            "description",
            "image",
            "sort_order",
            "is_active",
        )


class FoodItemForm(forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = (
            "category",
            "name",
            "slug",
            "description",
            "price",
            "image",
            "is_available",
            "is_featured",
            "prep_time_minutes",
        )
