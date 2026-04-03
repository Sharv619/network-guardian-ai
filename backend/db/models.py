from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subscription_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free"
    )  # free, pro, enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships would be defined in child models via foreign keys

    __table_args__ = (
        Index("idx_tenants_subdomain", "subdomain"),
        Index("idx_tenants_api_key", "api_key"),
    )


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
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
        Index("idx_domains_tenant_id", "tenant_id"),
        Index("idx_domains_tenant_domain", "tenant_id", "domain", unique=True),
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
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filter_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client: Mapped[str | None] = mapped_column(String(100), nullable=True)

    domain: Mapped["Domain"] = relationship("Domain", back_populates="metadata_entry")

    __table_args__ = (
        Index("idx_metadata_domain_id", "domain_id"),
        Index("idx_metadata_tenant_id", "tenant_id"),
    )


class DomainFeatures(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    digit_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vowel_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    non_alphanumeric: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    domain: Mapped["Domain"] = relationship("Domain", back_populates="features")

    __table_args__ = (
        Index("idx_features_domain_id", "domain_id"),
        Index("idx_features_tenant_id", "tenant_id"),
    )


class FeedbackEntry(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
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
        Index("idx_feedback_tenant_id", "tenant_id"),
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_processed", "processed"),
    )


class TLDRReputation(Base):
    __tablename__ = "tld_reputation"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tld: Mapped[str] = mapped_column(String(20), nullable=False)
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    threat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_tld_reputation_tld", "tld"),
        Index("idx_tld_reputation_tenant_id", "tenant_id"),
        Index("idx_tld_reputation_tenant_tld", "tenant_id", "tld", unique=True),
    )


class TemporalPattern(Base):
    __tablename__ = "temporal_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
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

    __table_args__ = (
        Index("idx_temporal_hour_day", "hour_of_day", "day_of_week"),
        Index("idx_temporalpattern_tenant_id", "tenant_id"),
        Index(
            "idx_temporalpattern_tenant_hour_day",
            "tenant_id",
            "hour_of_day",
            "day_of_week",
            unique=True,
        ),
    )


class ThreatEntry:
    """Simple data class for API responses - not a database model"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def dict(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}


class BlocklistSource(Base):
    __tablename__ = "blocklist_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync: Mapped[datetime | None] = mapped_column(nullable=True)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_blocklist_source_name", "name"),
        Index("idx_blocklist_source_tenant_id", "tenant_id"),
        Index("idx_blocklist_source_tenant_name", "tenant_id", "name", unique=True),
    )


class BlocklistEntry(Base):
    __tablename__ = "blocklist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    rule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    first_seen: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_updated: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_blocklist_domain", "domain"),
        Index("idx_blocklist_category", "category"),
        Index("idx_blocklist_source", "source"),
        Index("idx_blocklist_domain_category", "domain", "category"),
        Index("idx_blocklist_tenant_id", "tenant_id"),
        Index("idx_blocklist_tenant_domain", "tenant_id", "domain"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "category": self.category,
            "source": self.source,
            "rule": self.rule,
            "risk_level": self.risk_level,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class BlocklistStats(Base):
    __tablename__ = "blocklist_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    total_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    removed_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sync_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_blocklist_stats_source", "source_name"),
        Index("idx_blocklist_stats_tenant_id", "tenant_id"),
    )


class SystemStats(Base):
    """Persistent key-value store for in-memory counters that need to survive restarts."""

    __tablename__ = "system_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(4000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (Index("idx_system_stats_tenant_key", "tenant_id", "key", unique=True),)
