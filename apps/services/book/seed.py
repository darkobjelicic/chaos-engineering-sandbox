import os
from sqlmodel import Session, create_engine
from services.book.main import Book

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres-book:5432/book_db")

def seed_books():
    engine = create_engine(DATABASE_URL, echo=False)
    
    with Session(engine) as session:
        # provjeri da li već postoje knjige
        existing = session.query(Book).count()
        if existing > 0:
            print("✓ Knjige već postoje u bazi")
            return
        
        books = [
            Book(title="Rat i mir", author="Lav Tolstoj", price=25.99, description="Klasični roman o ljubavi, ratu i istoriji"),
            Book(title="Prestupljenje i kazna", author="Fjodor Dostojevski", price=22.50, description="Psihološki roman o krivici i iskupljenju"),
            Book(title="Ponos i predrasuda", author="Džein Ostin", price=18.99, description="Romantični roman iz 19. veka"),
            Book(title="Devet priča", author="Isak Asimov", price=15.75, description="Zbirka naučnofantastičnih priča"),
        ]
        
        for book in books:
            session.add(book)
        
        session.commit()
        print(f"✓ Ubačeno {len(books)} knjiga u bazu")

if __name__ == "__main__":
    seed_books()
