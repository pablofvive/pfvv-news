import os
import json
from datetime import datetime, timedelta, timezone

import requests

# ========= CONFIGURACIÓN BÁSICA =========

API_KEY = os.environ.get("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

# Lista fija de instrumentos de tu sistema
INSTRUMENTS = [
    "XAUUSD",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "NAS100",
    "SP500",
    "US30",
    "GER40",
]


def fetch_economic_calendar():
    """
    Descarga el calendario económico de Finnhub para hoy + próximos 7 días.
    """
    if not API_KEY:
        raise SystemExit("ERROR: FINNHUB_API_KEY no está definido en variables de entorno")

    today_utc = datetime.utcnow().date()
    to_date = today_utc + timedelta(days=7)

    # Parámetros SOLO con fechas (sin token)
    params = {
        "from": today_utc.isoformat(),
        "to": to_date.isoformat(),
    }

    # Token va en el header obligatorio
    headers = {
        "X-Finnhub-Token": API_KEY
    }

    response = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
    response.raise_for_status()

    data = response.json()
    events = data.get("economicCalendar", []) or []
    return events



def parse_time_to_gmt5(raw_time: str) -> str | None:
    """
    Convierte la hora que envía Finnhub a formato 'YYYY-MM-DD HH:MM'
    en zona horaria GMT-5 (Ecuador).
    """
    if not raw_time:
        return None

    # Puede venir como '2025-01-15 13:30:00' o '2025-01-15T13:30:00+00:00'
    cleaned = raw_time.replace("T", " ")
    cleaned = cleaned.split("+")[0].split("Z")[0].strip()

    dt = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        return None

    # Asumimos UTC y convertimos a GMT-5
    dt_utc = dt.replace(tzinfo=timezone.utc)
    dt_gmt5 = dt_utc - timedelta(hours=5)
    return dt_gmt5.strftime("%Y-%m-%d %H:%M")


def transform_event(e: dict) -> dict | None:
    """
    Transforma un evento de Finnhub al formato PFVV.
    Solo mantenemos eventos de alto impacto.
    """
    impact_raw = (e.get("impact") or "").strip().lower()

    # Nos quedamos solo con eventos de alto impacto
    if impact_raw not in ("high", "major", "importance-high"):
        return None

    raw_time = e.get("time")
    time_gmt5 = parse_time_to_gmt5(raw_time)
    if not time_gmt5:
        return None

    country = (e.get("country") or "").strip()
    title_event = (e.get("event") or "").strip()

    if country and title_event:
        title = f"{country} {title_event}"
    else:
        title = title_event or country or "Economic Event"

    return {
        "symbols": INSTRUMENTS,
        "impact": impact_raw,
        "time_gmt5": time_gmt5,
        "title": title,
    }


def main():
    events_raw = fetch_economic_calendar()

    transformed = []
    for e in events_raw:
        te = transform_event(e)
        if te is not None:
            transformed.append(te)

    # Ordenamos por fecha/hora GMT-5
    def sort_key(ev):
        try:
            return datetime.strptime(ev["time_gmt5"], "%Y-%m-%d %H:%M")
        except Exception:
            return datetime.max

    transformed.sort(key=sort_key)

    # Guardamos EXACTAMENTE en noticias.json
    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump(transformed, f, ensure_ascii=False, indent=2)

    print(f"Guardados {len(transformed)} eventos en noticias.json")


if __name__ == "__main__":
    main()
