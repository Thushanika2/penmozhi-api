from app.seeders.user_seeder import seed_health_data, seed_users
from app.seeders.education_seeder import seed_education
from app.seeders.tracking_category_seeder import seed_tracking_categories


def run_all():
    print("Running user seeder...")
    seed_users()
    print("Running education seeder...")
    seed_education()
    print("Running health data seeder...")
    seed_health_data()
    print("Running tracking category seeder...")
    seed_tracking_categories()
    print("All seeders completed.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.extensions import db

        db.create_all()
        run_all()
