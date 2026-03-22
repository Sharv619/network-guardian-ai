"""
Blocklist API Router - Endpoints for blocklist management and queries.
"""


from fastapi import APIRouter, HTTPException, Request

from backend.services.blocklist_loader import BLOCKLIST_SOURCES, blocklist_loader

router = APIRouter(prefix="", tags=["blocklist"])


@router.get("/status")
async def get_blocklist_status(request: Request):
    """Get current blocklist knowledge base status and statistics for the current tenant."""
    # Get tenant_id from request state (set by TenantMiddleware)
    tenant_id = getattr(request.state, "tenant_id", 1)  # Default to 1 for backward compatibility

    try:
        stats = await blocklist_loader.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get blocklist status: {str(e)}")


@router.get("/sources")
async def get_blocklist_sources():
    """Get list of available blocklist sources."""
    return {
        "sources": BLOCKLIST_SOURCES,
        "total": len(BLOCKLIST_SOURCES),
    }


@router.post("/sync")
async def trigger_sync():
    """Manually trigger a blocklist sync for all enabled sources."""
    try:
        results = await blocklist_loader.sync_all()
        return {
            "success": True,
            "sources_synced": len(results),
            "results": [
                {
                    "source": r.source,
                    "success": r.success,
                    "entries": r.total_entries,
                    "new": r.new_entries,
                    "updated": r.updated_entries,
                    "skipped": r.skipped,
                    "errors": r.errors,
                    "duration_ms": r.duration_ms,
                    "error": r.error_message,
                }
                for r in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync/{source_key}")
async def sync_source(source_key: str):
    """Sync a specific blocklist source."""
    if source_key not in BLOCKLIST_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_key}")

    try:
        result = await blocklist_loader.sync_source(source_key, BLOCKLIST_SOURCES[source_key])
        return {
            "success": result.success,
            "source": result.source,
            "entries": result.total_entries,
            "new": result.new_entries,
            "updated": result.updated_entries,
            "skipped": result.skipped,
            "errors": result.errors,
            "duration_ms": result.duration_ms,
            "error": result.error_message,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/domains")
async def list_domains(
    category: str | None = None,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List blocklist entries with optional filtering."""
    try:
        from sqlalchemy import func, select

        from backend.db.database import get_session
        from backend.db.models import BlocklistEntry

        results = []
        total = 0

        async with get_session() as session:
            query = select(BlocklistEntry)

            if category:
                query = query.where(BlocklistEntry.category == category)
            if source:
                query = query.where(BlocklistEntry.source == source)

            count_query = select(func.count()).select_from(query.subquery())
            total = await session.scalar(count_query) or 0

            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            entries = result.scalars().all()

            for entry in entries:
                results.append(entry.to_dict())

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "entries": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list domains: {str(e)}")


@router.get("/search")
async def search_blocklist(
    query: str,
    limit: int = 50,
):
    """Search blocklist entries by domain, category, or source."""
    try:
        results = await blocklist_loader.search_entries(query, limit)
        return {
            "query": query,
            "total": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/categories")
async def get_categories():
    """Get distribution of entries by category."""
    try:
        stats = await blocklist_loader.get_stats()
        return {
            "categories": stats.get("category_distribution", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/lookup/{domain}")
async def lookup_domain(domain: str):
    """Check if a domain exists in the blocklist knowledge base."""
    try:
        from sqlalchemy import select

        from backend.db.database import get_session
        from backend.db.models import BlocklistEntry

        result = None

        async with get_session() as session:
            query = select(BlocklistEntry).where(BlocklistEntry.domain == domain)
            query_result = await session.execute(query)
            entry = query_result.scalar_one_or_none()

            if entry:
                result = entry.to_dict()

        if result:
            return {
                "found": True,
                "entry": result,
            }
        else:
            return {
                "found": False,
                "domain": domain,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")
