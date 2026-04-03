"""
Blocklist Loader Service - Fetches blocklists, parses them, and stores in database.
Handles: AdGuard DNS Filter, EasyList, Steven Black hosts, etc.
"""

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from backend.core.logging_config import get_logger
from backend.db.database import get_session
from backend.db.models import BlocklistEntry, BlocklistSource, BlocklistStats
from backend.logic.blocklist_parser import BlocklistParser, ParsedBlocklistEntry, ParseResult

logger = get_logger(__name__)

BLOCKLIST_SOURCES: dict[str, dict[str, Any]] = {
    "adguard_dns": {
        "name": "AdGuard DNS Filter",
        "url": "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt",
        "category": "ads",
        "enabled": True,
        "parser_type": "adguard",
    },
    "easylist": {
        "name": "EasyList",
        "url": "https://easylist.to/easylist/easylist.txt",
        "category": "ads",
        "enabled": True,
        "parser_type": "easylist",
    },
    "easyprivacy": {
        "name": "EasyPrivacy",
        "url": "https://easylist.to/easylist/easyprivacy.txt",
        "category": "tracking",
        "enabled": True,
        "parser_type": "easyprivacy",
    },
    "steven_black": {
        "name": "Steven Black Hosts",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "category": "malware",
        "enabled": True,
        "parser_type": "hosts",
    },
}


@dataclass
class SyncResult:
    source: str
    success: bool
    total_entries: int
    new_entries: int
    updated_entries: int
    skipped: int
    errors: int
    duration_ms: int
    error_message: str | None = None


