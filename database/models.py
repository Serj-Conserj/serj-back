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
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database.database import Base


# For storing Users
class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

# class User(Base):
#     __tablename__ = "users"

#     # TODO change when bot will normally exist
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     first_name = Column(String(64))
#     last_name = Column(String(64))
#     username = Column(String(64))
#     telegram_id = Column(Integer, unique=True, nullable=False)  # пока называется как id
#     phone = Column(String(20))  # понять как получать

#     password = Column(String(128))  # это что за приколы

#     is_active = Column(Boolean, default=True)
#     is_admin = Column(Boolean, default=False)
#     is_superuser = Column(Boolean, default=False)

#     last_login = Column(DateTime, nullable=True)


# For storing Bookings
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"))
    booking_date = Column(DateTime)
    recording_date = Column(DateTime, server_default=func.now())
    num_of_people = Column(Integer)
    special_requests = Column(String)
    confirmed = Column(Boolean, default=False)

    user = relationship("User")
    place = relationship("Place")


# For storing Places


class Place(Base):
    __tablename__ = "places"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True)
    available_online = Column(
        Boolean, default=False
    )  # нужно сохранить - юзаю для очередей
