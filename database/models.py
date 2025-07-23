from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

# === Справочники ===

class Gender(Base):
    __tablename__ = "genders"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Orientation(Base):
    __tablename__ = "orientations"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class DatingGoal(Base):
    __tablename__ = "dating_goals"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)


# === Пользователь ===

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(Integer, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(Integer)
    bio = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    gender_id = Column(ForeignKey("genders.id"))
    orientation_id = Column(ForeignKey("orientations.id"))
    dating_goal_id = Column(ForeignKey("dating_goals.id"))
    city_id = Column(ForeignKey("cities.id"))

    gender = relationship("Gender")
    orientation = relationship("Orientation")
    dating_goal = relationship("DatingGoal")
    city = relationship("City")

    tags = relationship("UserTag", back_populates="user")
    photos = relationship("Photo", back_populates="user")


# === Привязка тэгов к пользователю ===

class UserTag(Base):
    __tablename__ = "user_tags"
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    tag_id = Column(ForeignKey("tags.id"), primary_key=True)

    user = relationship("User", back_populates="tags")
    tag = relationship("Tag")


# === Фото ===

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    file_id = Column(String)  # Telegram File ID или путь к файлу
    uploaded_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="photos")


# === Анонимный чат ===

class AnonymousChat(Base):
    __tablename__ = "chats"
    __table_args__ = (
        Index('ix_unique_chat_users', 'user1_id', 'user2_id', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(ForeignKey("users.id"))
    user2_id = Column(ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.datetime.now)
    messages_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])


# === Запрос на деанон ===

class DeanonRequest(Base):
    __tablename__ = "deanon_requests"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(ForeignKey("chats.id"))
    user1_approved = Column(Boolean, default=False)
    user2_approved = Column(Boolean, default=False)
    requested_at = Column(DateTime, default=datetime.datetime.now)

    chat = relationship("AnonymousChat", foreign_keys=[chat_id])
