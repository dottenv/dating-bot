from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(Integer, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(Integer)
    tags = Column(String)
    gender = Column(String)
    orientation = Column(String)
    city = Column(String)
    bio = Column(String)
    photo_id = Column(String)
    dating_goal = Column(String)  # Цель знакомства: отношения, дружба, общение и т.д.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    user_rating = Column(Integer, default=100)  # Рейтинг пользователя от 0 до 100, по умолчанию 100
    profile_completed = Column(Boolean, default=False)  # Флаг, указывающий на полноту заполнения профиля


class AnonymousChat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(ForeignKey('users.id'))
    user2_id = Column(ForeignKey('users.id'))
    start_time = Column(DateTime, default=datetime.datetime.now)
    messages_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    user1 = relationship('User', foreign_keys=[user1_id])
    user2 = relationship('User', foreign_keys=[user2_id])

class DeanonRequest(Base):
    __tablename__ = 'deanon_requests'
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(ForeignKey('chats.id'))
    user1_approved = Column(Boolean, default=False)
    user2_approved = Column(Boolean, default=False)
    requested_at = Column(DateTime, default=datetime.datetime.now)

    chat = relationship('AnonymousChat', foreign_keys=[chat_id])

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(ForeignKey('users.id'))
    user2_id = Column(ForeignKey('users.id'))
    chat_count = Column(Integer, default=1)  # Количество чатов между пользователями
    last_chat_at = Column(DateTime, default=datetime.datetime.now)

    user1 = relationship('User', foreign_keys=[user1_id])
    user2 = relationship('User', foreign_keys=[user2_id])
