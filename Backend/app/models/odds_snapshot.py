"""
Odds Snapshot model for RF-07
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class OddsSnapshot(SysBase):
    """Odds Snapshot model for storing provider data snapshots"""
    
    __tablename__ = "odds_snapshots"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("app.requests.id", ondelete="CASCADE"), nullable=False, index=True)
    taken_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    request = relationship("Request", foreign_keys=[request_id])
    odds_lines = relationship("OddsLine", back_populates="snapshot", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OddsSnapshot(id={self.id}, request_id={self.request_id}, taken_at={self.taken_at})>"

