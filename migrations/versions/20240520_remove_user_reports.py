"""Remove user_reports table

Revision ID: 20240520_remove_user_reports
Revises: 20240520_rating_system_enhancements
Create Date: 2024-05-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240520_remove_user_reports'
down_revision = '20240520_rating_system_enhancements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование таблицы перед удалением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'user_reports' in tables:
        # Удаляем индекс, если он существует
        try:
            op.drop_index('ix_user_reports_id', table_name='user_reports')
        except:
            pass  # Игнорируем ошибку, если индекс не существует
        
        # Удаляем таблицу
        op.drop_table('user_reports')


def downgrade() -> None:
    # Восстанавливаем таблицу user_reports
    op.create_table('user_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=True),
        sa.Column('reported_user_id', sa.Integer(), nullable=True),
        sa.Column('chat_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_reports_id', 'user_reports', ['id'], unique=False)