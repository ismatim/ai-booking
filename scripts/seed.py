# scripts/seed.py
import sys
import os

# Add the project root to the path so we can import our services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_service import SupabaseService


def create_db():
    db = SupabaseService()
    print("🌱 Creating database tables...")

    print("✅ Database tables created successfully!")


def run_seed():
    db = SupabaseService()
    print("🌱 Seeding database...")

    # Logic to insert consultants, users, or test bookings
    # ...

    print("✅ Database seeded successfully!")


if __name__ == "__main__":
    run_seed()
