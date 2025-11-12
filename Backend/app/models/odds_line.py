"""
Odds Line model for RF-07
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import SysBase

class OddsLine(SysBase):
    """Odds Line model for storing individual odds from providers"""
    
    __tablename__ = "odds_lines"
    __table_args__ = {'schema': 'app'}
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("app.odds_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("app.providers.id", ondelete="RESTRICT"), nullable=True, index=True)  # Nullable porque puede venir de espn
    source = Column(String(50), nullable=False, default="espn")  # "espn", "provider_code", etc.
    line_code = Column(String(100), nullable=False)  # e.g., "home_win", "away_win", "over_2.5"
    price = Column(Numeric(10, 4), nullable=False)  # Decimal odds
    line_metadata = Column(Text, nullable=True)  # JSON con metadatos adicionales
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    snapshot = relationship("OddsSnapshot", back_populates="odds_lines")
    provider = relationship("Provider", back_populates="odds_lines", foreign_keys=[provider_id])
    
    def __repr__(self):
        return f"<OddsLine(id={self.id}, snapshot_id={self.snapshot_id}, line_code='{self.line_code}', price={self.price})>"

