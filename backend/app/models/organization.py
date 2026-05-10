"""Organization model.

An Organization groups one or more Users. Users on a verified work email
domain share a single org for that domain; users on a generic free-mail
domain (gmail.com etc.) get a solo "personal" org. Resources (warehouses,
reports, etc.) remain user-scoped — orgs exist for identity + invitations.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True, unique=True)
    is_personal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("User", back_populates="organization")
