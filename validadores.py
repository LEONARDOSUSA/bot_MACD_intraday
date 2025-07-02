# validadores.py
import requests
from datetime import datetime, timedelta
import pytz

def verificar_claves_y_datos(api_key, secret_key):
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key
    }

    # Verifica conexión con la API de trading (get_clock)
    try:
        clock = requests.get("https://paper-api.alpaca.markets/v2/clock", headers=headers)
        if clock.status_code != 200:
            print(f"❌ Error con claves de trading: {clock.status_code}")
            return False
    except Exception as e:
        print(f"🚫 Error conectando a clock: {e}")
        return False

    # Verifica acceso a datos de mercado
    try:
        eastern = pytz.timezone("US/Eastern")
        ayer = datetime.now(tz=eastern) - timedelta(days=1)
        start = ayer.replace(hour=9, minute=30, second=0, microsecond=0).isoformat()
        end = ayer.replace(hour=9, minute=45, second=0, microsecond=0).isoformat()

        params = {
            "timeframe": "15Min",
            "adjustment": "raw",
            "start": start,
            "end": end
        }

        resp = requests.get("https://data.alpaca.markets/v2/stocks/AAPL/bars", headers=headers, params=params)
        if resp.status_code != 200:
            print(f"❌ Error con datos de mercado: {resp.status_code}")
            return False
    except Exception as e:
        print(f"🚫 Error accediendo a datos: {e}")
        return False

    print("✅ Verificación de claves y datos completada.")
    return True
