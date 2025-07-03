import os
import time
import requests
from datetime import datetime, timedelta
from validadores import verificar_claves_y_datos
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

# 🧱 Obtener nivel de referencia (cierre 15Min entre 09:30–09:45)
def obtener_nivel_15m(ticker, fecha_base):
    inicio = datetime.combine(fecha_base, datetime.strptime("09:30", "%H:%M").time())
    inicio = NY_TZ.localize(inicio)
    fin = inicio + timedelta(minutes=15)
    df = api.get_bars(ticker, "15Min", start=inicio.isoformat(), end=fin.isoformat()).df
    df = df.tz_convert("America/New_York")
    if df.empty:
        print(f"⛔ Sin vela 15Min para {ticker}")
        return None
    return df.iloc[0]["close"]

# 📊 Confirmar condición técnica MACD sin cruce + tolerancia
def confirmar_macd(ticker, momento, direccion):
    timeframes = ["1Min", "5Min", "15Min"]
    confirmados = 0

    for tf in timeframes:
        try:
            inicio = momento - timedelta(minutes=600)
            inicio = NY_TZ.localize(inicio.replace(tzinfo=None))
            fin = NY_TZ.localize(momento.replace(tzinfo=None))
            df = api.get_bars(ticker, tf, start=inicio.isoformat(), end=fin.isoformat()).df
            df = df.tz_convert("America/New_York").dropna().copy()

            if len(df) < 35:
                print(f"· {tf}: ❌ Datos insuficientes — marco excluido")
                continue

            macd = ta.trend.MACD(df["close"])
            df["macd"], df["signal"] = macd.macd(), macd.macd_signal()
            df = df.dropna()
            m1, s1 = df["macd"].iloc[-1], df["signal"].iloc[-1]

            if direccion == "CALL" and m1 > s1:
                confirmados += 1
                print(f"· {tf}: ✅ MACD alineado (CALL)")
            elif direccion == "PUT" and m1 < s1:
                confirmados += 1
                print(f"· {tf}: ✅ MACD alineado (PUT)")
            else:
                print(f"· {tf}: ❌ MACD no alineado")
        except Exception as e:
            print(f"· {tf}: ⚠️ Error técnico → {e}")

    return confirmados >= 2

# 🔁 Loop principal
def run():
    fecha_hoy = datetime.now(NY_TZ).date()
    niveles = {}
    enviados = set()
    print(f"📍 Esperando cierre de vela 15Min...", flush=True)
    while datetime.now(NY_TZ).time() < datetime.strptime("09:46", "%H:%M").time():
        time.sleep(10)

    for ticker in tickers_activos:
        niveles[ticker] = obtener_nivel_15m(ticker, fecha_hoy)

    activos_vivos = tickers_activos[:]
    print("\n🔁 Comenzando escaneo minuto a minuto\n", flush=True)

    while activos_vivos and datetime.now(NY_TZ).time() < datetime.strptime("14:00", "%H:%M").time():
        for ticker in activos_vivos[:]:
            try:
                fin = datetime.now(NY_TZ)
                inicio = fin - timedelta(minutes=3)
                inicio = NY_TZ.localize(inicio.replace(tzinfo=None))
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

                print(f"\n📊 {ticker} ➝ patrón {direccion} detectado — {momento.strftime('%H:%M')}", flush=True)
                if confirmar_macd(ticker, momento, direccion):
                    precio = round(c2, 2)
                    hora = momento.strftime("%H:%M")
                    señal = (
                        f"📈 Estrategia: Breakout Triple MACD\n"
                        f"📊 Ticker: {ticker}\n"
                        f"📌 Señal: {direccion} a las {hora}\n"
                        f"💵 Precio: ${precio}"
                    )
                    print("✅ Señal disparada\n", flush=True)
                    enviar_mensaje(señal)
                    enviados.add(ticker)
                    activos_vivos.remove(ticker)
                else:
                    print("· Señal descartada — MACD insuficiente\n", flush=True)

            except Exception as e:
                print(f"⚠️ Error con {ticker}: {e}", flush=True)

        time.sleep(60)

if __name__ == "__main__":
    print("🔐 Validando entorno Alpaca...")
    if not verificar_claves_y_datos(ALPACA_KEY, ALPACA_SECRET):
        print("⛔ No se pudo iniciar el bot. Revisá claves o suscripción de datos.")
        exit()
    run()


   
              
                  
     
