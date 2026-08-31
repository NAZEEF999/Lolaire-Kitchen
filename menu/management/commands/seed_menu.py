from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import cloudinary.uploader


CATEGORIES = [
    ("Starters", "Elegant appetizers to begin your Lolaire's experience."),
    ("Main Courses", "Signature dishes prepared for a memorable dining experience."),
    ("Rice & Sides", "Premium rice dishes and carefully prepared sides."),
    ("Pasta", "Classic pasta dishes with a Lolaire's Kitchen touch."),
    ("Grills", "Beautifully grilled meats, chicken and seafood."),
    ("Seafood", "Fresh seafood dishes prepared with refined flavours."),
    ("Desserts", "Luxurious desserts to finish your meal."),
    ("Drinks", "Refreshing beverages and signature drinks."),
]


MENU_ITEMS = [
    {
        "category": "Starters",
        "name": "Chicken Wings",
        "description": "Crispy chicken wings glazed with a rich house sauce.",
        "price": "8500",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Starters",
        "name": "Spring Rolls",
        "description": "Crispy golden spring rolls served with a refined dipping sauce.",
        "price": "6500",
        "featured": False,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1515022376298-7333f33e704b?auto=format&fit=crop&fm=jpg&q=85&w=1200",
       
    },
    {
        "category": "Main Courses",
        "name": "Lolaire's Signature Chicken",
        "description": "Tender grilled chicken finished with Lolaire's signature seasoning.",
        "price": "15000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Main Courses",
        "name": "Creamy Chicken",
        "description": "Tender chicken served in a luxurious creamy sauce.",
        "price": "14500",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Main Courses",
        "name": "Beef Steak",
        "description": "Premium grilled beef steak served with a rich house sauce.",
        "price": "22000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Rice & Sides",
        "name": "Jollof Rice",
        "description": "Richly seasoned jollof rice prepared with our signature blend.",
        "price": "8500",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Rice & Sides",
        "name": "Fried Rice",
        "description": "Fragrant fried rice prepared with fresh vegetables and premium seasoning.",
        "price": "8500",
        "featured": False,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Rice & Sides",
        "name": "Jollof Rice & Grilled Chicken",
        "description": "Lolaire's signature jollof rice paired with beautifully grilled chicken.",
        "price": "16000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Pasta",
        "name": "Creamy Chicken Pasta",
        "description": "Silky creamy pasta tossed with tender chicken and herbs.",
        "price": "14000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Pasta",
        "name": "Penne Alfredo",
        "description": "Penne pasta coated in a rich and creamy Alfredo sauce.",
        "price": "13000",
        "featured": False,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Grills",
        "name": "Grilled Chicken",
        "description": "Juicy chicken grilled over high heat and finished with house seasoning.",
        "price": "15000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Grills",
        "name": "Grilled Beef",
        "description": "Tender beef grilled to perfection and served with a signature sauce.",
        "price": "18000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1558030006-450675393462?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Seafood",
        "name": "Grilled Fish",
        "description": "Fresh fish grilled with aromatic herbs and Lolaire's signature seasoning.",
        "price": "18000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Seafood",
        "name": "Garlic Butter Prawns",
        "description": "Succulent prawns sauteed in garlic butter and fresh herbs.",
        "price": "20000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Desserts",
        "name": "Chocolate Cake",
        "description": "Rich chocolate cake served with a luxurious finish.",
        "price": "7500",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Desserts",
        "name": "Cheesecake",
        "description": "Smooth creamy cheesecake with a delicate biscuit base.",
        "price": "7000",
        "featured": False,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1565958011703-44f9829ba187?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Drinks",
        "name": "Fresh Fruit Juice",
        "description": "Freshly prepared seasonal fruit juice.",
        "price": "5000",
        "featured": False,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=1200&q=85",
    },
    {
        "category": "Drinks",
        "name": "Lolaire's Signature Mocktail",
        "description": "A refreshing premium mocktail created especially for Lolaire's Kitchen.",
        "price": "7000",
        "featured": True,
        "available": True,
        "image_url": "https://images.unsplash.com/photo-1551024506-0bccd828d307?auto=format&fit=crop&w=1200&q=85",
    },
]


class Command(BaseCommand):
    help = "Create/update Lolaire's Kitchen categories and menu items."

    @transaction.atomic
    def handle(self, *args, **options):
        from menu.models import Category, MenuItem

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CREATING CATEGORIES")
        self.stdout.write("=" * 60)

        categories = {}

        for name, description in CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "is_active": True,
                },
            )

            category.description = description
            category.is_active = True
            category.save()

            categories[name] = category

            if created:
                self.stdout.write("Created category: " + name)
            else:
                self.stdout.write("Updated category: " + name)

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CREATING MENU ITEMS")
        self.stdout.write("=" * 60)

        created_count = 0
        updated_count = 0
        image_success = 0
        image_failed = 0

        for item in MENU_ITEMS:
            category = categories[item["category"]]

            menu_item, created = MenuItem.objects.get_or_create(
                name=item["name"],
                defaults={
                    "category": category,
                    "description": item["description"],
                    "price": Decimal(item["price"]),
                    "is_available": item["available"],
                    "is_featured": item["featured"],
                    "is_active": True,
                },
            )

            menu_item.category = category
            menu_item.description = item["description"]
            menu_item.price = Decimal(item["price"])
            menu_item.is_available = item["available"]
            menu_item.is_featured = item["featured"]
            menu_item.is_active = True

            # Upload image directly to Cloudinary.
            try:
                result = cloudinary.uploader.upload(
                    item["image_url"],
                    folder="lolaires-kitchen/menu",
                    public_id=(
                        item["name"]
                        .lower()
                        .replace("'", "")
                        .replace("&", "and")
                        .replace(" ", "_")
                    ),
                    overwrite=True,
                    resource_type="image",
                )

                menu_item.image = result["public_id"]
                image_success += 1

                self.stdout.write(
                    "Image uploaded: " + item["name"]
                )

            except Exception as error:
                image_failed += 1
                self.stdout.write(
                    self.style.WARNING(
                        "Image upload failed for "
                        + item["name"]
                        + ": "
                        + str(error)
                    )
                )

            menu_item.save()

            if created:
                created_count += 1
                self.stdout.write("Created: " + item["name"])
            else:
                updated_count += 1
                self.stdout.write("Updated: " + item["name"])

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("LOLAIRE'S KITCHEN MENU SEED COMPLETE")
        self.stdout.write("=" * 60)
        self.stdout.write("Categories: " + str(len(categories)))
        self.stdout.write("Menu items created: " + str(created_count))
        self.stdout.write("Menu items updated: " + str(updated_count))
        self.stdout.write("Images uploaded: " + str(image_success))
        self.stdout.write("Images failed: " + str(image_failed))
        self.stdout.write("Availability configured")
        self.stdout.write("Featured items configured")
        self.stdout.write("=" * 60)