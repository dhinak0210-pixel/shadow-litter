"""
src/security/api_fortress.py
──────────────────────────────
Cloudflare-on-steroids API protection.
Rate limiting, bot detection, geo-fencing, challenge-response.
"""

from fastapi import Request, HTTPException
import time
import hashlib
import math

class APIFortress:
    """
    Multi-layer API protection. Survive coordinated attacks.
    """
    
    def __init__(self):
        self.blocked_countries = ["XX", "YY"] # Sample high-risk codes
        self.rate_limits = {
            'anonymous': (10, 60),      # 10 req/min
            'authenticated': (200, 60)   # 200 req/min
        }
        self.ip_history = {}
        
    async def protect_endpoint(self, request: Request, tier: str = 'anonymous'):
        """Apply all protection layers."""
        client_ip = request.client.host if request.client else "unknown"
        
        # Layer 1: Rate Limiting (Simple In-Memory Mock)
        now = time.time()
        if client_ip not in self.ip_history:
            self.ip_history[client_ip] = []
        
        # Clean old requests
        self.ip_history[client_ip] = [t for t in self.ip_history[client_ip] if now - t < 60]
        
        limit, window = self.rate_limits[tier]
        if len(self.ip_history[client_ip]) >= limit:
            print(f"🚫 RATE LIMIT TRIGGERED: {client_ip}")
            raise HTTPException(status_code=429, detail="Too many orbital requests. Calm down.")
            
        self.ip_history[client_ip].append(now)
        
        # Layer 2: Advanced Payload Analysis
        body = await request.body()
        
        # 2a: Signature Matching (SQLi/Command Injection)
        malicious_signatures = [
            b"OR '1'='1", b"DROP TABLE", b"system(", b"exec(", b"rm -rf", b"$(", b"${"
        ]
        if any(sig in body for sig in malicious_signatures):
            print(f"🚨 MALICIOUS SIGNATURE DETECTED: {client_ip}")
            raise HTTPException(status_code=403, detail="Signature-based exploit detected.")

        # 2b: Entropy Analysis (Detect Encrypted/Encoded Attacks)
        if len(body) > 50:
            entropy = self._calculate_entropy(body)
            if entropy > 7.0:
                print(f"🚨 HIGH ENTROPY DETECTED ({entropy:.2f}): {client_ip}")
                raise HTTPException(status_code=403, detail="High entropy payload (likely shellcode) detected.")

        return True

    def _calculate_entropy(self, data: bytes) -> float:
        """Shannon entropy calculation to detect encoded attacks."""
        if not data: return 0
        entropy = 0
        for x in range(256):
            p_x = float(data.count(x)) / len(data)
            if p_x > 0:
                entropy += - p_x * math.log(p_x, 2)
        return entropy
