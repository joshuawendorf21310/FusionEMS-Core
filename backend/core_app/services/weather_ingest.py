import httpx
from typing import Any, Optional

METAR_URL = "https://aviationweather.gov/api/data/metar"

async def fetch_metar(icao: str) -> Optional[dict[str, Any]]:
    """
    Fetch raw METAR data from aviationweather.gov for a given ICAO code.
    Returns a dictionary with raw text and parsed fields if available, or None.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                METAR_URL,
                params={"ids": icao, "format": "json", "taf": "false"}
            )
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not data or not isinstance(data, list):
                return None
            
            # aviationweather.gov returns a list of metar objects
            metar = data[0]
            
            return {
                "raw_text": metar.get("rawOb", ""),
                "station_id": metar.get("icaoId"),
                "observation_time": metar.get("reportTime"),
                "temp_c": metar.get("temp"),
                "dewpoint_c": metar.get("dewp"),
                "wind_dir": metar.get("wdir"),
                "wind_speed_kt": metar.get("wspd"),
                "visibility_statute_mi": metar.get("visib"),
                "altim_in_hg": metar.get("altim"),
                "flight_category": metar.get("flightCategory"), # VFR, MVFR, IFR, LIFR
            }
    except Exception:
        return None
