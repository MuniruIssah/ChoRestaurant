"""
Menu domain models:
  - Category (menu_category)
  - FoodItem (menu_fooditem)
Matches docs/schema.sql and PRD §4.2.
Owned by Developer 1.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.utils import format_currency, quantize_money


def generate_unique_slug(model_cls, source_text: str, max_length: int, instance_pk=None) -> str:
    base_slug = slugify(source_text)[: max_length - 8] or "item"
    slug = base_slug
    counter = 1
    qs = model_cls.objects.all()
    if instance_pk is not None:
        qs = qs.exclude(pk=instance_pk)
    while qs.filter(slug=slug).exists():
        counter += 1
        slug = f"{base_slug}-{counter}"[:max_length]
    return slug


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def ordered(self):
        return self.order_by("sort_order", "name")


class Category(TimeStampedModel):
    """
    Food category model (menu_category).
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to="menu/categories/",
        max_length=500,
        blank=True,
        null=True,
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        db_table = "menu_category"
        verbose_name = "Food Category"
        verbose_name_plural = "Food Categories"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name, max_length=120, instance_pk=self.pk)
        super().save(*args, **kwargs)


class FoodItemQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True, category__is_active=True)

    def featured(self):
        return self.available().filter(is_featured=True)

    def by_category(self, category_slug_or_id):
        if str(category_slug_or_id).isdigit():
            return self.filter(category_id=int(category_slug_or_id))
        return self.filter(category__slug=category_slug_or_id)

    def search(self, query: str):
        if not query:
            return self
        q = query.strip()
        return self.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )


class FoodItem(TimeStampedModel):
    """
    Food item model (menu_fooditem).
    Supports categories, prices in NUMERIC(12,2), images (local or Cloudinary),
    availability toggles, and featured daily offers / special meals.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="food_items",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    image = models.ImageField(
        upload_to="menu/items/",
        max_length=500,
        blank=True,
        null=True,
    )
    is_available = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(
        default=False,
        help_text="Special meals and daily offers highlighted on the customer site.",
    )
    prep_time_minutes = models.IntegerField(
        default=20,
        validators=[MinValueValidator(0)],
    )

    objects = FoodItemQuerySet.as_manager()

    class Meta:
        db_table = "menu_fooditem"
        verbose_name = "Food Item"
        verbose_name_plural = "Food Items"
        ordering = ["category__sort_order", "name"]
        indexes = [
            models.Index(fields=["category"], name="idx_fooditem_category"),
            models.Index(fields=["is_available"], name="idx_fooditem_available"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=Decimal("0.00")),
                name="chk_fooditem_price_non_negative",
            ),
            models.CheckConstraint(
                check=Q(prep_time_minutes__gte=0),
                name="chk_fooditem_prep_time_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.formatted_price})"

    @property
    def formatted_price(self) -> str:
        return format_currency(self.price)

    @property
    def is_orderable(self) -> bool:
        return bool(self.is_available and self.category and self.category.is_active)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(FoodItem, self.name, max_length=170, instance_pk=self.pk)
        if self.price is not None:
            self.price = quantize_money(self.price)
        super().save(*args, **kwargs)
