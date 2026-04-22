# app/routes/items.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app import models

router = APIRouter()


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class ItemCreate(BaseModel):
    name: str
    description: str = ""


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: Optional[str] = None  # ISO string for dashboard display

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        data = {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description or "",
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
        return cls(**data)


class ItemsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ItemResponse]


class ItemStatsResponse(BaseModel):
    total_items: int
    items_with_description: int
    description_coverage_pct: float
    latest_item_name: Optional[str]
    latest_item_created_at: Optional[str]


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@router.get("/items/stats", response_model=ItemStatsResponse, summary="Get item statistics for the dashboard")
def get_item_stats(db: Session = Depends(get_db)):
    """
    Returns aggregate statistics about items:
    - total count
    - items with a non-empty description
    - description coverage percentage
    - latest item added (for the dashboard stat card)
    """
    total = db.query(func.count(models.Item.id)).scalar() or 0
    with_desc = (
        db.query(func.count(models.Item.id))
        .filter(models.Item.description.isnot(None), models.Item.description != "")
        .scalar() or 0
    )
    latest = (
        db.query(models.Item)
        .order_by(models.Item.created_at.desc())
        .first()
    )
    coverage = round((with_desc / total * 100), 1) if total > 0 else 0.0

    return ItemStatsResponse(
        total_items=total,
        items_with_description=with_desc,
        description_coverage_pct=coverage,
        latest_item_name=latest.name if latest else None,
        latest_item_created_at=latest.created_at.isoformat() if latest and latest.created_at else None,
    )


@router.get("/items", response_model=ItemsListResponse, summary="List items with search and pagination")
def get_items(
    search: Optional[str] = Query(None, description="Search by name or description"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of items.
    Supports optional full-text search across name and description.
    """
    query = db.query(models.Item)

    if search:
        like = f"%{search}%"
        query = query.filter(
            models.Item.name.ilike(like) | models.Item.description.ilike(like)
        )

    total = query.count()
    items = (
        query
        .order_by(models.Item.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ItemsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ItemResponse.from_orm(i) for i in items],
    )


@router.get("/items/{item_id}", response_model=ItemResponse, summary="Get a single item by ID")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return ItemResponse.from_orm(item)


@router.post("/items", response_model=ItemResponse, status_code=201, summary="Create a new item")
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    if not item.name.strip():
        raise HTTPException(status_code=422, detail="Item name cannot be empty")
    db_item = models.Item(name=item.name.strip(), description=item.description.strip())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return ItemResponse.from_orm(db_item)


@router.put("/items/{item_id}", response_model=ItemResponse, summary="Update an existing item (full or partial)")
def update_item(item_id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    """
    Partial update — only fields provided in the request body are changed.
    Required by the dashboard Edit modal.
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    if item.name is not None:
        if not item.name.strip():
            raise HTTPException(status_code=422, detail="Item name cannot be empty")
        db_item.name = item.name.strip()

    if item.description is not None:
        db_item.description = item.description.strip()

    db.commit()
    db.refresh(db_item)
    return ItemResponse.from_orm(db_item)


@router.delete("/items/{item_id}", summary="Delete an item")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    db.delete(item)
    db.commit()
    return {"message": f"Item {item_id} deleted successfully"}
