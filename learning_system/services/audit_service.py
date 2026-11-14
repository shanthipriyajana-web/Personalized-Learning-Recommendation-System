"""
Audit Service for recording security and compliance events.
Preserves immutable traceability of all administrative and learning decisions.
"""

from learning_system.models import AuditLog


class AuditService:
    @staticmethod
    def log_event(action: str, entity_type: str, entity_id: str, actor=None, details: dict = None, ip_address: str = None) -> AuditLog:
        """
        Records an audit event in the database.
        """
        return AuditLog.objects.create(
            actor=actor if actor and getattr(actor, 'is_authenticated', False) else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=details or {},
            ip_address=ip_address
        )
