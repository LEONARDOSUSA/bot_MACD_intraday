import os
import time
import requests
from datetime import datetime, timedelta
import pandas as pd
import alpaca_trade_api as tradeapi
import pytz
import ta

# 🔐 Configuración
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://paper-api.alpaca.markets"
api = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, base_url=BASE_URL)
NY_TZ = pytz.timezone("America/New_York")
tickers_activos = ["AAPL", "SPY", "TSLA", "MSFT", "NVDA", "AMD"]

# 📨 Enviar mensaje por Telegram
def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

# 🧱 Obtener nivel de referencia de vela 15M (9:30–9:45)
def obtener_nivel_15m(ticker, fecha_base):
    inicio = NY_TZ.localize(datetime.combine(fecha_base, datetime.strptime("09:30", "%H:%M").time()))
    fin = inicio + timedelta(minutes=15)
    df = api.get_bars(ticker, "15Min", start=inicio.isoformat(), end=fin.isoformat()).df
    df = df.tz_convert("America/New_York")
    if df.empty:
        print(f"⛔ Sin vela 15M para {ticker}")
        return None
    return df.iloc[0]["close"]

# 🧠 Confirmar alineación MACD
def confirmar_macd(ticker, momento, direccion):
    timeframes = ["1Min", "5Min", "15Min"]
    for tf in timeframes:
        inicio = momento - timedelta(minutes=100)
        df = api.get_bars(ticker, tf, start=inicio.isoformat(), end=momento.isoformat()).df
        df = df.tz_convert("America/New_York")
        if len(df) < 35:
            return False

        macd = ta.trend.MACD(df["close"])
        df["macd"], df["signal"] = macd.macd(), macd.macd_signal()

        m0, m1 = df["macd"].iloc[-2], df["macd"].iloc[-1]
        s0, s1 = df["signal"].iloc[-2], df["signal"].iloc[-1]

        if direccion == "CALL" and not (m0 < s0 and m1 > s1):
            return False
        if direccion == "PUT" and not (m0 > s0 and m1 < s1):
            return False
    return True

# 🔁 Loop principal
def run():
    fecha_hoy = datetime.now(NY_TZ).date()
    niveles = {}

    print(f"📍 Esperando cierre de vela 15M...", flush=True)
    while datetime.now(NY_TZ).time() < datetime.strptime("09:46", "%H:%M").time():
        time.sleep(10)

    for ticker in tickers_activos:
        niveles[ticker] = obtener_nivel_15m(ticker, fecha_hoy)

    activos_vivos = tickers_activos[:]

    print("🔁 Comenzando escaneo minuto a minuto\n", flush=True)
    while activos_vivos and datetime.now(NY_TZ).time() < datetime.strptime("14:00", "%H:%M").time():
        for ticker in activos_vivos[:]:
            try:
                fin = datetime.now(NY_TZ)
                inicio = fin - timedelta(minutes=3)
                df = api.get_bars(ticker, "1Min", start=inicio.isoformat(), end=fin.isoformat()).df
                df = df.tz_convert("America/New_York")
                if len(df) < 3:
                    continue

                c1 = df["close"].iloc[-3]
                c2 = df["close"].iloc[-2]
                momento = df.index[-2].to_pydatetime()
                nivel = niveles[ticker]

                if c1 > nivel and c2 > nivel:
                    direccion = "CALL"
                elif c1 < nivel and c2 < nivel:
                    direccion = "PUT"
                else:
                    continue

                print(f"📊 {ticker} ➝ patrón {direccion} detectado — {momento.strftime('%H:%M')}", flush=True)

                if confirmar_macd(ticker, momento, direccion):
                    precio = round(c2, 2)
                    hora = momento.strftime("%H:%M")
                    señal = (
                        f"📈 Estrategia: Breakout Triple MACD\n"
                        f"📊 Ticker: {ticker}\n"
                        f"📌 Señal: {direccion} a las {hora}\n"
                        f"💵 Precio: ${precio}"
                    )
                    print(f"✅ {señal}", flush=True)
                    enviar_mensaje(señal)
                    activos_vivos.remove(ticker)
                else:
                    print(f"· MACD no alineado para {ticker}", flush=True)

            except Exception as e:
                print(f"⚠️ Error con {ticker}: {e}", flush=True)

        time.sleep(60)

if __name__ == "__main__":
enviar_mensaje("🧪 Test de conexión: el bot puede comunicarse con Telegram.")
     run()  ← lo dejás comentado por ahora, solo para esta prueba 

