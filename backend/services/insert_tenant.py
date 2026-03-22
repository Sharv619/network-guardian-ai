from backend.db.session import SessionLocal
from backend.db.models import Tenant
from datetime import datetime

def insert_tenant():
    db = SessionLocal()
    try:
        # Check if tenant with ID 2 already exists
        existing_tenant = db.query(Tenant).filter(Tenant.id == 2).first()
        if existing_tenant:
            print(f"⚠️ Tenant with ID 2 already exists: {existing_tenant.name}")
            return

        # Create a new tenant
        tenant = Tenant(
            id=2,
            name="Acme Corp",
            subdomain="acme",
            api_key="acme-api-key-123",
            is_active=True,
            subscription_tier="pro",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(tenant)
        db.commit()
        print("✅ Tenant 'Acme Corp' inserted successfully!")

        # Verify insertion
        new_tenant = db.query(Tenant).filter(Tenant.id == 2).first()
        print(f"Verified: {new_tenant.name} (ID: {new_tenant.id})")

    except Exception as e:
        print(f"❌ Error inserting tenant: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    insert_tenant()
