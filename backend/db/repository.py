from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging_config import get_logger
from .database import get_session_factory
from .models import Domain, DomainMetadata, DomainFeatures

logger = get_logger(__name__)


class DomainRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_domain(
        self,
        domain: str,
        entropy: Optional[float] = None,
        risk_score: str = "Unknown",
        category: str = "Unknown",
        summary: Optional[str] = None,
        is_anomaly: bool = False,
        anomaly_score: float = 0.0,
        analysis_source: str = "unknown",
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
        features: Optional[dict[str, Any]] = None,
    ) -> Domain:
        domain_obj = Domain(
            domain=domain.lower().strip(),
            entropy=entropy,
            risk_score=risk_score,
            category=category,
            summary=summary,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            analysis_source=analysis_source,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        
        self.session.add(domain_obj)
        await self.session.flush()
        
        if metadata:
            metadata_obj = DomainMetadata(
                domain_id=domain_obj.id,
                reason=metadata.get("reason"),
                filter_id=metadata.get("filter_id"),
                rule=metadata.get("rule"),
                client=metadata.get("client"),
            )
            self.session.add(metadata_obj)
        
        if features:
            features_obj = DomainFeatures(
                domain_id=domain_obj.id,
                length=features.get("length", 0),
                digit_ratio=features.get("digit_ratio", 0.0),
                vowel_ratio=features.get("vowel_ratio", 0.0),
                non_alphanumeric=features.get("non_alphanumeric", 0),
            )
            self.session.add(features_obj)
        
        await self.session.refresh(domain_obj)
        
        logger.debug(
            "Domain created",
            extra={"domain": domain, "risk_score": risk_score, "category": category},
        )
        
        return domain_obj

    async def create_domain_from_analysis(self, analysis_result: dict[str, Any]) -> Optional[Domain]:
        domain = analysis_result.get("domain", "")
        
        if not domain:
            logger.warning("Cannot create domain: missing domain name")
            return None
        
        existing = await self.get_domain(domain)
        if existing:
            logger.debug("Domain already exists, skipping", extra={"domain": domain})
            return existing
        
        return await self.create_domain(
            domain=domain,
            entropy=analysis_result.get("entropy"),
            risk_score=analysis_result.get("risk_score", "Unknown"),
            category=analysis_result.get("category", "Unknown"),
            summary=analysis_result.get("summary"),
            is_anomaly=analysis_result.get("is_anomaly", False),
            anomaly_score=analysis_result.get("anomaly_score", 0.0),
            analysis_source=analysis_result.get("analysis_source", "unknown"),
            timestamp=self._parse_timestamp(analysis_result.get("timestamp")),
            metadata=analysis_result.get("adguard_metadata"),
            features=analysis_result.get("features"),
        )

    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        if timestamp is None:
            return None
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, str):
            try:
                if timestamp.endswith("Z"):
                    timestamp = timestamp[:-1] + "+00:00"
                return datetime.fromisoformat(timestamp)
            except ValueError:
                return None
        return None

    async def get_domain(self, domain: str) -> Optional[Domain]:
        result = await self.session.execute(
            select(Domain).where(Domain.domain == domain.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_domain_by_id(self, domain_id: int) -> Optional[Domain]:
        result = await self.session.execute(
            select(Domain).where(Domain.id == domain_id)
        )
        return result.scalar_one_or_none()

    async def get_recent_domains(self, limit: int = 20) -> list[Domain]:
        result = await self.session.execute(
            select(Domain)
            .order_by(Domain.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_domains(self) -> list[Domain]:
        result = await self.session.execute(
            select(Domain).order_by(Domain.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_domain_features(self) -> list[list[float]]:
        result = await self.session.execute(
            select(Domain.entropy, DomainFeatures.length, DomainFeatures.digit_ratio,
                   DomainFeatures.vowel_ratio, DomainFeatures.non_alphanumeric)
            .join(DomainFeatures, Domain.id == DomainFeatures.domain_id, isouter=True)
            .where(and_(
                Domain.entropy.is_not(None),
                DomainFeatures.length.is_not(None)
            ))
        )
        rows = result.all()
        return [[float(x) for x in row] for row in rows if all(x is not None for x in row)]

    async def get_stats(self) -> dict[str, Any]:
        total_result = await self.session.execute(select(func.count(Domain.id)))
        total = total_result.scalar() or 0
        
        anomaly_result = await self.session.execute(
            select(func.count(Domain.id)).where(Domain.is_anomaly.is_(True))
        )
        anomalies = anomaly_result.scalar() or 0
        
        category_result = await self.session.execute(
            select(Domain.category, func.count(Domain.id))
            .group_by(Domain.category)
        )
        categories = {row[0]: row[1] for row in category_result.all()}
        
        source_result = await self.session.execute(
            select(Domain.analysis_source, func.count(Domain.id))
            .group_by(Domain.analysis_source)
        )
        sources = {row[0]: row[1] for row in source_result.all()}
        
        return {
            "total_domains": total,
            "total_anomalies": anomalies,
            "categories": categories,
            "analysis_sources": sources,
        }

    async def domain_exists(self, domain: str) -> bool:
        result = await self.session.execute(
            select(func.count(Domain.id)).where(Domain.domain == domain.lower().strip())
        )
        count = result.scalar() or 0
        return count > 0

    async def delete_domain(self, domain: str) -> bool:
        domain_obj = await self.get_domain(domain)
        if not domain_obj:
            return False
        
        await self.session.delete(domain_obj)
        return True

    async def count_domains(self) -> int:
        result = await self.session.execute(select(func.count(Domain.id)))
        return result.scalar() or 0

    async def count_anomalies(self) -> int:
        result = await self.session.execute(
            select(func.count(Domain.id)).where(Domain.is_anomaly.is_(True))
        )
        return result.scalar() or 0

    async def get_domains_by_category(self, category: str, limit: int = 100) -> list[Domain]:
        result = await self.session.execute(
            select(Domain)
            .where(Domain.category == category)
            .order_by(Domain.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_domains_by_risk(self, risk_score: str, limit: int = 100) -> list[Domain]:
        result = await self.session.execute(
            select(Domain)
            .where(Domain.risk_score == risk_score)
            .order_by(Domain.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_domain_repository() -> DomainRepository:
    factory = get_session_factory()
    session = factory()
    return DomainRepository(session)
