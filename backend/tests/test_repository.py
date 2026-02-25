import pytest
from datetime import datetime, timezone

from backend.db.repository import DomainRepository
from backend.db.models import Domain, DomainMetadata, DomainFeatures


class TestDomainRepository:
    """Tests for DomainRepository database operations."""

    @pytest.fixture
    async def repository(self, temp_db_path):
        """Create repository with temporary in-memory database."""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from backend.db.models import Base

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        repo = DomainRepository(session)

        yield repo

        await session.close()
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_domain_success(self, repository):
        result = await repository.create_domain(
            domain="example.com",
            entropy=3.5,
            risk_score="Low",
            category="General Traffic",
            summary="Safe domain",
            is_anomaly=False,
            anomaly_score=0.0,
            analysis_source="local_heuristic",
        )

        assert result is not None
        assert result.domain == "example.com"
        assert result.entropy == 3.5
        assert result.risk_score == "Low"
        assert result.category == "General Traffic"

    @pytest.mark.asyncio
    async def test_create_domain_with_metadata(self, repository):
        result = await repository.create_domain(
            domain="blocked-site.com",
            entropy=4.2,
            risk_score="High",
            category="Malware",
            summary="Malicious domain",
            metadata={
                "reason": "Blocked",
                "filter_id": 2,
                "rule": "||blocked-site.com^",
                "client": "192.168.1.1",
            },
        )

        assert result is not None
        assert result.metadata_entry is not None
        assert result.metadata_entry.reason == "Blocked"
        assert result.metadata_entry.filter_id == 2

    @pytest.mark.asyncio
    async def test_create_domain_with_features(self, repository):
        result = await repository.create_domain(
            domain="test-domain.net",
            entropy=2.8,
            risk_score="Medium",
            category="Tracker",
            summary="Tracking domain",
            features={
                "length": 15,
                "digit_ratio": 0.0,
                "vowel_ratio": 0.25,
                "non_alphanumeric": 1,
            },
        )

        assert result is not None
        assert result.features is not None
        assert result.features.length == 15
        assert result.features.digit_ratio == 0.0

    @pytest.mark.asyncio
    async def test_create_domain_from_analysis(self, repository, sample_domain_analysis):
        result = await repository.create_domain_from_analysis(sample_domain_analysis)

        assert result is not None
        assert result.domain == sample_domain_analysis["domain"]
        assert result.entropy == sample_domain_analysis["entropy"]

    @pytest.mark.asyncio
    async def test_create_domain_from_analysis_empty(self, repository):
        result = await repository.create_domain_from_analysis({})

        assert result is None

    @pytest.mark.asyncio
    async def test_get_domain_existing(self, repository):
        await repository.create_domain(domain="existing.com", entropy=3.0)

        result = await repository.get_domain("existing.com")

        assert result is not None
        assert result.domain == "existing.com"

    @pytest.mark.asyncio
    async def test_get_domain_not_found(self, repository):
        result = await repository.get_domain("nonexistent.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_domain_case_insensitive(self, repository):
        await repository.create_domain(domain="Example.COM", entropy=3.0)

        result = await repository.get_domain("example.com")

        assert result is not None
        assert result.domain == "example.com"

    @pytest.mark.asyncio
    async def test_get_recent_domains(self, repository):
        for i in range(15):
            await repository.create_domain(
                domain=f"domain{i}.com",
                entropy=3.0 + i * 0.1,
            )

        results = await repository.get_recent_domains(limit=10)

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_get_all_domains(self, repository):
        for i in range(5):
            await repository.create_domain(domain=f"all{i}.com", entropy=3.0)

        results = await repository.get_all_domains()

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_all_domain_features(self, repository):
        for i in range(3):
            await repository.create_domain(
                domain=f"features{i}.com",
                entropy=3.0 + i,
                features={
                    "length": 10 + i,
                    "digit_ratio": 0.1 * i,
                    "vowel_ratio": 0.3,
                    "non_alphanumeric": i,
                },
            )

        features = await repository.get_all_domain_features()

        assert len(features) == 3
        for f in features:
            assert len(f) == 5

    @pytest.mark.asyncio
    async def test_get_stats(self, repository):
        await repository.create_domain(domain="high1.com", entropy=4.0, risk_score="High", category="Malware")
        await repository.create_domain(domain="high2.com", entropy=4.1, risk_score="High", category="Malware")
        await repository.create_domain(domain="low1.com", entropy=2.0, risk_score="Low", category="General Traffic")
        await repository.create_domain(
            domain="anomaly.com",
            entropy=4.5,
            is_anomaly=True,
            anomaly_score=-0.5,
        )

        stats = await repository.get_stats()

        assert stats["total_domains"] == 4
        assert stats["total_anomalies"] == 1
        assert "Malware" in stats["categories"]
        assert "General Traffic" in stats["categories"]

    @pytest.mark.asyncio
    async def test_domain_exists_true(self, repository):
        await repository.create_domain(domain="exists.com", entropy=3.0)

        exists = await repository.domain_exists("exists.com")

        assert exists is True

    @pytest.mark.asyncio
    async def test_domain_exists_false(self, repository):
        exists = await repository.domain_exists("doesnotexist.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_domain_existing(self, repository):
        await repository.create_domain(domain="todelete.com", entropy=3.0)

        deleted = await repository.delete_domain("todelete.com")

        assert deleted is True
        assert await repository.get_domain("todelete.com") is None

    @pytest.mark.asyncio
    async def test_delete_domain_not_found(self, repository):
        deleted = await repository.delete_domain("nonexistent.com")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_count_domains(self, repository):
        for i in range(7):
            await repository.create_domain(domain=f"count{i}.com", entropy=3.0)

        count = await repository.count_domains()

        assert count == 7

    @pytest.mark.asyncio
    async def test_count_anomalies(self, repository):
        await repository.create_domain(domain="normal1.com", entropy=3.0, is_anomaly=False)
        await repository.create_domain(domain="normal2.com", entropy=3.0, is_anomaly=False)
        await repository.create_domain(
            domain="anomaly1.com",
            entropy=4.5,
            is_anomaly=True,
            anomaly_score=-0.5,
        )
        await repository.create_domain(
            domain="anomaly2.com",
            entropy=4.6,
            is_anomaly=True,
            anomaly_score=-0.6,
        )

        count = await repository.count_anomalies()

        assert count == 2

    @pytest.mark.asyncio
    async def test_get_domains_by_category(self, repository):
        await repository.create_domain(domain="malware1.com", entropy=4.0, category="Malware")
        await repository.create_domain(domain="malware2.com", entropy=4.1, category="Malware")
        await repository.create_domain(domain="tracker1.com", entropy=3.0, category="Tracker")

        results = await repository.get_domains_by_category("Malware")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_domains_by_risk(self, repository):
        await repository.create_domain(domain="high1.com", entropy=4.0, risk_score="High")
        await repository.create_domain(domain="high2.com", entropy=4.1, risk_score="High")
        await repository.create_domain(domain="low1.com", entropy=2.0, risk_score="Low")

        results = await repository.get_domains_by_risk("High")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_duplicate_domain_raises_error(self, repository):
        await repository.create_domain(domain="duplicate.com", entropy=3.0)
        
        with pytest.raises(Exception):
            await repository.create_domain(domain="duplicate.com", entropy=4.0)
