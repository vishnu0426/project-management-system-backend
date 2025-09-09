"""
Database type compatibility layer for SQLite/PostgreSQL
"""
from sqlalchemy import String, JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type when available,
    otherwise uses CHAR(36) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=False, **kwargs):
        self.as_uuid = as_uuid
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# For compatibility with existing code
def UUID_PK():
    """UUID primary key with default"""
    return UUID(as_uuid=True)


# Export commonly used types
__all__ = ['UUID', 'UUID_PK', 'JSON']
