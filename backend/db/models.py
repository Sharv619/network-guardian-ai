from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(253), unique=True, nullable=False)
    entropy: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="Unknown")
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    analysis_source: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    metadata_entry: Mapped["DomainMetadata"] = relationship(
        "DomainMetadata",
        back_populates="domain",
        uselist=False,
        lazy="selectin",
    )
    features: Mapped["DomainFeatures"] = relationship(
        "DomainFeatures",
        back_populates="domain",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_domains_domain", "domain"),
        Index("idx_domains_created_at", "created_at"),
        Index("idx_domains_category", "category"),
        Index("idx_domains_risk_score", "risk_score"),
        Index("idx_domains_is_anomaly", "is_anomaly"),
    )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "domain": self.domain,
            "entropy": self.entropy,
            "risk_score": self.risk_score,
            "category": self.category,
            "summary": self.summary,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "analysis_source": self.analysis_source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if self.metadata_entry:
            result["reason"] = self.metadata_entry.reason
            result["filter_id"] = self.metadata_entry.filter_id
            result["rule"] = self.metadata_entry.rule
            result["client"] = self.metadata_entry.client

        if self.features:
            result["length"] = self.features.length
            result["digit_ratio"] = self.features.digit_ratio
            result["vowel_ratio"] = self.features.vowel_ratio
            result["non_alphanumeric"] = self.features.non_alphanumeric

        return result


class DomainMetadata(Base):
    __tablename__ = "metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filter_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client: Mapped[str | None] = mapped_column(String(100), nullable=True)

    domain: Mapped["Domain"] = relationship("Domain", back_populates="metadata_entry")

    __table_args__ = (Index("idx_metadata_domain_id", "domain_id"),)


class DomainFeatures(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    digit_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vowel_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    non_alphanumeric: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    domain: Mapped["Domain"] = relationship("Domain", back_populates="features")

    __table_args__ = (Index("idx_features_domain_id", "domain_id"),)


class FeedbackEntry(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_category: Mapped[str] = mapped_column(String(50), nullable=False)
    original_risk_score: Mapped[str] = mapped_column(String(20), nullable=False)
    corrected_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corrected_risk_score: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_feedback_domain_id", "domain_id"),
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_processed", "processed"),
    )


class TLDRReputation(Base):
    __tablename__ = "tld_reputation"

    id: Mapped[int] = mapped_column(primary_key=True)
    tld: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    threat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (Index("idx_tld_reputation_tld", "tld"),)


class TemporalPattern(Base):
    __tablename__ = "temporal_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    threat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    anomaly_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (Index("idx_temporal_hour_day", "hour_of_day", "day_of_week", unique=True),)


class ThreatEntry:
    """Simple data class for API responses - not a database model"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def dict(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith('_')}
