import os
import time
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select
import logging
from pythonjsonlogger import jsonlogger

# JSON logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("book")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler.setFormatter(fmt)
logger.addHandler(handler)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres-book:5432/book_db")

engine = create_engine(DATABASE_URL, echo=False)


class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    price: float
    description: Optional[str] = None


class BookCreate(SQLModel):
    title: str
    author: str
    price: float
    description: Optional[str] = None


class BookUpdate(SQLModel):
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None


app = FastAPI(title="Book Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@app.on_event("startup")
def on_startup():
    # retry logic za konekciju sa DB-om
    max_retries = 5
    for attempt in range(max_retries):
        try:
            create_db_and_tables()
            logger.info("✓ Book DB initialized")
            break
        except Exception as e:
            logger.warning(f"DB connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
    
    # seed test podatke
    try:
        with Session(engine) as session:
            existing = session.exec(select(Book)).all()
            if len(existing) == 0:
                test_books = [
                    Book(title="Rat i mir", author="Lav Tolstoj", price=25.99, description="Klasični roman o ljubavi, ratu i istoriji"),
                    Book(title="Prestupljenje i kazna", author="Fjodor Dostojevski", price=22.50, description="Psihološki roman o krivici i iskupljenju"),
                    Book(title="Ponos i predrasuda", author="Džein Ostin", price=18.99, description="Romantični roman iz 19. veka"),
                    Book(title="Devet priča", author="Isak Asimov", price=15.75, description="Zbirka naučnofantastičnih priča"),
                ]
                for book in test_books:
                    session.add(book)
                session.commit()
                logger.info(f"✓ Ubačeno {len(test_books)} test knjiga")
            else:
                logger.info(f"✓ {len(existing)} knjiga već postoji")
    except Exception as e:
        logger.warning(f"Seed warning: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "book"}


@app.get("/books", response_model=List[Book])
def list_books(session: Session = Depends(get_session)):
    books = session.exec(select(Book)).all()
    return books


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    return book


@app.post("/books", response_model=Book)
def create_book(book: BookCreate, session: Session = Depends(get_session)):
    db_book = Book.from_orm(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate, session: Session = Depends(get_session)):
    db_book = session.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    update_data = book.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


@app.delete("/books/{book_id}")
def delete_book(book_id: int, session: Session = Depends(get_session)):
    db_book = session.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    session.delete(db_book)
    session.commit()
    return {"message": "Knjiga obrisana"}
