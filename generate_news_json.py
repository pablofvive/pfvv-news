import os
import requests
import json
from datetime import datetime, timedelta

# 1) Tu API key de FinancialModelingPrep irá en un SECRETO de GitHub:
FMP_API_KEY = os.environ.get("FMP_API_KEY")

# 2) Símbolos que el bot opera y que se ven afectados por noticias de USA
PFVV_SYMBOLS = [
    "EURUSD", "USDJPY", "GBPUSD",
    "XAUUSD", "NAS100", "SP500",
    "US30", "GER40"
]

# 3) Rango de días a futuro que quieres cubrir
DAYS_AHEAD = 10   # próximos 10 días

def fetch_economic_calendar():
    today = datetime.utcnow().date()
    date_from = today.strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")

    url = (
        "https://financialmodelingprep.com/stable/economic-calendar"
        f"?from={date_from}&to={date_to}&apikey={FMP_API_KEY}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def to_pfvv_json(events):
    """
    Convierte la respuesta de FMP al formato EXACTO que tu EA espera.
    """
    result = []

    for ev in events:
        # Filtrar solo USA (puedes ampliar después si quieres)
        if ev.get("country") != "US":
            continue

        # Filtrar solo impacto ALTO
        impact_raw = (ev.get("impact") or "").lower()
        if impact_raw != "high":
            continue

        # Fecha/hora que devuelve FMP, ejemplo "2021-10-18 21:00:00"
        date_str = ev.get("date")
        if not date_str:
            continue

        # Nos quedamos con "YYYY-MM-DD HH:MM"
        time_gmt5 = date_str[:16]

        title = ev.get("event") or "Economic event"

        result.append({
            "symbols": PFVV_SYMBOLS,
            "impact": "high",
            "time_gmt5": time_gmt5,
            "title": title
        })

    return result

def main():
    if not FMP_API_KEY:
        raise RuntimeError("Falta la API key: define FMP_API_KEY como variable de entorno.")

    events = fetch_economic_calendar()
    pfvv_events = to_pfvv_json(events)

    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump(pfvv_events, f, ensure_ascii=False, indent=2)

    print(f"Generadas {len(pfvv_events)} noticias en noticias.json")

if __name__ == "__main__":
    main()
