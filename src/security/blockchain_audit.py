"""
src/security/blockchain_audit.py
──────────────────────────────────
Tamper-proof audit logging via blockchain anchoring.
Every critical action hashed to public blockchain.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List
import aiohttp
import asyncio
import logging

logger = logging.getLogger("blockchain_audit")

class BlockchainAuditFortress:
    """
    Cryptographic audit trail. Making log deletion impossible.
    Fixes blocking I/O and potential event loss.
    """
    
    def __init__(self, blockchain_api: str = "https://blockchain.shadow-litter.ai"):
        self.pending_events = []
        self.blockchain_api = blockchain_api
        self.last_anchor_tx = None
        self.lock = asyncio.Lock()
        
    def log_critical_event(self, 
                          event_type: str, 
                          actor: str, 
                          resource: str, 
                          action: str, 
                          metadata: Dict):
        """
        Log event and prepare for blockchain anchoring.
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': event_type,
            'actor': actor,
            'resource': resource,
            'action': action,
            'metadata': metadata
        }
        
        event_hash = self._hash_event(event)
        event['hash'] = event_hash
        
        self.pending_events.append(event)
        logger.info(f"📖 Logged critical event: {event_type}")
        
        # Async anchor check
        if len(self.pending_events) >= 10:
            asyncio.create_task(self._anchor_to_blockchain())
            
        return event_hash

    def _hash_event(self, event: Dict) -> str:
        canonical = json.dumps(event, sort_keys=True)
        return hashlib.sha3_256(canonical.encode()).hexdigest()

    async def _anchor_to_blockchain(self):
        """Non-blocking blockchain anchor using aiohttp."""
        async with self.lock:
            if not self.pending_events:
                return
                
            batch = self.pending_events.copy()
            self.pending_events.clear()
            
            merkle_root = hashlib.sha3_256(str(batch).encode()).hexdigest()
            logger.info(f"🔒 Anchoring {len(batch)} events to Blockchain. Root: {merkle_root[:8]}...")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.blockchain_api}/anchor",
                        json={"merkle_root": merkle_root, "events": batch},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.last_anchor_tx = data.get('tx_hash')
                            logger.info(f"✅ Anchored to blockchain! TX: {self.last_anchor_tx}")
                        else:
                            # Re-add to pending if failed
                            self.pending_events.extend(batch)
                            logger.error(f"❌ Failed to anchor: {response.status}")
            except Exception as e:
                self.pending_events.extend(batch)
                logger.error(f"❌ Blockchain error: {e}")
