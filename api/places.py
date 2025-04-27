from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database import get_db
from database.models import Place, Cuisine, MetroStation
from schemas import Place, PlaceCreate, Cuisine, MetroStation

router = APIRouter(prefix="/api/v1")

@router.get("/places", response_model=List[Place])
async def get_places(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    cuisine: Optional[str] = None,
    metro: Optional[str] = None,
    expand: Optional[List[str]] = Query(None)
):
    query = db.query(Place)
    
    # Фильтрация
    if min_rating is not None:
        query = query.filter(Place.goo_rating >= min_rating)
    
    if cuisine:
        query = query.join(Place.cuisines).filter(Cuisine.name.ilike(f"%{cuisine}%"))
    
    if metro:
        query = query.join(Place.metro_stations).filter(MetroStation.name.ilike(f"%{metro}%"))
    
    # Eager loading
    if expand:
        if "cuisines" in expand:
            query = query.options(joinedload(Place.cuisines))
        if "metro" in expand:
            query = query.options(joinedload(Place.metro_stations))
    
    return query.offset(skip).limit(limit).all()

@router.get("/places/{place_id}", response_model=Place)
async def get_place(
    place_id: UUID,
    db: Session = Depends(get_db),
    expand: Optional[List[str]] = Query(None)
):
    query = db.query(Place).filter(Place.id == place_id)
    
    if expand:
        if "cuisines" in expand:
            query = query.options(joinedload(Place.cuisines))
        if "metro" in expand:
            query = query.options(joinedload(Place.metro_stations))
    
    place = query.first()
    
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    
    return place

@router.get("/cuisines", response_model=List[Cuisine])
async def get_cuisines(
    db: Session = Depends(get_db),
    search: Optional[str] = None
):
    query = db.query(Cuisine)
    if search:
        query = query.filter(Cuisine.name.ilike(f"%{search}%"))
    return query.all()

@router.get("/metro", response_model=List[MetroStation])
async def get_metro_stations(
    db: Session = Depends(get_db),
    search: Optional[str] = None
):
    query = db.query(MetroStation)
    if search:
        query = query.filter(MetroStation.name.ilike(f"%{search}%"))
    return query.all()