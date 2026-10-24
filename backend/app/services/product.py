from sqlalchemy.orm import Session
from app.models import Product


def list_products(db: Session):
    return db.query(Product).all()


def create_product(db: Session, **kwargs) -> Product:
    product = Product(**kwargs)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