class BlocklistLoader:
    def __init__(self):
        self.session: httpx.AsyncClient | None = None
        self._sync_stats: list[SyncResult] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self.session is None or self.session.is_closed:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "Network Guardian AI/1.0"},
            )
        return self.session

    async def close(self):
        if self.session:
            await self.session.aclose()

    async def fetch_filter_list(self, url: str) -> str | None:
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    async def sync_source(self, source_key: str, source_config: dict[str, Any]) -> SyncResult:
        start_time = time.time()
        source_name = source_config["name"]
        url = source_config["url"]
        parser_type = source_config.get("parser_type", "adguard")

        logger.info(f"Syncing blocklist source: {source_name}")

        try:
            content = await self.fetch_filter_list(url)
            if not content:
                return SyncResult(
                    source=source_key,
                    success=False,
                    total_entries=0,
                    new_entries=0,
                    updated_entries=0,
                    skipped=0,
                    errors=1,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_message="Failed to fetch filter list",
                )

            parser = BlocklistParser(source_name=source_key)
            parse_result = parser.parse_content(content)

            logger.info(f"Parsed {len(parse_result.entries)} entries from {source_name}")

            new_count, updated_count = await self._store_entries(parse_result.entries, source_key)

            await self._update_source_status(source_key, parse_result)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Completed sync for {source_name}: "
                f"{new_count} new, {updated_count} updated, {parse_result.skipped} skipped"
            )

            return SyncResult(
                source=source_key,
                success=True,
                total_entries=len(parse_result.entries),
                new_entries=new_count,
                updated_entries=updated_count,
                skipped=parse_result.skipped,
                errors=parse_result.errors,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Error syncing {source_name}: {e}")
            return SyncResult(
                source=source_key,
                success=False,
                total_entries=0,
                new_entries=0,
                updated_entries=0,
                skipped=0,
                errors=1,
                duration_ms=duration_ms,
                error_message=str(e),
            )

    async def _store_entries(
        self, entries: list[ParsedBlocklistEntry], source_key: str
    ) -> tuple[int, int]:
        new_count = 0
        updated_count = 0

        from sqlalchemy import select

        try:
            async with get_session() as session:
                for entry in entries:
                    result = await session.execute(
                        select(BlocklistEntry)
                        .where(
                            BlocklistEntry.domain == entry.domain,
                            BlocklistEntry.source == source_key,
                        )
                        .limit(1)
                    )
                    existing_entry = result.scalars().first()

                    if existing_entry:
                        existing_entry.category = entry.category
                        existing_entry.rule = entry.rule
                        existing_entry.risk_level = entry.risk_level
                        existing_entry.last_updated = datetime.now(UTC)
                        updated_count += 1
                    else:
                        new_entry = BlocklistEntry(
                            tenant_id=1,
                            domain=entry.domain,
                            category=entry.category,
                            source=source_key,
                            rule=entry.rule,
                            risk_level=entry.risk_level,
                        )
                        session.add(new_entry)
                        new_count += 1

                await session.commit()
        except Exception as e:
            logger.error(f"Error storing entries: {e}")

        return new_count, updated_count

    async def _update_source_status(self, source_key: str, parse_result: ParseResult):
        from sqlalchemy import select

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(BlocklistSource).where(BlocklistSource.name == source_key)
                )
                source = result.scalar_one_or_none()

                if source:
                    source.last_sync = datetime.now(UTC)
                    source.entry_count = len(parse_result.entries)
                    source.is_active = True
                else:
                    source = BlocklistSource(
                        name=source_key,
                        url=BLOCKLIST_SOURCES[source_key]["url"],
                        category=BLOCKLIST_SOURCES[source_key]["category"],
                        enabled=True,
                        last_sync=datetime.now(UTC),
                        entry_count=len(parse_result.entries),
                        is_active=True,
                    )
                    session.add(source)

                stats = BlocklistStats(
                    source_name=source_key,
                    total_entries=len(parse_result.entries),
                    new_entries=0,
                    removed_entries=0,
                    sync_duration_ms=0,
                    sync_status="success",
                )
                session.add(stats)

                await session.commit()
        except Exception as e:
            logger.error(f"Error updating source status: {e}")

    async def sync_all(self, enabled_only: bool = True) -> list[SyncResult]:
        results: list[SyncResult] = []

        for source_key, source_config in BLOCKLIST_SOURCES.items():
            if enabled_only and not source_config.get("enabled", True):
                continue

            result = await self.sync_source(source_key, source_config)
            results.append(result)
            self._sync_stats.append(result)

        return results

    async def get_stats(self) -> dict[str, Any]:
        from sqlalchemy import func, select

        try:
            async with get_session() as session:
                total_entries = await session.scalar(select(func.count(BlocklistEntry.id))) or 0

                active_sources = (
                    await session.scalar(
                        select(func.count(BlocklistSource.id)).where(
                            BlocklistSource.is_active == True
                        )
                    )
                    or 0
                )

                last_sync_result = await session.execute(
                    select(BlocklistStats).order_by(BlocklistStats.created_at.desc()).limit(1)
                )
                last_sync = last_sync_result.scalar_one_or_none()

                category_counts = {}
                category_result = await session.execute(
                    select(BlocklistEntry.category, func.count(BlocklistEntry.id)).group_by(
                        BlocklistEntry.category
                    )
                )
                for row in category_result.all():
                    category_counts[row[0]] = row[1]

                return {
                    "total_entries": total_entries,
                    "active_sources": active_sources,
                    "total_sources": len(BLOCKLIST_SOURCES),
                    "last_sync": last_sync.created_at.isoformat() if last_sync else None,
                    "last_sync_status": last_sync.sync_status if last_sync else None,
                    "category_distribution": category_counts,
                    "recent_syncs": [
                        {
                            "source": s.source,
                            "success": s.success,
                            "entries": s.total_entries,
                            "duration_ms": s.duration_ms,
                            "error": s.error_message,
                        }
                        for s in self._sync_stats[-10:]
                    ],
                }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_entries": 0,
                "active_sources": 0,
                "total_sources": len(BLOCKLIST_SOURCES),
                "last_sync": None,
                "error": str(e),
            }

    async def search_entries(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        results = []

        from sqlalchemy import or_, select

        try:
            async with get_session() as session:
                stmt = (
                    select(BlocklistEntry)
                    .where(
                        or_(
                            BlocklistEntry.domain.contains(query),
                            BlocklistEntry.category == query,
                            BlocklistEntry.source == query,
                        )
                    )
                    .limit(limit)
                )

                result = await session.execute(stmt)
                entries = result.scalars().all()

                for entry in entries:
                    results.append(entry.to_dict())
        except Exception as e:
            logger.error(f"Error searching entries: {e}")

        return results

    def get_available_sources(self) -> dict[str, dict[str, Any]]:
        return BLOCKLIST_SOURCES.copy()


blocklist_loader = BlocklistLoader()
