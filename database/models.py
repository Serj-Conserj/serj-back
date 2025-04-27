from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    Table,
    create_engine,
)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from database.database import Base

Base = declarative_base()

# For storing Users
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


# Main table with places (associative tables included)

# Associative table for restraunts:
restaurant_cuisine = Table(
    "restaurant_cuisine",
    Base.metadata,
    Column("restaurant_id", UUID(as_uuid=True), ForeignKey("places.id")),
    Column("cuisine_id", UUID(as_uuid=True), ForeignKey("cuisines.id")),
)

# Associative table for metro stations:
restaurant_metro = Table(
    "restaurant_metro",
    Base.metadata,
    Column("restaurant_id", UUID(as_uuid=True), ForeignKey("places.id")),
    Column("metro_id", UUID(as_uuid=True), ForeignKey("metro_stations.id")),
)


class Cuisine(Base):
    __tablename__ = "cuisines"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    places = relationship(
        "Place", secondary=restaurant_cuisine, back_populates="cuisines"
    )


class MetroStation(Base):
    __tablename__ = "metro_stations"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    places = relationship(
        "Place", secondary=restaurant_metro, back_populates="metro_stations"
    )


class Place(Base):
    __tablename__ = "places"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    alternate_name = Column(String(255))
    address = Column(String(255))
    goo_rating = Column(Float)
    party_booking_name = Column(String(512))
    booking_form = Column(String(512))
    available_online = Column(Boolean, default=False)

    cuisines = relationship(
        "Cuisine", secondary=restaurant_cuisine, back_populates="places"
    )
    metro_stations = relationship(
        "MetroStation", secondary=restaurant_metro, back_populates="places"
    )
