from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.core.logging_config import get_logger
from backend.db.database import get_session
from backend.db.repository import DomainRepository
from backend.db.backup import get_backup_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/database", tags=["database"])


class DomainResponse(BaseModel):
    id: int
    domain: str
    entropy: Optional[float]
    risk_score: str
    category: str
    summary: Optional[str]
    is_anomaly: bool
    anomaly_score: float
    analysis_source: str
    timestamp: Optional[str]
    created_at: Optional[str]
    reason: Optional[str] = None
    filter_id: Optional[int] = None
    rule: Optional[str] = None
    client: Optional[str] = None


class StatsResponse(BaseModel):
    total_domains: int
    total_anomalies: int
    categories: dict[str, int]
    analysis_sources: dict[str, int]


class BackupInfoResponse(BaseModel):
    name: str
    path: str
    size_bytes: int
    size_mb: float
    created_at: str
    compressed: bool


class BackupCreateResponse(BaseModel):
    success: bool
    backup: Optional[BackupInfoResponse] = None
    error: Optional[str] = None


class ExportResponse(BaseModel):
    success: bool
    path: Optional[str] = None
    total_domains: int = 0
    error: Optional[str] = None


@router.get("/stats", response_model=StatsResponse)
async def get_database_stats() -> StatsResponse:
    """Get database statistics."""
    async with get_session() as session:
        repo = DomainRepository(session)
        stats = await repo.get_stats()
        return StatsResponse(**stats)


@router.get("/domains", response_model=List[DomainResponse])
async def list_domains(
    limit: int = Query(20, ge=1, le=1000, description="Maximum domains to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    risk_score: Optional[str] = Query(None, description="Filter by risk score"),
) -> List[DomainResponse]:
    """List recent domains from the database."""
    async with get_session() as session:
        repo = DomainRepository(session)
        
        if category:
            domains = await repo.get_domains_by_category(category, limit)
        elif risk_score:
            domains = await repo.get_domains_by_risk(risk_score, limit)
        else:
            domains = await repo.get_recent_domains(limit)
        
        return [DomainResponse(**d.to_dict()) for d in domains]


@router.get("/domains/{domain}", response_model=DomainResponse)
async def get_domain(domain: str) -> DomainResponse:
    """Get a specific domain by name."""
    async with get_session() as session:
        repo = DomainRepository(session)
        domain_obj = await repo.get_domain(domain)
        
        if not domain_obj:
            raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
        
        return DomainResponse(**domain_obj.to_dict())


@router.delete("/domains/{domain}")
async def delete_domain(domain: str) -> dict[str, Any]:
    """Delete a domain from the database."""
    async with get_session() as session:
        repo = DomainRepository(session)
        deleted = await repo.delete_domain(domain)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
        
        return {"status": "deleted", "domain": domain}


@router.get("/features")
async def get_domain_features() -> dict[str, Any]:
    """Get all domain features for ML training."""
    async with get_session() as session:
        repo = DomainRepository(session)
        features = await repo.get_all_domain_features()
        
        return {
            "total_samples": len(features),
            "feature_count": 5,
            "feature_names": ["entropy", "length", "digit_ratio", "vowel_ratio", "non_alphanumeric"],
        }


@router.post("/backup", response_model=BackupCreateResponse)
async def create_backup() -> BackupCreateResponse:
    """Create a database backup."""
    try:
        backup_manager = get_backup_manager()
        backup_info = await backup_manager.create_backup()
        
        if backup_info:
            return BackupCreateResponse(
                success=True,
                backup=BackupInfoResponse(**backup_info.to_dict()),
            )
        else:
            return BackupCreateResponse(
                success=False,
                error="Failed to create backup - database file not found",
            )
    except Exception as e:
        logger.error("Backup creation failed", extra={"error": str(e)})
        return BackupCreateResponse(success=False, error=str(e))


@router.get("/backups", response_model=List[BackupInfoResponse])
async def list_backups() -> List[BackupInfoResponse]:
    """List all available backups."""
    backup_manager = get_backup_manager()
    backups = await backup_manager.list_backups()
    return [BackupInfoResponse(**b.to_dict()) for b in backups]


@router.post("/restore/{backup_name}")
async def restore_backup(backup_name: str) -> dict[str, Any]:
    """Restore database from a backup."""
    try:
        backup_manager = get_backup_manager()
        success = await backup_manager.restore_backup(backup_name)
        
        if success:
            return {"status": "restored", "backup": backup_name}
        else:
            raise HTTPException(status_code=400, detail="Restore failed")
    except Exception as e:
        logger.error("Restore failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/{backup_name}")
async def delete_backup(backup_name: str) -> dict[str, Any]:
    """Delete a backup file."""
    backup_manager = get_backup_manager()
    deleted = await backup_manager.delete_backup(backup_name)
    
    if deleted:
        return {"status": "deleted", "backup": backup_name}
    else:
        raise HTTPException(status_code=404, detail=f"Backup '{backup_name}' not found")


@router.get("/export")
async def export_database() -> ExportResponse:
    """Export database to JSON file."""
    try:
        from datetime import datetime, timezone
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_path = f"./exports/network_guardian_export_{timestamp}.json"
        
        backup_manager = get_backup_manager()
        success = await backup_manager.export_to_json(export_path)
        
        if success:
            async with get_session() as session:
                repo = DomainRepository(session)
                stats = await repo.get_stats()
            
            return ExportResponse(
                success=True,
                path=export_path,
                total_domains=stats["total_domains"],
            )
        else:
            return ExportResponse(success=False, error="Export failed")
    except Exception as e:
        logger.error("Export failed", extra={"error": str(e)})
        return ExportResponse(success=False, error=str(e))
