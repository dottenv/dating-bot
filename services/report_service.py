from sqlalchemy.orm import Session
from database.models import UserReport, User, AnonymousChat
from typing import Optional, List
from utils.debug import dbg
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# Получаем список ID администраторов из .env
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

def create_report(db: Session, reporter_id: int, reported_user_id: int, chat_id: int, reason: str) -> Optional[UserReport]:
    """Создает новую жалобу на пользователя"""
    try:
        dbg(f"Создание жалобы от пользователя {reporter_id} на пользователя {reported_user_id}", "REPORT")
        
        report = UserReport(
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            chat_id=chat_id,
            reason=reason,
            status="pending"
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        dbg(f"Жалоба создана с ID: {report.id}", "REPORT")
        return report
    except Exception as e:
        dbg(f"Ошибка при создании жалобы: {e}", "REPORT_ERROR")
        db.rollback()
        return None

def get_report_by_id(db: Session, report_id: int) -> Optional[UserReport]:
    """Получает жалобу по ID"""
    try:
        return db.query(UserReport).filter(UserReport.id == report_id).first()
    except Exception as e:
        dbg(f"Ошибка при получении жалобы: {e}", "REPORT_ERROR")
        return None

def get_pending_reports(db: Session) -> List[UserReport]:
    """Получает список нерассмотренных жалоб"""
    try:
        return db.query(UserReport).filter(UserReport.status == "pending").all()
    except Exception as e:
        dbg(f"Ошибка при получении списка жалоб: {e}", "REPORT_ERROR")
        return []

def update_report_status(db: Session, report_id: int, status: str, admin_comment: str = None) -> Optional[UserReport]:
    """Обновляет статус жалобы"""
    try:
        report = db.query(UserReport).filter(UserReport.id == report_id).first()
        if report:
            report.status = status
            if admin_comment:
                report.admin_comment = admin_comment
            report.reviewed_at = datetime.datetime.now()
            
            # Если жалоба принята, обновляем счетчик жалоб на пользователя
            if status == "reviewed":
                update_user_reports_count(db, report.reported_user_id)
                
            db.commit()
            db.refresh(report)
            dbg(f"Статус жалобы ID: {report_id} обновлен на {status}", "REPORT")
            return report
        return None
    except Exception as e:
        dbg(f"Ошибка при обновлении статуса жалобы: {e}", "REPORT_ERROR")
        db.rollback()
        return None

def update_user_reports_count(db: Session, user_id: int) -> None:
    """Обновляет счетчик жалоб на пользователя и его категорию"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # Увеличиваем счетчик жалоб
            user.reports_count += 1
            
            # Обновляем категорию пользователя в зависимости от количества жалоб
            if user.reports_count >= 5:
                user.report_category = "problematic"
            elif user.reports_count >= 2:
                user.report_category = "warning"
            
            db.commit()
            dbg(f"Обновлен счетчик жалоб для пользователя ID: {user_id}, текущее значение: {user.reports_count}, категория: {user.report_category}", "REPORT")
    except Exception as e:
        dbg(f"Ошибка при обновлении счетчика жалоб: {e}", "REPORT_ERROR")
        db.rollback()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def get_chat_partner_id(chat: AnonymousChat, user_id: int) -> Optional[int]:
    """Получает ID собеседника в чате"""
    if chat.user1_id == user_id:
        return chat.user2_id
    elif chat.user2_id == user_id:
        return chat.user1_id
    return None