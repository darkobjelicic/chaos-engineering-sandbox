import os
import time
from sqlmodel import Session, create_engine, select
from services.inventory.main import Inventory

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres-inventory:5432/inventory_db")

def seed_inventory():
    engine = create_engine(DATABASE_URL, echo=False)
    
    # čekaj malo da se baza inicijalizira
    time.sleep(2)
    
    with Session(engine) as session:
        # provjeri da li već postoje stavke
        existing = session.exec(select(Inventory)).all()
        if len(existing) > 0:
            print("✓ Zalihе već postoje u bazi")
            return
        
        items = [
            Inventory(book_id=1, quantity=50),
            Inventory(book_id=2, quantity=30),
            Inventory(book_id=3, quantity=45),
            Inventory(book_id=4, quantity=20),
        ]
        
        for item in items:
            session.add(item)
        
        session.commit()
        print(f"✓ Ubačeno {len(items)} stavki zaliha u bazu")

if __name__ == "__main__":
    seed_inventory()
