from app.seeders.user_seeder import seed_education, seed_health_data, seed_users


def run_all():
    print("Running user seeder...")
    seed_users()
    print("Running education seeder...")
    seed_education()
    print("Running health data seeder...")
    seed_health_data()
    print("All seeders completed.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.extensions import db

        db.create_all()
        run_all()
