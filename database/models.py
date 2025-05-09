# models.py
from sqlalchemy import (
    Column,
    String,
    Float,
    JSON,
    ForeignKey,
    Table,
    Integer,
    DateTime,
    Boolean,
    Index,
    func,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
import uuid

Base = declarative_base()


class Member(Base):
    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)


# For storing Bookings
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("members.id"))
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    booking_date = Column(DateTime)
    recording_date = Column(DateTime, server_default=func.now())
    num_of_people = Column(Integer)
    special_requests = Column(String)
    confirmed = Column(Boolean, default=False)

    member = relationship("Member")
    place = relationship("Place")


# Таблицы связи многие-ко-многим
place_alternate_names = Table(
    "place_alternate_names",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
    Column(
        "alternate_name_id",
        UUID(as_uuid=True),
        ForeignKey("alternate_names.id", ondelete="CASCADE"),
    ),
)

place_metro_stations = Table(
    "place_metro_stations",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
    Column(
        "metro_station_id",
        UUID(as_uuid=True),
        ForeignKey("metro_stations.id", ondelete="CASCADE"),
    ),
)

place_cuisines = Table(
    "place_cuisines",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
    Column(
        "cuisine_id", UUID(as_uuid=True), ForeignKey("cuisines.id", ondelete="CASCADE")
    ),
)

place_features = Table(
    "place_features",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
    Column(
        "feature_id", UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE")
    ),
)

place_visit_purposes = Table(
    "place_visit_purposes",
    Base.metadata,
    Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
    Column(
        "visit_purpose_id",
        UUID(as_uuid=True),
        ForeignKey("visit_purposes.id", ondelete="CASCADE"),
    ),
)


class Place(AsyncAttrs, Base):
    __tablename__ = "places"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String)
    phone = Column(String)
    address = Column(String)
    type = Column(String)
    average_check = Column(String)
    description = Column(String)
    deposit_rules = Column(String)
    coordinates_lat = Column(Float)
    coordinates_lon = Column(Float)
    source_url = Column(String)
    source_domain = Column(String)

    # Relationships
    alternate_names = relationship(
        "AlternateName", secondary=place_alternate_names, back_populates="places"
    )
    metro_stations = relationship(
        "MetroStation", secondary=place_metro_stations, back_populates="places"
    )
    cuisines = relationship(
        "Cuisine", secondary=place_cuisines, back_populates="places"
    )
    features = relationship(
        "Feature", secondary=place_features, back_populates="places"
    )
    visit_purposes = relationship(
        "VisitPurpose", secondary=place_visit_purposes, back_populates="places"
    )

    opening_hours = relationship("OpeningHour", back_populates="place")
    photos = relationship("Photo", back_populates="place")
    menu_links = relationship("MenuLink", back_populates="place")
    booking_links = relationship("BookingLink", back_populates="place")
    reviews = relationship("Review", back_populates="place")
    available_online = Column(Boolean, default=True)

    __ts_vector__ = Column(
        TSVECTOR(),
        Computed(
            "to_tsvector('russian', "
            "coalesce(full_name, '') || ' ' || "
            "coalesce(address, '') || ' ' || "
            "coalesce(description, ''))"
        )
    )
    
    __table_args__ = (
        Index('ix_place_search', __ts_vector__, postgresql_using='gin'),
        Index('ix_place_trgm', 'full_name', 'address', postgresql_using='gin', 
              postgresql_ops={
                  'full_name': 'gin_trgm_ops',
                  'address': 'gin_trgm_ops'
              }),
    )

    @property
    def name(self):
        return self.full_name


class AlternateName(AsyncAttrs, Base):
    __tablename__ = "alternate_names"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    places = relationship(
        "Place", secondary=place_alternate_names, back_populates="alternate_names"
    )
    
    __table_args__ = (
        Index('ix_alt_names', 'name', postgresql_using='gin',
              postgresql_ops={'name': 'gin_trgm_ops'}),
    )


class MetroStation(AsyncAttrs, Base):
    __tablename__ = "metro_stations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    places = relationship(
        "Place", secondary=place_metro_stations, back_populates="metro_stations"
    )


class Cuisine(AsyncAttrs, Base):
    __tablename__ = "cuisines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    places = relationship("Place", secondary=place_cuisines, back_populates="cuisines")


class Feature(AsyncAttrs, Base):
    __tablename__ = "features"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    places = relationship("Place", secondary=place_features, back_populates="features")


class VisitPurpose(AsyncAttrs, Base):
    __tablename__ = "visit_purposes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    places = relationship(
        "Place", secondary=place_visit_purposes, back_populates="visit_purposes"
    )


class OpeningHour(AsyncAttrs, Base):
    __tablename__ = "opening_hours"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day = Column(String)
    hours = Column(String)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    place = relationship("Place", back_populates="opening_hours")


class Photo(AsyncAttrs, Base):
    __tablename__ = "photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String)
    url = Column(String)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    place = relationship("Place", back_populates="photos")


class MenuLink(AsyncAttrs, Base):
    __tablename__ = "menu_links"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String)
    url = Column(String)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    place = relationship("Place", back_populates="menu_links")


class BookingLink(AsyncAttrs, Base):
    __tablename__ = "booking_links"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String)
    url = Column(String)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    place = relationship("Place", back_populates="booking_links")


class Review(AsyncAttrs, Base):
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author = Column(String)
    date = Column(String)
    rating = Column(Integer)
    text = Column(String)
    source = Column(String)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    place = relationship("Place", back_populates="reviews")
