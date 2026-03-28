from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AdminAction
from app.admin.schemas import AdminActionCreate, VALID_ACTION_TYPES


class AdminActionService:
    """Service class for AdminAction operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, action_data: AdminActionCreate, admin_id: UUID) -> AdminAction:
        """Create a new admin action log entry."""
        try:
            action = AdminAction(
                admin_id=admin_id,
                action_type=action_data.action_type,
                target_user_id=action_data.target_user_id,
                target_resource_id=action_data.target_resource_id,
                description=action_data.description,
                action_metadata=action_data.action_metadata,
            )
            self.db.add(action)
            self.db.commit()
            self.db.refresh(action)
            return action
        except Exception:
            self.db.rollback()
            raise

    def log_action(
        self,
        admin_id: UUID,
        action_type: str,
        description: str,
        target_user_id: UUID | None = None,
        target_resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdminAction:
        """Convenience method to log an admin action directly."""
        try:
            action = AdminAction(
                admin_id=admin_id,
                action_type=action_type,
                target_user_id=target_user_id,
                target_resource_id=target_resource_id,
                description=description,
                action_metadata=metadata,
            )
            self.db.add(action)
            self.db.commit()
            self.db.refresh(action)
            return action
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, action_id: UUID) -> AdminAction | None:
        """Get a single admin action by ID."""
        return self.db.query(AdminAction).filter(
            AdminAction.id == action_id,
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        admin_id: UUID | None = None,
        action_type: str | None = None,
        target_user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AdminAction]:
        """Get admin actions with optional filtering."""
        query = self.db.query(AdminAction)

        if admin_id:
            query = query.filter(AdminAction.admin_id == admin_id)

        if action_type:
            if action_type in VALID_ACTION_TYPES:
                query = query.filter(AdminAction.action_type == action_type)

        if target_user_id:
            query = query.filter(AdminAction.target_user_id == target_user_id)

        if start_date:
            query = query.filter(AdminAction.created_at >= start_date)

        if end_date:
            query = query.filter(AdminAction.created_at <= end_date)

        return query.order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_admin(
        self,
        admin_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AdminAction]:
        """Get all actions performed by a specific admin."""
        return self.db.query(AdminAction).filter(
            AdminAction.admin_id == admin_id,
        ).order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def get_user_admin_actions(
        self,
        target_user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AdminAction]:
        """Get all admin actions performed on a specific user."""
        return self.db.query(AdminAction).filter(
            AdminAction.target_user_id == target_user_id,
        ).order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_action_type(
        self,
        action_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AdminAction]:
        """Get all actions of a specific type."""
        if action_type not in VALID_ACTION_TYPES:
            return []

        return self.db.query(AdminAction).filter(
            AdminAction.action_type == action_type,
        ).order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_resource(
        self,
        target_resource_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AdminAction]:
        """Get all admin actions performed on a specific resource."""
        return self.db.query(AdminAction).filter(
            AdminAction.target_resource_id == target_resource_id,
        ).order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def count(
        self,
        admin_id: UUID | None = None,
        action_type: str | None = None,
        target_user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count admin actions with optional filtering."""
        query = self.db.query(AdminAction)

        if admin_id:
            query = query.filter(AdminAction.admin_id == admin_id)

        if action_type:
            if action_type in VALID_ACTION_TYPES:
                query = query.filter(AdminAction.action_type == action_type)

        if target_user_id:
            query = query.filter(AdminAction.target_user_id == target_user_id)

        if start_date:
            query = query.filter(AdminAction.created_at >= start_date)

        if end_date:
            query = query.filter(AdminAction.created_at <= end_date)

        return query.count()

    def get_recent(self, limit: int = 10) -> list[AdminAction]:
        """Get the most recent admin actions."""
        return self.db.query(AdminAction).order_by(
            AdminAction.created_at.desc()
        ).limit(limit).all()

    def get_action_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int]:
        """Get count summary by action type using database aggregation."""
        query = self.db.query(
            AdminAction.action_type,
            func.count(AdminAction.id).label('count')
        )

        if start_date:
            query = query.filter(AdminAction.created_at >= start_date)

        if end_date:
            query = query.filter(AdminAction.created_at <= end_date)

        results = query.group_by(AdminAction.action_type).all()

        return {action_type: count for action_type, count in results}