"""DPIE Shared Knowledge and Evidence Engine

Central intelligence layer accessible to all agents. Contains:
- Shared analysis context
- Agent findings
- Evidence records
- Confidence scores
- Dark pattern taxonomy
- Previous investigation results
- Agent execution history
- Structured knowledge references

Agents exchange structured information using these types without
relying on unstructured chat messages.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from datetime import datetime

# Import schema classes - requires dpie package to be installed
from dpie.schemas import (
    EvidenceRecord,
    DarkPatternCategory,
)

try:
    from dpie.config import settings as _settings
except Exception:  # pragma: no cover
    _settings = None


# ---------------------------------------------------------------------------
# In-memory knowledge store (can be replaced with PostgreSQL later)
# ---------------------------------------------------------------------------

class SharedKnowledgeBase:
    """Central shared knowledge base for all agents.
    
    Stores evidence, findings, taxonomy, and investigation history.
    Thread-safe operations for single-process use.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the knowledge base.

        Args:
            db_path: Path to SQLite database. If None, uses in-memory.
        """
        self._memory: Dict[str, Any] = {
            "evidence": {},  # evidence_id -> EvidenceRecord
            "findings": {},  # investigation_id -> List[EvidenceRecord]
            "taxonomy": {},  # category_code -> DarkPatternCategory
            "investigation_history": [],  # List of investigation records
            "agent_execution_log": [],  # List of agent execution records
            "agent_findings_index": {},  # element_id -> [evidence_ids]
        }
        self._lock = threading.RLock()
        self._max_evidence = int(getattr(_settings, "kb_max_evidence", 5000) or 0) if _settings else 5000
        self._max_history = int(getattr(_settings, "kb_max_history", 2000) or 0) if _settings else 2000

        # Initialize SQLite if path provided
        self._db_path = db_path
        self._db_connection: Optional[sqlite3.Connection] = None

        if db_path:
            self._db_connection = sqlite3.connect(db_path, check_same_thread=False)
            self._db_connection.execute(
                "PRAGMA journal_mode=WAL"
            )
            self._initialize_tables()

    def _trim_bounds(self) -> None:
        # Call with lock held when mutating.
        if self._max_evidence and len(self._memory["evidence"]) > self._max_evidence:
            # Drop oldest by insertion order (Python 3.7+ dict order).
            overflow = len(self._memory["evidence"]) - self._max_evidence
            for k in list(self._memory["evidence"].keys())[:overflow]:
                self._memory["evidence"].pop(k, None)
            # Rebuild element index
            idx: Dict[str, List[str]] = {}
            for eid, ev in self._memory["evidence"].items():
                el = ev.get("source_element_id")
                if el:
                    idx.setdefault(el, []).append(eid)
            self._memory["agent_findings_index"] = idx
        if self._max_history:
            for key in ("investigation_history", "agent_execution_log"):
                seq = self._memory.get(key) or []
                if len(seq) > self._max_history:
                    self._memory[key] = seq[-self._max_history:]
    
    def _initialize_tables(self):
        """Initialize SQLite tables."""
        if not self._db_connection:
            return
        
        self._db_connection.executescript("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                source_agent TEXT NOT NULL,
                source_element_id TEXT,
                source_url TEXT,
                element_type TEXT,
                element_selector TEXT,
                element_text TEXT,
                element_attributes TEXT,
                detected_pattern TEXT,
                detected_subcategory TEXT,
                confidence_score REAL,
                evidence_text TEXT,
                visual_properties TEXT,
                interaction_context TEXT,
                risk_score REAL,
                tags TEXT,
                metadata TEXT,
                verified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS taxonomy (
                category_code TEXT PRIMARY KEY,
                category_name TEXT NOT NULL,
                description TEXT,
                subcategories TEXT,
                severity_weight REAL DEFAULT 0.5
            );
            
            CREATE TABLE IF NOT EXISTS investigation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                findings_json TEXT,
                confidence_score REAL,
                risk_score REAL,
                execution_time_ms INTEGER,
                model_used TEXT,
                tokens_consumed INTEGER,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS agent_execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_type TEXT NOT NULL,
                request_id TEXT,
                status TEXT,
                execution_time_ms INTEGER,
                findings_count INTEGER,
                model_used TEXT,
                tokens_consumed INTEGER,
                created_at TEXT NOT NULL
            );
        """)
        
        # Insert default taxonomy
        self._insert_default_taxonomy()
    
    def _insert_default_taxonomy(self):
        """Insert established dark pattern taxonomy."""
        if not self._db_connection:
            return
        
        default_categories = [
            {
                "category_code": "interface_interference",
                "category_name": "Interface Interference",
                "description": "Elements that distract or mislead users by modifying the UI in unexpected ways",
                "subcategories": [
                    "misleading_navigation",
                    "hidden_conditions",
                    "visual_noise",
                ],
                "severity_weight": 0.6,
            },
            {
                "category_code": "obstruction",
                "category_name": "Obstruction",
                "description": "Barriers that make it difficult for users to accomplish their goals",
                "subcategories": [
                    "confirmshaming",
                    "hard_to_cancel",
                    "interface_interference",
                ],
                "severity_weight": 0.7,
            },
            {
                "category_code": "sneaking",
                "category_name": "Sneaking",
                "description": "Deceptive designs that hide, delay, or confuse information",
                "subcategories": [
                    "bait_and_switch",
                    "hidden_costs",
                    "misdirection",
                ],
                "severity_weight": 0.65,
            },
            {
                "category_code": "forced_action",
                "category_name": "Forced Action",
                "description": "Actions forced on users without reasonable alternatives",
                "subcategories": [
                    "mandatory_account_creation",
                    "confirmed_selection",
                    "no_exit_button",
                ],
                "severity_weight": 0.8,
            },
            {
                "category_code": "nagging",
                "category_name": "Nagging",
                "description": "Excessive repeated prompts that annoy or wear down users",
                "subcategories": [
                    "repeated_modals",
                    "continuous_permission_prompts",
                    "countdown_timers",
                ],
                "severity_weight": 0.5,
            },
        ]
        
        for cat in default_categories:
            self.update_taxonomy(
                category_code=cat["category_code"],
                category_name=cat["category_name"],
                description=cat["description"],
                subcategories=cat["subcategories"],
                severity_weight=cat["severity_weight"],
            )
    
    def add_findings_to_kb(self, findings: List[Any]) -> int:
        """Compatibility helper to store findings (batched DB commit when SQLite)."""
        count = 0
        items = list(findings or [])
        if not items:
            return 0
        with self._lock:
            for f in items:
                try:
                    self._store_evidence_inner(f, commit=False)
                    count += 1
                except Exception:
                    continue
            if self._db_connection:
                try:
                    self._db_connection.commit()
                except Exception:
                    pass
            self._trim_bounds()
        return count

    def store_evidence(self, evidence: Any) -> str:
        with self._lock:
            return self._store_evidence_inner(evidence, commit=True)

    def _store_evidence_inner(self, evidence: Any, commit: bool = True) -> str:
        """Store an evidence record (lock must be held by caller or via public API)."""
        # Generate ID if missing
        if not hasattr(evidence, 'evidence_id') or not evidence.evidence_id:
            import hashlib
            evidence_id = hashlib.sha256(
                f"{evidence.source_agent}_{datetime.utcnow()}_{id(evidence)}".encode()
            ).hexdigest()[:16]
            # Make a copy with the ID
            evidence = evidence.model_copy(update={"evidence_id": evidence_id}) if hasattr(evidence, 'model_copy') else evidence

        evidence_id = evidence.evidence_id

        # Store in memory
        self._memory["evidence"][evidence_id] = evidence.model_dump() if hasattr(evidence, 'model_dump') else dict(evidence)

        # Store in SQLite if available
        if self._db_connection:
            self._db_connection.execute(
                """INSERT OR REPLACE INTO evidence
                   (evidence_id, source_agent, source_element_id, source_url,
                    element_type, element_selector, element_text, element_attributes,
                    detected_pattern, detected_subcategory, confidence_score, evidence_text,
                    visual_properties, interaction_context, risk_score, tags, metadata,
                    verified, created_at, updated_at)
                   VALUES (:evidence_id, :source_agent, :source_element_id, :source_url,
                           :element_type, :element_selector, :element_text, :element_attributes,
                           :detected_pattern, :detected_subcategory, :confidence_score, :evidence_text,
                           :visual_properties, :interaction_context, :risk_score, :tags, :metadata,
                           :verified, :created_at, :updated_at)""",
                {
                    "evidence_id": evidence_id,
                    "source_agent": evidence.source_agent.value if hasattr(evidence.source_agent, 'value') else str(evidence.source_agent),
                    "source_element_id": evidence.source_element_id,
                    "source_url": evidence.source_url,
                    "element_type": evidence.element_type,
                    "element_selector": evidence.element_selector,
                    "element_text": evidence.element_text,
                    "element_attributes": json.dumps(evidence.element_attributes) if evidence.element_attributes else None,
                    "detected_pattern": evidence.detected_pattern,
                    "detected_subcategory": evidence.detected_subcategory,
                    "confidence_score": evidence.confidence_score,
                    "evidence_text": evidence.evidence_text,
                    "visual_properties": json.dumps(evidence.visual_properties) if evidence.visual_properties else None,
                    "interaction_context": json.dumps(evidence.interaction_context) if evidence.interaction_context else None,
                    "risk_score": evidence.risk_score,
                    "tags": json.dumps(evidence.tags) if evidence.tags else None,
                    "metadata": json.dumps(evidence.metadata) if evidence.metadata else None,
                    "verified": 1 if evidence.verified else 0,
                    "created_at": evidence.created_at.isoformat(),
                    "updated_at": evidence.updated_at.isoformat(),
                },
            )
            if commit:
                self._db_connection.commit()

        # Index by element for quick lookup
        if evidence.source_element_id:
            if evidence.source_element_id not in self._memory["agent_findings_index"]:
                self._memory["agent_findings_index"][evidence.source_element_id] = []
            self._memory["agent_findings_index"][evidence.source_element_id].append(evidence_id)
        if commit:
            self._trim_bounds()

        return evidence_id
    
    def retrieve_evidence(self, evidence_id: str) -> Optional[Any]:
        """Retrieve an evidence record by ID.

        Args:
            evidence_id: The evidence record ID

        Returns:
            EvidenceRecord or None
        """
        # Check memory first
        if evidence_id in self._memory["evidence"]:
            data = self._memory["evidence"][evidence_id]
            return EvidenceRecord(**data)

        # Check SQLite
        if self._db_connection:
            row = self._db_connection.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
            ).fetchone()
            if row:
                return EvidenceRecord(
                    evidence_id=row[0],
                    source_agent=row[1],
                    source_element_id=row[2],
                    source_url=row[3],
                    element_type=row[4],
                    element_selector=row[5],
                    element_text=row[6],
                    element_attributes=json.loads(row[7]) if row[7] else {},
                    detected_pattern=row[8],
                    detected_subcategory=row[9],
                    confidence_score=row[10],
                    evidence_text=row[11],
                    visual_properties=json.loads(row[12]) if row[12] else None,
                    interaction_context=json.loads(row[13]) if row[13] else None,
                    risk_score=row[14],
                    tags=json.loads(row[15]) if row[15] else [],
                    metadata=json.loads(row[16]) if row[16] else {},
                    verified=bool(row[17]),
                    created_at=datetime.fromisoformat(row[18]) if row[18] else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(row[19]) if row[19] else datetime.utcnow(),
                )

        return None

    def get_evidence(self, evidence_id: str) -> Optional[Any]:
        """Compatibility alias for retrieve_evidence."""
        return self.retrieve_evidence(evidence_id)
    
    def update_evidence(self, evidence: Any) -> bool:
        """Update an existing evidence record.
        
        Args:
            evidence: Updated EvidenceRecord
            
        Returns:
            True if updated successfully
        """
        evidence_id = evidence.evidence_id
        if not evidence_id or evidence_id not in self._memory["evidence"]:
            return False
        
        # Update in memory
        self._memory["evidence"][evidence_id] = evidence.model_dump() if hasattr(evidence, 'model_dump') else dict(evidence)
        
        # Update in SQLite
        if self._db_connection:
            self._db_connection.execute(
                """UPDATE evidence SET 
                   source_agent = :source_agent, source_element_id = :source_element_id,
                   source_url = :source_url, element_type = :element_type,
                   element_selector = :element_selector, element_text = :element_text,
                   element_attributes = :element_attributes, detected_pattern = :detected_pattern,
                   detected_subcategory = :detected_subcategory, confidence_score = :confidence_score,
                   evidence_text = :evidence_text, visual_properties = :visual_properties,
                   interaction_context = :interaction_context, risk_score = :risk_score,
                   tags = :tags, metadata = :metadata, verified = :verified,
                   updated_at = :updated_at
                   WHERE evidence_id = :evidence_id""",
                {
                    "evidence_id": evidence_id,
                    "source_agent": evidence.source_agent.value if hasattr(evidence.source_agent, 'value') else str(evidence.source_agent),
                    "source_element_id": evidence.source_element_id,
                    "source_url": evidence.source_url,
                    "element_type": evidence.element_type,
                    "element_selector": evidence.element_selector,
                    "element_text": evidence.element_text,
                    "element_attributes": json.dumps(evidence.element_attributes) if evidence.element_attributes else None,
                    "detected_pattern": evidence.detected_pattern,
                    "detected_subcategory": evidence.detected_subcategory,
                    "confidence_score": evidence.confidence_score,
                    "evidence_text": evidence.evidence_text,
                    "visual_properties": json.dumps(evidence.visual_properties) if evidence.visual_properties else None,
                    "interaction_context": json.dumps(evidence.interaction_context) if evidence.interaction_context else None,
                    "risk_score": evidence.risk_score,
                    "tags": json.dumps(evidence.tags) if evidence.tags else None,
                    "metadata": json.dumps(evidence.metadata) if evidence.metadata else None,
                    "verified": 1 if evidence.verified else 0,
                    "updated_at": evidence.updated_at.isoformat(),
                },
            )
            self._db_connection.commit()
        
        return True
    
    def delete_evidence(self, evidence_id: str) -> bool:
        """Delete an evidence record.
        
        Args:
            evidence_id: The evidence record ID
            
        Returns:
            True if deleted successfully
        """
        if evidence_id not in self._memory["evidence"]:
            return False
        
        # Remove from memory
        del self._memory["evidence"][evidence_id]
        
        # Remove from index
        for element_id, ids in self._memory["agent_findings_index"].items():
            if evidence_id in ids:
                ids.remove(evidence_id)
        
        # Delete from SQLite
        if self._db_connection:
            self._db_connection.execute(
                "DELETE FROM evidence WHERE evidence_id = ?", (evidence_id,)
            )
            self._db_connection.commit()
        
        return True
    
    # -------------------------------------------------------------------
    # Taxonomy Management
    # -------------------------------------------------------------------
    
    def update_taxonomy(
        self,
        category_code: str,
        category_name: str,
        description: str,
        subcategories: Optional[List[str]] = None,
        severity_weight: float = 0.5,
    ) -> Any:
        """Update or add a dark pattern taxonomy category.
        
        Args:
            category_code: Unique category identifier
            category_name: Human-readable category name
            description: Category description
            subcategories: List of subcategory names
            severity_weight: Severity weight (0-1)
            
        Returns:
            The updated/created DarkPatternCategory
        """
        category = DarkPatternCategory(
            name=category_name,
            code=category_code,
            description=description,
            subcategories=subcategories or [],
            severity_range=f"0.{severity_weight * 10:.0f}-1.0",
        )
        
        # Store in memory
        self._memory["taxonomy"][category_code] = category.model_dump()
        
        # Store in SQLite
        if self._db_connection:
            self._db_connection.execute(
                """INSERT OR REPLACE INTO taxonomy 
                   (category_code, category_name, description, subcategories, severity_weight)
                   VALUES (:category_code, :category_name, :description, :subcategories, :severity_weight)""",
                {
                    "category_code": category_code,
                    "category_name": category_name,
                    "description": description,
                    "subcategories": json.dumps(subcategories or []),
                    "severity_weight": severity_weight,
                },
            )
            self._db_connection.commit()
        
        return category
    
    def get_taxonomy(self, category_code: str) -> Optional[Any]:
        """Get a taxonomy category by code.
        
        Args:
            category_code: Category code
            
        Returns:
            DarkPatternCategory or None
        """
        # Check memory
        if category_code in self._memory["taxonomy"]:
            data = self._memory["taxonomy"][category_code]
            return DarkPatternCategory(**data)
        
        # Check SQLite
        if self._db_connection:
            row = self._db_connection.execute(
                "SELECT * FROM taxonomy WHERE category_code = ?", (category_code,)
            ).fetchone()
            if row:
                return DarkPatternCategory(
                    name=row[1],
                    code=row[0],
                    description=row[2],
                    subcategories=json.loads(row[3]) if row[3] else [],
                    severity_range=f"0.{row[4] * 10:.0f}-1.0",
                )
        
        return None
    
    def list_taxonomy(self) -> List[Any]:
        """List all taxonomy categories."""
        categories = []
        for code in self._memory["taxonomy"]:
            cat = self.get_taxonomy(code)
            if cat:
                categories.append(cat)
        return categories
    
    # -------------------------------------------------------------------
    # Investigation History
    # -------------------------------------------------------------------
    
    def log_investigation(
        self,
        investigation_id: str,
        agent_type: Any,
        findings: List[Any],
        confidence_score: float,
        risk_score: Optional[float] = None,
        execution_time_ms: Optional[int] = None,
        model_used: Optional[str] = None,
        tokens_consumed: Optional[int] = None,
    ):
        """Log an investigation run.
        
        Args:
            investigation_id: Unique investigation identifier
            agent_type: Type of agent that ran
            findings: List of EvidenceRecord findings
            confidence_score: Overall confidence
            risk_score: Overall risk score
            execution_time_ms: Execution time in ms
            model_used: LLM model used
            tokens_consumed: Token count
        """
        # Store findings
        for finding in findings:
            self.store_evidence(finding)
        
        # Log to memory
        log_entry = {
            "investigation_id": investigation_id,
            "agent_type": agent_type.value if hasattr(agent_type, 'value') else str(agent_type),
            "findings_json": json.dumps(
                [f.model_dump() for f in findings], default=str
            ),
            "confidence_score": confidence_score,
            "risk_score": risk_score,
            "execution_time_ms": execution_time_ms or 0,
            "model_used": model_used or "unknown",
            "tokens_consumed": tokens_consumed or 0,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._memory["investigation_history"].append(log_entry)
        
        # Store in SQLite
        if self._db_connection:
            self._db_connection.execute(
                """INSERT INTO investigation_history 
                   (investigation_id, agent_type, findings_json, confidence_score,
                    risk_score, execution_time_ms, model_used, tokens_consumed, created_at)
                   VALUES (:investigation_id, :agent_type, :findings_json, :confidence_score,
                           :risk_score, :execution_time_ms, :model_used, :tokens_consumed, :created_at)""",
                log_entry,
            )
            self._db_connection.commit()
    
    def get_investigation_history(
        self,
        agent_type: Optional[Any] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get investigation history.
        
        Args:
            agent_type: Filter by agent type
            limit: Maximum number of results
            
        Returns:
            List of investigation records
        """
        history = self._memory["investigation_history"]
        if agent_type:
            history = [h for h in history if h["agent_type"] == agent_type.value]
        
        history.sort(key=lambda x: x["created_at"], reverse=True)
        return history[:limit]
    
    # -------------------------------------------------------------------
    # Agent Execution Logging
    # -------------------------------------------------------------------
    
    def log_agent_execution(
        self,
        agent_type: Any,
        request_id: Optional[str],
        status: str,
        execution_time_ms: int,
        findings_count: int,
        model_used: Optional[str] = None,
        tokens_consumed: Optional[int] = None,
    ):
        """Log agent execution.
        
        Args:
            agent_type: Type of agent
            request_id: Related request ID
            status: Execution status
            execution_time_ms: Execution time in ms
            findings_count: Number of findings produced
            model_used: LLM model used
            tokens_consumed: Token count
        """
        log_entry = {
            "agent_type": agent_type.value if hasattr(agent_type, 'value') else str(agent_type),
            "request_id": request_id,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "findings_count": findings_count,
            "model_used": model_used or "unknown",
            "tokens_consumed": tokens_consumed or 0,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        with self._lock:
            self._memory["agent_execution_log"].append(log_entry)
            self._trim_bounds()

        # Store in SQLite
        if self._db_connection:
            self._db_connection.execute(
                """INSERT INTO agent_execution_log
                   (agent_type, request_id, status, execution_time_ms, findings_count,
                    model_used, tokens_consumed, created_at)
                   VALUES (:agent_type, :request_id, :status, :execution_time_ms,
                           :findings_count, :model_used, :tokens_consumed, :created_at)""",
                log_entry,
            )
            self._db_connection.commit()
    
    # -------------------------------------------------------------------
    # Search and Query
    # -------------------------------------------------------------------
    
    def search_evidence_by_pattern(self, pattern: str) -> List[Any]:
        """Search evidence by detected dark pattern pattern.
        
        Args:
            pattern: Pattern name or category code
            
        Returns:
            List of matching EvidenceRecord objects
        """
        results = []
        for evidence in self._memory["evidence"].values():
            if evidence.get("detected_pattern") == pattern:
                results.append(EvidenceRecord(**evidence))
        return results
    
    def search_evidence_by_element(self, element_id: str) -> List[Any]:
        """Search evidence by element ID.
        
        Args:
            element_id: DOM element identifier
            
        Returns:
            List of matching EvidenceRecord objects
        """
        evidence_ids = self._memory["agent_findings_index"].get(element_id, [])
        return [
            self.retrieve_evidence(eid) for eid in evidence_ids
            if self.retrieve_evidence(eid) is not None
        ]
    
    def search_evidence_by_confidence(
        self, min_confidence: float, max_confidence: float = 1.0
    ) -> List[Any]:
        """Search evidence by confidence score range.
        
        Args:
            min_confidence: Minimum confidence (0-1)
            max_confidence: Maximum confidence (0-1)
            
        Returns:
            List of matching EvidenceRecord objects
        """
        results = []
        for evidence in self._memory["evidence"].values():
            confidence = evidence.get("confidence_score", 0)
            if min_confidence <= confidence <= max_confidence:
                results.append(EvidenceRecord(**evidence))
        return results
    
    # -------------------------------------------------------------------
    # Snapshot and Export
    # -------------------------------------------------------------------
    
    def export_snapshot(self) -> Dict[str, Any]:
        """Export a snapshot of the knowledge base.
        
        Returns:
            Dictionary representing the current state
        """
        return {
            "evidence": {
                eid: data for eid, data in self._memory["evidence"].items()
            },
            "taxonomy": {
                code: data for code, data in self._memory["taxonomy"].items()
            },
            "investigation_history_count": len(self._memory["investigation_history"]),
            "agent_execution_log_count": len(self._memory["agent_execution_log"]),
            "agent_findings_index_count": len(self._memory["agent_findings_index"]),
        }
    
    def import_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Import a knowledge base snapshot.
        
        Args:
            snapshot: Snapshot dictionary from export_snapshot()
        """
        # Import evidence
        for evidence_id, data in snapshot.get("evidence", {}).items():
            self._memory["evidence"][evidence_id] = data
        
        # Import taxonomy
        for code, data in snapshot.get("taxonomy", {}).items():
            self._memory["taxonomy"][code] = data
        
        # Import indices (rebuild)
        self._memory["agent_findings_index"] = {}
        for evidence in self._memory["evidence"].values():
            eid = evidence.get("evidence_id", "")
            element_id = evidence.get("source_element_id")
            if element_id and eid:
                if element_id not in self._memory["agent_findings_index"]:
                    self._memory["agent_findings_index"][element_id] = []
                self._memory["agent_findings_index"][element_id].append(eid)
        
        import logging
        logging.getLogger(__name__).info("Knowledge base snapshot imported successfully")


# ---------------------------------------------------------------------------
# Global knowledge base instance
# ---------------------------------------------------------------------------

# Singleton instance - can be replaced with DI in FastAPI
_shared_kb: Optional[SharedKnowledgeBase] = None


def get_knowledge_base() -> SharedKnowledgeBase:
    """Get the global knowledge base instance.
    
    Returns:
        SharedKnowledgeBase singleton
    """
    global _shared_kb
    if _shared_kb is None:
        _shared_kb = SharedKnowledgeBase()
    return _shared_kb


def init_knowledge_base(db_path: Optional[str] = None) -> SharedKnowledgeBase:
    """Initialize or reinitialize the global knowledge base.
    
    Args:
        db_path: Path to SQLite database. If None, uses in-memory.
        
    Returns:
        Initialized SharedKnowledgeBase
    """
    global _shared_kb
    _shared_kb = SharedKnowledgeBase(db_path=db_path)
    return _shared_kb


# ---------------------------------------------------------------------------
# Export useful types
# -------------------------------------------------------------------------__

__all__ = [
    "SharedKnowledgeBase",
    "get_knowledge_base",
    "init_knowledge_base",
    "_shared_kb",
]