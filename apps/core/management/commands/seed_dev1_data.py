"""
Management command to seed Developer 1's foundational data:
  - Singleton RestaurantSettings (Ghana & GHS defaults)
  - Demo users for all 4 roles: ADMIN, STAFF, RIDER, CUSTOMER
  - Default delivery address in Accra, Ghana for the demo customer
  - Verified RiderProfile for the demo rider
  - Sample Ghanaian & Continental food categories and food items
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Address, CustomerProfile, RiderProfile, User, UserRole
from apps.core.models import RestaurantSettings
from apps.menu.models import Category, FoodItem


class Command(BaseCommand):
    help = "Seed Developer 1 foundation data (roles, profiles, addresses, categories, and food items)."

    @transaction.atomic
    def handle(self, *args, **options):
        settings_obj = RestaurantSettings.get_solo()
        self.stdout.write(
            self.style.SUCCESS(
                f"Configured RestaurantSettings: {settings_obj.restaurant_name} "
                f"({settings_obj.operating_country}, {settings_obj.currency})"
            )
        )

        # 1. Admin user
        admin_user, created = User.objects.get_or_create(
            username="admin_cho",
            defaults={
                "email": "admin@chorestaurant.com",
                "first_name": "Kwame",
                "last_name": "Mensah",
                "phone": "+233240000001",
                "role": UserRole.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
            },
        )
        if created:
            admin_user.set_password("AdminPass123!")
            admin_user.save()

        # 2. Staff user
        staff_user, created = User.objects.get_or_create(
            username="staff_ama",
            defaults={
                "email": "staff@chorestaurant.com",
                "first_name": "Ama",
                "last_name": "Osei",
                "phone": "+233240000002",
                "role": UserRole.STAFF,
                "is_email_verified": True,
            },
        )
        if created:
            staff_user.set_password("StaffPass123!")
            staff_user.save()

        # 3. Rider user
        rider_user, created = User.objects.get_or_create(
            username="rider_kofi",
            defaults={
                "email": "rider@chorestaurant.com",
                "first_name": "Kofi",
                "last_name": "Boateng",
                "phone": "+233240000003",
                "role": UserRole.RIDER,
                "is_email_verified": True,
            },
        )
        if created:
            rider_user.set_password("RiderPass123!")
            rider_user.save()

        rider_profile, _ = RiderProfile.objects.get_or_create(user=rider_user)
        rider_profile.vehicle_type = "MOTORCYCLE"
        rider_profile.plate_number = "GR-4521-26"
        rider_profile.is_available = True
        rider_profile.is_verified = True
        rider_profile.location_consent = True
        rider_profile.current_lat = Decimal("5.610000")
        rider_profile.current_lng = Decimal("-0.182000")
        rider_profile.save()

        # 4. Customer user
        customer_user, created = User.objects.get_or_create(
            username="customer_akua",
            defaults={
                "email": "customer@chorestaurant.com",
                "first_name": "Akua",
                "last_name": "Asante",
                "phone": "+233240000004",
                "role": UserRole.CUSTOMER,
                "is_email_verified": True,
            },
        )
        if created:
            customer_user.set_password("CustomerPass123!")
            customer_user.save()

        CustomerProfile.objects.get_or_create(user=customer_user)
        Address.objects.get_or_create(
            user=customer_user,
            label="Home",
            defaults={
                "line1": "14 Independence Avenue",
                "line2": "Ridge",
                "city": "Accra",
                "state": "Greater Accra",
                "postal_code": "GA-050-1234",
                "country": "Ghana",
                "latitude": Decimal("5.573100"),
                "longitude": Decimal("-0.196900"),
                "is_default": True,
            },
        )

        # 5. Categories & Food Items
        menu_seed = [
            {
                "name": "Local Dishes",
                "description": "Authentic Ghanaian favorites prepared fresh daily.",
                "sort_order": 1,
                "items": [
                    {
                        "name": "Assorted Jollof Rice with Grilled Chicken",
                        "description": "Smoky Ghanaian party jollof served with spicy grilled chicken, kelewele, and shito.",
                        "price": Decimal("85.00"),
                        "is_featured": True,
                        "prep_time_minutes": 25,
                    },
                    {
                        "name": "Banku & Grilled Tilapia",
                        "description": "Fresh Volta tilapia grilled with spices, served with hot banku and green/red pepper sauce.",
                        "price": Decimal("110.00"),
                        "is_featured": True,
                        "prep_time_minutes": 30,
                    },
                    {
                        "name": "Waakye Special",
                        "description": "Traditional rice and beans with wele, boiled egg, gari, spaghetti, beef stew, and shito.",
                        "price": Decimal("75.00"),
                        "is_featured": False,
                        "prep_time_minutes": 15,
                    },
                ],
            },
            {
                "name": "Grills & Starters",
                "description": "Spicy starters, skewers, and side dishes.",
                "sort_order": 2,
                "items": [
                    {
                        "name": "Spicy Kelewele Bowl",
                        "description": "Diced ripe plantain seasoned with ginger, cloves, and chili, served with roasted peanuts.",
                        "price": Decimal("35.00"),
                        "is_featured": True,
                        "prep_time_minutes": 15,
                    },
                    {
                        "name": "Beef Chichinga Skewers",
                        "description": "Tender spiced Ghanaian suya kebabs grilled over charcoal with onions and bell peppers.",
                        "price": Decimal("50.00"),
                        "is_featured": False,
                        "prep_time_minutes": 20,
                    },
                ],
            },
            {
                "name": "Drinks & Refreshments",
                "description": "Chilled natural juices and local beverages.",
                "sort_order": 3,
                "items": [
                    {
                        "name": "Chilled Sobolo (Hibiscus Drink)",
                        "description": "Refreshing hibiscus infusion spiced with ginger, pineapple, and cloves.",
                        "price": Decimal("20.00"),
                        "is_featured": False,
                        "prep_time_minutes": 5,
                    },
                    {
                        "name": "Fresh Pineapple & Ginger Juice",
                        "description": "100% cold-pressed Aburi pineapple and organic ginger.",
                        "price": Decimal("28.00"),
                        "is_featured": False,
                        "prep_time_minutes": 5,
                    },
                ],
            },
        ]

        for cat_data in menu_seed:
            category, _ = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "description": cat_data["description"],
                    "sort_order": cat_data["sort_order"],
                    "is_active": True,
                },
            )
            for item_data in cat_data["items"]:
                FoodItem.objects.get_or_create(
                    category=category,
                    name=item_data["name"],
                    defaults={
                        "description": item_data["description"],
                        "price": item_data["price"],
                        "is_available": True,
                        "is_featured": item_data["is_featured"],
                        "prep_time_minutes": item_data["prep_time_minutes"],
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded Developer 1 foundation data (Users, Profiles, Addresses, Categories, FoodItems)."
            )
        )
