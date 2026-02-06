"""
Immutable Logger - Tamper-Proof Audit Logging
Uses SHA-256 hashing to ensure logs cannot be altered for 2027 audits.

Each log entry includes:
- SHA-256 hash of content
- Previous entry hash (blockchain-style)
- Timestamp
- Immutable flag
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib
import json


class ImmutableLogEntry(BaseModel):
    """
    Single immutable log entry with cryptographic integrity
    """
    entry_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    log_type: str = Field(description="governance|bias_audit|legal_sandbox|override")
    content: Dict[str, Any]
    
    # Cryptographic integrity
    content_hash: str = Field(description="SHA-256 hash of content")
    previous_hash: Optional[str] = Field(
        default=None,
        description="Hash of previous entry (blockchain-style chaining)"
    )
    chain_index: int = Field(ge=0, description="Position in the chain")
    
    # Audit metadata
    actor_id: Optional[str] = None
    action: str
    resource_id: Optional[str] = None
    
    # Immutability flag
    is_sealed: bool = Field(default=True, description="Entry is sealed and immutable")
    
    class Config:
        frozen = True  # Make the entire object immutable
    
    @classmethod
    def create(
        cls,
        entry_id: str,
        log_type: str,
        content: Dict[str, Any],
        action: str,
        previous_hash: Optional[str] = None,
        chain_index: int = 0,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> "ImmutableLogEntry":
        """
        Create a new immutable log entry with computed hash
        """
        # Serialize content for hashing
        content_json = json.dumps(content, sort_keys=True, default=str)
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        return cls(
            entry_id=entry_id,
            log_type=log_type,
            content=content,
            content_hash=content_hash,
            previous_hash=previous_hash,
            chain_index=chain_index,
            actor_id=actor_id,
            action=action,
            resource_id=resource_id
        )
    
    def verify_integrity(self) -> bool:
        """
        Verify the entry's hash matches its content
        """
        content_json = json.dumps(self.content, sort_keys=True, default=str)
        computed_hash = hashlib.sha256(content_json.encode()).hexdigest()
        return computed_hash == self.content_hash
    
    def get_chain_hash(self) -> str:
        """
        Get hash that includes previous hash (for chaining)
        """
        chain_data = {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'content_hash': self.content_hash,
            'previous_hash': self.previous_hash,
            'chain_index': self.chain_index
        }
        chain_json = json.dumps(chain_data, sort_keys=True)
        return hashlib.sha256(chain_json.encode()).hexdigest()


class ImmutableLogger:
    """
    Immutable logging system with cryptographic verification
    Ensures all governance logs are tamper-proof for regulatory audits
    """
    
    def __init__(self):
        self.log_chain: List[ImmutableLogEntry] = []
        self._last_hash: Optional[str] = None
    
    def append(
        self,
        entry_id: str,
        log_type: str,
        content: Dict[str, Any],
        action: str,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> ImmutableLogEntry:
        """
        Append a new entry to the immutable log chain
        """
        entry = ImmutableLogEntry.create(
            entry_id=entry_id,
            log_type=log_type,
            content=content,
            action=action,
            previous_hash=self._last_hash,
            chain_index=len(self.log_chain),
            actor_id=actor_id,
            resource_id=resource_id
        )
        
        self.log_chain.append(entry)
        self._last_hash = entry.get_chain_hash()
        
        return entry
    
    def verify_chain(self) -> bool:
        """
        Verify the entire log chain for integrity
        Returns False if any entry has been tampered with
        """
        if not self.log_chain:
            return True
        
        # Verify first entry
        if not self.log_chain[0].verify_integrity():
            return False
        
        if self.log_chain[0].previous_hash is not None:
            return False  # First entry should have no previous hash
        
        # Verify chain links
        for i in range(1, len(self.log_chain)):
            current = self.log_chain[i]
            previous = self.log_chain[i - 1]
            
            # Verify content integrity
            if not current.verify_integrity():
                return False
            
            # Verify chain index
            if current.chain_index != i:
                return False
            
            # Verify previous hash matches
            expected_previous = previous.get_chain_hash()
            if current.previous_hash != expected_previous:
                return False
        
        return True
    
    def get_logs(
        self,
        log_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[ImmutableLogEntry]:
        """
        Query logs with filters
        """
        logs = self.log_chain
        
        if log_type:
            logs = [l for l in logs if l.log_type == log_type]
        
        if actor_id:
            logs = [l for l in logs if l.actor_id == actor_id]
        
        if since:
            logs = [l for l in logs if l.timestamp >= since]
        
        return logs
    
    def export_for_audit(self, filepath: str) -> str:
        """
        Export logs to JSON file for regulatory audit
        Includes chain verification proof
        """
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'total_entries': len(self.log_chain),
            'chain_verified': self.verify_chain(),
            'last_hash': self._last_hash,
            'entries': [
                {
                    'entry_id': e.entry_id,
                    'timestamp': e.timestamp.isoformat(),
                    'log_type': e.log_type,
                    'action': e.action,
                    'content': e.content,
                    'content_hash': e.content_hash,
                    'previous_hash': e.previous_hash,
                    'chain_index': e.chain_index,
                    'actor_id': e.actor_id,
                    'resource_id': e.resource_id
                }
                for e in self.log_chain
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        by_type = {}
        for entry in self.log_chain:
            log_type = entry.log_type
            by_type[log_type] = by_type.get(log_type, 0) + 1
        
        return {
            'total_entries': len(self.log_chain),
            'chain_verified': self.verify_chain(),
            'entries_by_type': by_type,
            'last_hash': self._last_hash,
            'chain_length': len(self.log_chain)
        }


# Global singleton instance
_immutable_logger: Optional[ImmutableLogger] = None


def get_immutable_logger() -> ImmutableLogger:
    """Get or create global immutable logger instance"""
    global _immutable_logger
    if _immutable_logger is None:
        _immutable_logger = ImmutableLogger()
    return _immutable_logger
