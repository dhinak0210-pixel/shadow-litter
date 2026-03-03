"""
Real ESA Data Space Ecosystem access — no guest accounts.
Required: Copernicus Open Access Hub credentials.
"""

import os
from dataclasses import dataclass
from typing import Optional
import requests
from datetime import datetime, timedelta

@dataclass
class OrbitalCredentials:
    """Real credentials for real satellites."""
    username: str  # Your ESA Data Space login
    password: str  # App password (not main password!)
    client_id: str = "cdse-public"
    token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

class ESAOrbitalConnector:
    """
    Live OAuth2 connection to Copernicus Data Space.
    Tokens expire every 10 minutes — this handles the rebirth.
    """
    
    def __init__(self, creds: OrbitalCredentials):
        # Resolve any environment variable placeholders like ${VAR}
        self.creds = creds
        if self.creds.username.startswith("${") and self.creds.username.endswith("}"):
            env_var = self.creds.username[2:-1]
            self.creds.username = os.getenv(env_var, self.creds.username)
        
        if self.creds.password.startswith("${") and self.creds.password.endswith("}"):
            env_var = self.creds.password[2:-1]
            self.creds.password = os.getenv(env_var, self.creds.password)

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        
    def authenticate(self) -> str:
        """Perform the ritual. Receive the token."""
        response = requests.post(
            self.creds.token_url,
            data={
                "grant_type": "password",
                "client_id": self.creds.client_id,
                "username": self.creds.username,
                "password": self.creds.password
            },
            timeout=30
        )
        response.raise_for_status()
        
        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        self._expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        
        return self._access_token
    
    @property
    def token(self) -> str:
        """Auto-resurrect expired tokens."""
        if not self._access_token or datetime.now() >= self._expires_at:
            return self.authenticate()
        return self._access_token
    
    def get_auth_header(self) -> dict:
        """Ready-to-use header for API calls."""
        return {"Authorization": f"Bearer {self.token}"}


# Usage: Real credentials required
# creds = CopernicusCredentials(
#     username=os.getenv("COPERNICUS_USER"),
#     password=os.getenv("COPERNICUS_PASS")
# )
# auth = ESAAuthenticator(creds)
