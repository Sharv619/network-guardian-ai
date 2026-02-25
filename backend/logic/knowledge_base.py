"""
Knowledge Base System for Network Guardian AI
Combines SQL database with vector embeddings for persistent threat intelligence
"""

import json
import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import sqlite3
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import core modules
from ..core.logging_config import get_logger
from ..core.config import settings

# Import models with lazy loading to avoid circular imports
def get_domain_model():
    from ..db.models import Domain
    return Domain

def get_feedback_entry_model():
    from ..db.models import FeedbackEntry
    return FeedbackEntry

def get_vector_memory():
    from .vector_store import vector_memory, VectorMemory
    return vector_memory, VectorMemory

logger = get_logger(__name__)


@dataclass
class KnowledgeEntry:
    """Represents a knowledge base entry for threat intelligence"""
    domain: str
    risk_score: str
    category: str
    summary: str
    confidence: float
    source: str  # "gemini", "local_ml", "metadata", "heuristic", "human_feedback"
    features: Dict[str, Any]
    timestamp: str
    last_accessed: str = ""
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        return cls(**data)


class KnowledgeBase:
    """Persistent knowledge base combining SQL storage with vector embeddings"""
    
    def __init__(self, db_session: Session, vector_memory):
        self.db = db_session
        self.vector_memory = vector_memory
        self.knowledge_cache: Dict[str, KnowledgeEntry] = {}
        self.cache_lock = threading.Lock()
        self.cache_ttl = 300  # 5 minutes
        self.cache_access_times: Dict[str, float] = {}
        
        # Load existing knowledge into cache
        self._load_persistent_knowledge()
        
    def _load_persistent_knowledge(self):
        """Load existing threat knowledge from database into cache"""
        try:
            # Load recent domains from database
            Domain = get_domain_model()
            domains = self.db.query(Domain).order_by(Domain.created_at.desc()).limit(1000).all()
            
            for domain_obj in domains:
                try:
                    entry = KnowledgeEntry(
                        domain=getattr(domain_obj, 'domain', 'unknown') or "unknown",
                        risk_score=getattr(domain_obj, 'risk_score', 'Unknown') or "Unknown",
                        category=getattr(domain_obj, 'category', 'Unknown') or "Unknown",
                        summary=getattr(domain_obj, 'summary', '') or "",
                        confidence=0.8,  # Default confidence for historical data
                        source=getattr(domain_obj, 'analysis_source', 'database') or "database",
                        features={
                            "entropy": getattr(domain_obj, 'entropy', 0.0) or 0.0,
                            "is_anomaly": getattr(domain_obj, 'is_anomaly', False) or False,
                            "anomaly_score": getattr(domain_obj, 'anomaly_score', 0.0) or 0.0,
                        },
                        timestamp=getattr(domain_obj.timestamp, 'isoformat', lambda: datetime.now(timezone.utc).isoformat())() if getattr(domain_obj, 'timestamp', None) else datetime.now(timezone.utc).isoformat()
                    )
                    
                    cache_key = self._generate_cache_key(getattr(domain_obj, 'domain', 'unknown') or "unknown")
                    with self.cache_lock:
                        self.knowledge_cache[cache_key] = entry
                        self.cache_access_times[cache_key] = time.time()
                    
                except Exception as e:
                    logger.error(f"Error loading domain {getattr(domain_obj, 'domain', 'unknown')} into knowledge cache: {e}")
                    
            logger.info(f"Loaded {len(self.knowledge_cache)} entries into knowledge cache")
            
        except Exception as e:
            logger.error(f"Error loading persistent knowledge: {e}")
    
    def _generate_cache_key(self, domain: str) -> str:
        """Generate cache key for domain"""
        return hashlib.md5(domain.lower().encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache_access_times:
            return False
        return time.time() - self.cache_access_times[cache_key] < self.cache_ttl
    
    def query_knowledge(self, domain: str, context: Optional[Dict] = None, k: int = 5) -> List[Tuple[KnowledgeEntry, float]]:
        """Query knowledge base for similar threats and existing knowledge"""
        results = []
        cache_key = self._generate_cache_key(domain)
        
        # Check cache first
        with self.cache_lock:
            if cache_key in self.knowledge_cache and self._is_cache_valid(cache_key):
                entry = self.knowledge_cache[cache_key]
                entry.access_count += 1
                entry.last_accessed = datetime.now(timezone.utc).isoformat()
                self.cache_access_times[cache_key] = time.time()
                results.append((entry, 1.0))  # Exact match
        
        # Query vector memory for semantic similarity
        context_safe = context or {}
        search_text = f"{domain} {json.dumps(context_safe, sort_keys=True)}" if context_safe else domain
        
        vector_results = self.vector_memory.query_memory(search_text, k=k)
        
        for result in vector_results:
            try:
                similarity = result.get('_similarity_score', 0.0)
                if similarity > 0.7:  # Only return high similarity matches
                    # Safely handle potential None values for metadata
                    metadata = result.get('metadata') or {}
                    if not isinstance(metadata, dict):
                        metadata = {}
                        
                    entry = KnowledgeEntry(
                        domain=result.get('domain', domain) or domain,
                        risk_score=result.get('risk_score', 'Unknown'),
                        category=result.get('category', 'Unknown'),
                        summary=result.get('summary', ''),
                        confidence=similarity,
                        source=result.get('analysis_source', 'vector_match'),
                        features=metadata,
                        timestamp=result.get('timestamp', datetime.now(timezone.utc).isoformat())
                    )
                    results.append((entry, similarity))
            except Exception as e:
                logger.error(f"Error creating knowledge entry from vector result: {e}")
        
        # Sort by similarity/confidence
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
    
    def store_knowledge(self, domain: str, analysis_result: Dict[str, Any], source: str = "gemini"):
        """Store new knowledge in both database and vector memory"""
        try:
            # Create knowledge entry
            entry = KnowledgeEntry(
                domain=domain,
                risk_score=analysis_result.get('risk_score', 'Unknown'),
                category=analysis_result.get('category', 'Unknown'),
                summary=analysis_result.get('summary', ''),
                confidence=analysis_result.get('confidence', 0.9) if source == 'gemini' else 0.8,
                source=source,
                features={
                    'entropy': analysis_result.get('entropy_score'),
                    'anomaly_score': analysis_result.get('anomaly_score'),
                    'digit_ratio': analysis_result.get('digit_ratio'),
                    'is_anomaly': analysis_result.get('is_anomaly', False),
                    'analysis_source': analysis_result.get('analysis_source', source)
                },
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Store in cache
            cache_key = self._generate_cache_key(domain)
            with self.cache_lock:
                self.knowledge_cache[cache_key] = entry
                self.cache_access_times[cache_key] = time.time()
            
            # Store in database
            Domain = get_domain_model()
            domain_obj = Domain(
                domain=domain,
                entropy=analysis_result.get('entropy_score'),
                risk_score=analysis_result.get('risk_score', 'Unknown'),
                category=analysis_result.get('category', 'Unknown'),
                summary=analysis_result.get('summary', ''),
                is_anomaly=analysis_result.get('is_anomaly', False),
                anomaly_score=analysis_result.get('anomaly_score', 0.0),
                analysis_source=source,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.db.add(domain_obj)
            self.db.commit()
            self.db.refresh(domain_obj)
            
            # Store in vector memory for semantic search
            metadata = {
                "domain": domain,
                "risk_score": analysis_result.get('risk_score', 'Unknown'),
                "category": analysis_result.get('category', 'Unknown'),
                "summary": analysis_result.get('summary', ''),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_source": source,
                "entropy": analysis_result.get('entropy_score'),
                "anomaly_score": analysis_result.get('anomaly_score'),
                "is_anomaly": analysis_result.get('is_anomaly', False)
            }
            
            self.vector_memory.add_to_memory(domain, metadata, persist=True)
            
            logger.info(f"Stored knowledge for domain: {domain} (Source: {source})")
            
        except Exception as e:
            logger.error(f"Error storing knowledge for {domain}: {e}")
    
    def get_confidence_score(self, domain: str, context: Optional[Dict] = None) -> Tuple[float, str, str]:
        """Get confidence score and reasoning for a domain from knowledge base"""
        matches = self.query_knowledge(domain, context, k=3)
        
        if not matches:
            return 0.0, "No prior knowledge", "No historical data available"
        
        # Calculate weighted confidence based on matches
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for entry, similarity in matches:
            if entry and hasattr(entry, 'confidence'):
                weight = similarity * entry.confidence
                total_weighted_confidence += weight
                total_weight += weight
        
        if total_weight > 0:
            avg_confidence = total_weighted_confidence / total_weight
        else:
            avg_confidence = 0.0
        
        # Get the best match for reasoning
        best_match = matches[0][0] if matches and len(matches) > 0 else None
        reasoning = f"Similar to {len(matches)} previously analyzed domains. Confidence based on pattern matching."
        
        category = "Unknown"
        if best_match and hasattr(best_match, 'category'):
            category = best_match.category
        
        return avg_confidence, category, reasoning
    
    def learn_from_feedback(self, domain: str, feedback: str, corrected_category: Optional[str] = None, corrected_risk_score: Optional[str] = None):
        """Learn from human feedback and update knowledge base"""
        try:
            # Update the domain in database with feedback
            Domain = get_domain_model()
            FeedbackEntry = get_feedback_entry_model()
            domain_obj = self.db.query(Domain).filter(Domain.domain == domain).first()
            if domain_obj:
                feedback_entry = FeedbackEntry(
                    domain_id=domain_obj.id,
                    feedback_type="correction" if corrected_category else "validation",
                    original_category=domain_obj.category,
                    original_risk_score=domain_obj.risk_score,
                    corrected_category=corrected_category,
                    corrected_risk_score=corrected_risk_score,
                    user_note=feedback,
                    created_at=datetime.now(timezone.utc)
                )
                
                self.db.add(feedback_entry)
                self.db.commit()
                
                # Update the original domain record if corrected
                if corrected_category:
                    domain_obj.category = corrected_category
                if corrected_risk_score:
                    domain_obj.risk_score = corrected_risk_score
                
                self.db.commit()
                
                # Update cache
                cache_key = self._generate_cache_key(domain)
                if cache_key in self.knowledge_cache:
                    entry = self.knowledge_cache[cache_key]
                    if corrected_category:
                        entry.category = corrected_category
                    if corrected_risk_score:
                        entry.risk_score = corrected_risk_score
                    entry.confidence = 0.95  # High confidence from human feedback
                    
                logger.info(f"Learned from feedback for domain: {domain}")
                
        except Exception as e:
            logger.error(f"Error learning from feedback for {domain}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            Domain = get_domain_model()
            
            # Query database with proper error handling
            try:
                db_count = self.db.query(Domain).count()
            except Exception as e:
                logger.warning(f"Database query failed in get_statistics: {e}")
                # Rollback the failed transaction
                self.db.rollback()
                db_count = 0
            
            return {
                "total_knowledge_entries": len(self.knowledge_cache),
                "vector_memory_size": len(self.vector_memory.embeddings),
                "database_domains_count": db_count,
                "recent_learning_rate": len([k for k in self.knowledge_cache.values() if k.source == "human_feedback"]),
                "knowledge_coverage": {
                    "high_confidence": len([k for k in self.knowledge_cache.values() if k.confidence > 0.8]),
                    "medium_confidence": len([k for k in self.knowledge_cache.values() if 0.5 <= k.confidence <= 0.8]),
                    "low_confidence": len([k for k in self.knowledge_cache.values() if k.confidence < 0.5]),
                }
            }
        except Exception as e:
            print(f"Error in get_knowledge_stats: {e}")
            return {
                "total_domains": 0,
                "threat_breakdown": {},
                "avg_risk_score": 0.0,
                "trends": {},
                "threat_timeline": [],
                "recent_domains": [],
                "top_threat_categories": [],
                "anomaly_stats": {},
                "gemini_usage": {},
                "processing_stats": {}
            }


# Global knowledge base instance
_knowledge_base_instance = None
_knowledge_base_lock = threading.Lock()

def get_knowledge_base(db_session: Optional[Session] = None) -> KnowledgeBase:
    """Get knowledge base instance with database session"""
    global _knowledge_base_instance
    
    if db_session is None:
        # For testing/standalone usage, create a synchronous session
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from ..core.config import settings
        
        # Use the same database URL as configured, but synchronous
        sync_url = settings.DATABASE_URL.replace('+asyncpg', '').replace('aiosqlite', 'pysqlite')
        sync_engine = create_engine(sync_url, echo=False)
        SessionLocal = sessionmaker(bind=sync_engine)
        db_session = SessionLocal()
    
    with _knowledge_base_lock:
        if _knowledge_base_instance is None:
            from .vector_store import vector_memory
            _knowledge_base_instance = KnowledgeBase(db_session, vector_memory)
        return _knowledge_base_instance


# Enhanced analysis with knowledge base
def analyze_with_knowledge_base(domain: str, context: Optional[Dict] = None, fallback_to_api: bool = True):
    """Enhanced analysis using knowledge base with fallback options"""
    from ..core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create a synchronous session for this analysis
    sync_engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''), echo=False)
    SessionLocal = sessionmaker(bind=sync_engine)
    db_session = SessionLocal()
    kb = get_knowledge_base(db_session)
    
    try:
        # First, check knowledge base
        matches = kb.query_knowledge(domain, context, k=3)
        
        if matches:
            best_match, similarity = matches[0]
            if similarity > 0.85:  # High confidence match
                logger.info(f"High confidence knowledge base match found for {domain}")
                return {
                    "risk_score": best_match.risk_score,
                    "category": best_match.category,
                    "summary": f"🛡️ KNOWLEDGE BASE MATCH: {best_match.summary}",
                    "confidence": best_match.confidence,
                    "similarity_score": similarity,
                    "analysis_source": "knowledge_base",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            elif similarity > 0.7:  # Medium confidence match
                logger.info(f"Medium confidence knowledge base match found for {domain}")
                # Use as context for API call or local analysis
                context = context or {}
                context["similar_threats"] = [m[0].summary for m in matches]
        
        # If no high confidence match or fallback allowed, proceed with normal analysis
        if fallback_to_api:
            from .ml_heuristics import calculate_entropy, is_dga
            from .anomaly_engine import predict_anomaly
            from ..services.gemini_analyzer import analyze_domain
            
            # Calculate local features
            entropy = calculate_entropy(domain)
            # Use a simple feature extraction since extract_domain_features doesn't exist
            features = [len(domain), sum(c.isdigit() for c in domain) / len(domain) if domain else 0]
            is_anomaly_result, anomaly_score_result = predict_anomaly(features)
            
            # Try Gemini analysis
            try:
                analysis = analyze_domain(
                    domain,
                    context=context,
                    is_anomaly=is_anomaly_result,
                    anomaly_score=anomaly_score_result
                )
                analysis["analysis_source"] = "gemini_api"
                analysis["entropy_score"] = entropy
                analysis["anomaly_score"] = anomaly_score_result
                analysis["is_anomaly"] = is_anomaly_result
                
                # Store in knowledge base
                kb.store_knowledge(domain, analysis, "gemini")
                
                return analysis
            except Exception as e:
                logger.warning(f"Gemini API failed: {e}, falling back to local heuristics")
            
            # Calculate local features
            entropy = calculate_entropy(domain)
            # Use a simple feature extraction since extract_domain_features doesn't exist
            features = [len(domain), sum(c.isdigit() for c in domain) / len(domain) if domain else 0]
            is_anomaly, anomaly_score = predict_anomaly(features)
            
            # Try Gemini analysis
            try:
                analysis = analyze_domain(
                    domain,
                    context=context,
                    is_anomaly=is_anomaly,
                    anomaly_score=anomaly_score
                )
                analysis["analysis_source"] = "gemini_api"
                analysis["entropy_score"] = entropy
                analysis["anomaly_score"] = anomaly_score
                analysis["is_anomaly"] = is_anomaly
                
                # Store in knowledge base
                kb.store_knowledge(domain, analysis, "gemini")
                
                return analysis
            except Exception as e:
                logger.warning(f"Gemini API failed: {e}, falling back to local heuristics")
        
        # Local heuristic fallback
        from .ml_heuristics import is_dga, calculate_entropy
        
        entropy = calculate_entropy(domain)
        
        if is_dga(domain) or entropy > 3.8:
            category = "Malware"
            risk_score = "High"
            summary = f"🛡️ LOCAL HEURISTIC: High Entropy ({entropy:.2f}) or DGA pattern detected"
        else:
            category = "General Traffic"
            risk_score = "Low"
            summary = "🛡️ LOCAL HEURISTIC: No significant risk indicators detected"
        
        result = {
            "risk_score": risk_score,
            "category": category,
            "summary": summary,
            "confidence": 0.7,
            "analysis_source": "local_heuristic",
            "entropy_score": entropy,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store heuristic result in knowledge base
        kb.store_knowledge(domain, result, "local_heuristic")
        
        return result
    finally:
        # Close the session
        db_session.close()


def get_knowledge_stats():
    """Get knowledge base statistics for dashboard"""
    kb = get_knowledge_base()
    return kb.get_statistics()