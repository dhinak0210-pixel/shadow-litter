import math
from geopy.geocoders import Nominatim
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger("geo_oracle")

class GeoOracle:
    """
    Global Normalization Engine for Shadow Litter.
    Translates human locations into orbital targeting parameters.
    """
    
    def __init__(self, user_agent="shadow_litter_orbital_intelligence"):
        self.geolocator = Nominatim(user_agent=user_agent)
        
    def resolve_target(self, query: str, radius_km: float = 5.0) -> Optional[Dict]:
        """
        Converts a city/region name into a bounding box and target point.
        """
        logger.info(f"🌍 Resolving global target: {query}")
        
        try:
            location = self.geolocator.geocode(query)
            if not location:
                logger.error(f"❌ Could not resolve location: {query}")
                return None
                
            lat, lon = location.latitude, location.longitude
            
            # Approximate 1 degree latitude = 111.32 km
            # Longitude varies by cos(lat)
            lat_offset = radius_km / 111.32
            lon_offset = radius_km / (111.32 * math.cos(math.radians(lat)))
            
            bbox = {
                "south": lat - lat_offset,
                "north": lat + lat_offset,
                "west": lon - lon_offset,
                "east": lon + lon_offset
            }
            
            # Determine UTM Zone for metric projections (EPSG)
            utm_zone = math.floor((lon + 180) / 6) + 1
            hemisphere = "N" if lat >= 0 else "S"
            utm_epsg = f"EPSG:326{utm_zone}" if hemisphere == "N" else f"EPSG:327{utm_zone}"
            
            return {
                "name": query,
                "display_name": location.address,
                "center_lat": lat,
                "center_lon": lon,
                "bbox": bbox,
                "radius_m": int(radius_km * 1000),
                "utm_zone": f"{utm_zone}{hemisphere}",
                "epsg_code": utm_epsg
            }
            
        except Exception as e:
            logger.error(f"❌ Geocoding error: {e}")
            return None

# Singleton
global_oracle = GeoOracle()
