from sqlalchemy.orm import Session
from database.models import AnonymousChat, DeanonRequest, User
from typing import Optional, Tuple, List

def find_available_chat_partner(db: Session, user_id: int) -> Optional[User]:
    # Find users who are active and not in a chat
    active_chat_users = db.query(AnonymousChat).filter(
        (AnonymousChat.user1_id == user_id) | (AnonymousChat.user2_id == user_id),
        AnonymousChat.is_active == True
    ).all()
    
    if active_chat_users:
        return None  # User is already in a chat
    
    # Find all active chats to exclude users who are already chatting
    active_chats = db.query(AnonymousChat).filter(AnonymousChat.is_active == True).all()
    busy_user_ids = []
    for chat in active_chats:
        busy_user_ids.extend([chat.user1_id, chat.user2_id])
    
    # Find a user who is not busy and not the current user
    available_user = db.query(User).filter(
        User.id != user_id,
        User.is_active == True,
        ~User.id.in_(busy_user_ids)
    ).first()
    
    return available_user

def create_chat(db: Session, user1_id: int, user2_id: int) -> AnonymousChat:
    chat = AnonymousChat(
        user1_id=user1_id,
        user2_id=user2_id,
        is_active=True
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

def get_active_chat(db: Session, user_id: int) -> Optional[AnonymousChat]:
    return db.query(AnonymousChat).filter(
        ((AnonymousChat.user1_id == user_id) | (AnonymousChat.user2_id == user_id)),
        AnonymousChat.is_active == True
    ).first()

def end_chat(db: Session, chat_id: int) -> None:
    chat = db.query(AnonymousChat).filter(AnonymousChat.id == chat_id).first()
    if chat:
        chat.is_active = False
        db.commit()

def create_deanon_request(db: Session, chat_id: int) -> DeanonRequest:
    request = DeanonRequest(
        chat_id=chat_id,
        user1_approved=False,
        user2_approved=False
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request

def get_deanon_request(db: Session, chat_id: int) -> Optional[DeanonRequest]:
    return db.query(DeanonRequest).filter(DeanonRequest.chat_id == chat_id).first()

def update_deanon_approval(db: Session, request_id: int, user_position: int, approved: bool) -> DeanonRequest:
    request = db.query(DeanonRequest).filter(DeanonRequest.id == request_id).first()
    if request:
        if user_position == 1:
            request.user1_approved = approved
        elif user_position == 2:
            request.user2_approved = approved
        db.commit()
        db.refresh(request)
    return request