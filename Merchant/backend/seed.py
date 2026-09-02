"""Seed baseline categories for local development.

Usage:
    python seed.py
"""

from app import create_app
from app.extensions import db
from app.models import Category

DEFAULT_CATEGORIES = {
    "Electronics": ["Keyboards", "Mouse", "Monitors", "Laptops", "Audio"],
    "Fashion": ["Men", "Women", "Kids"],
    "Home & Kitchen": ["Furniture", "Decor", "Appliances"],
}


def run():
    app = create_app()
    with app.app_context():
        for parent_name, children in DEFAULT_CATEGORIES.items():
            parent = Category.query.filter_by(name=parent_name).first()
            if not parent:
                parent = Category(
                    name=parent_name,
                    slug=parent_name.lower().replace(" & ", "-").replace(" ", "-"),
                )
                db.session.add(parent)
                db.session.flush()

            for child_name in children:
                exists = Category.query.filter_by(
                    name=child_name, parent_id=parent.id
                ).first()
                if not exists:
                    db.session.add(
                        Category(
                            name=child_name,
                            slug=child_name.lower().replace(" ", "-"),
                            parent_id=parent.id,
                        )
                    )

        db.session.commit()
        print("Seeded categories.")


if __name__ == "__main__":
    run()
