import json
import datetime
import requests
import yfinance as yf
import numpy as np

# 8 pares principales de divisas (sin materias primas)
PAIRS = [
    {"symbol": "EURUSD", "ticker": "EURUSD=X", "base": "EUR", "quote": "USD", "decimals": 5},
    {"symbol": "USDJPY", "ticker": "USDJPY=X", "base": "USD", "quote": "JPY", "decimals": 3},
    {"symbol": "GBPUSD", "ticker": "GBPUSD=X", "base": "GBP", "quote": "USD", "decimals": 5},
    {"symbol": "AUDUSD", "ticker": "AUDUSD=X", "base": "AUD", "quote": "USD", "decimals": 5},
    {"symbol": "NZDUSD", "ticker": "NZDUSD=X", "base": "NZD", "quote": "USD", "decimals": 5},
    {"symbol": "USDCAD", "ticker": "USDCAD=X", "base": "USD", "quote": "CAD", "decimals": 5},
    {"symbol": "USDCHF", "ticker": "USDCHF=X", "base": "USD", "quote": "CHF", "decimals": 5},
    {"symbol": "EURJPY", "ticker": "EURJPY=X", "base": "EUR", "quote": "JPY", "decimals": 3},
]

CENTRAL_BANKS = [
    {"bank": "Fed", "currency": "USD", "rate": "4.50%", "stance": "HAWKISH", "next_meeting": "Dic 2026", "note": "Vigilando persistencia inflacionaria y fortaleza laboral."},
    {"bank": "BCE", "currency": "EUR", "rate": "3.00%", "stance": "DOVISH", "next_meeting": "Dic 2026", "note": "Presión por debilidad manufacturera en la Eurozona."},
    {"bank": "BoJ", "currency": "JPY", "rate": "0.25%", "stance": "NEUTRAL", "next_meeting": "Dic 2026", "note": "Normalización gradual condicionada a salarios internos."},
    {"bank": "BoE", "currency": "GBP", "rate": "4.75%", "stance": "NEUTRAL", "next_meeting": "Dic 2026", "note": "Inflación de servicios mantiene cautela en recortes."},
    {"bank": "RBA", "currency": "AUD", "rate": "4.35%", "stance": "HAWKISH", "next_meeting": "Dic 2026", "note": "Postura restrictiva hasta consolidar meta de inflación."},
    {"bank": "RBNZ", "currency": "NZD", "rate": "4.25%", "stance": "DOVISH", "next_meeting": "Feb 2027", "note": "Ciclo de flexibilización activo ante enfriamiento interno."},
    {"bank": "BoC", "currency": "CAD", "rate": "3.75%", "stance": "DOVISH", "next_meeting": "Dic 2026", "note": "Diferencial de tasas presionando al dólar canadiense."},
    {"bank": "SNB", "currency": "CHF", "rate": "1.00%", "stance": "DOVISH", "next_meeting": "Dic 2026", "note": "Busca contener apreciación excesiva del franco suizo."},
]

def get_ticker_metrics(ticker_str, decimals=2):
    try:
        df = yf.Ticker(ticker_str).history(period="3mo", interval="1d")
        if df.empty or len(df) < 20:
            return None
        close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        change_pct = ((close - prev_close) / prev_close) * 100
        ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
        ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])
        high_20 = float(df["High"].tail(20).max())
        low_20 = float(df["Low"].tail(20).min())
        return {
            "price": round(close, decimals),
            "change_pct": round(change_pct, 2),
            "ema20": round(ema20, decimals),
            "ema50": round(ema50, decimals),
            "high_20": round(high_20, decimals),
            "low_20": round(low_20, decimals),
        }
    except Exception:
        return None

def analyze_pair(pair_cfg):
    df_1h = yf.Ticker(pair_cfg["ticker"]).history(period="1mo", interval="1h")
    dec = pair_cfg["decimals"]
    if df_1h.empty or len(df_1h) < 60:
        return None

    price = float(df_1h["Close"].iloc[-1])
    prev_24h = float(df_1h["Close"].iloc[-24])
    chg_24h = round(((price - prev_24h) / prev_24h) * 100, 2)

    ema50 = float(df_1h["Close"].ewm(span=50).mean().iloc[-1])
    ema200 = float(df_1h["Close"].ewm(span=200).mean().iloc[-1])

    # Rango institucional de las últimas 72 horas (3 días intradía)
    recent_high = float(df_1h["High"].tail(72).max())
    recent_low = float(df_1h["Low"].tail(72).min())
    rng = recent_high - recent_low

    if price > ema50 and ema50 > ema200:
        bias = "ALCISTA"
        summary = f"Estructura alcista sobre EMA50/200 en 1H ({round(ema50, dec)}). Flujo comprador prioriza retrocesos a descuento."
        zone_type = "Demanda / OB Alcista 4H"
        zone_low = round(recent_low + rng * 0.20, dec)
        zone_high = round(recent_low + rng * 0.38, dec)
        target_liq = round(recent_high, dec)
        ultron_note = f"Esperar mitigación en zona de descuento ({zone_low} - {zone_high}) y confirmar CHOCH en 15m/30m hacia liquidez en {target_liq}."
    elif price < ema50 and ema50 < ema200:
        bias = "BAJISTA"
        summary = f"Estructura bajista bajo EMA50/200 en 1H ({round(ema50, dec)}). Presión vendedora domina rebotes a zona premium."
        zone_type = "Oferta / OB Bajista 4H"
        zone_low = round(recent_high - rng * 0.38, dec)
        zone_high = round(recent_high - rng * 0.20, dec)
        target_liq = round(recent_low, dec)
        ultron_note = f"Esperar mitigación en zona premium ({zone_low} - {zone_high}) tras barrido de máximos intradía hacia liquidez en {target_liq}."
    else:
        bias = "NEUTRAL"
        summary = f"Consolidación entre medias móviles 1H ({round(ema50, dec)} / {round(ema200, dec)}). Esperar ruptura con volumen en Londres/NY."
        zone_type = "Rango de Equilibrio"
        zone_low = round(recent_low + rng * 0.35, dec)
        zone_high = round(recent_high - rng * 0.35, dec)
        target_liq = round(recent_high if price > ema200 else recent_low, dec)
        ultron_note = f"Evitar entradas en medio del rango ({zone_low} - {zone_high}); esperar toma de liquidez en extremos ({recent_low} / {recent_high})."

    return {
        "symbol": pair_cfg["symbol"],
        "price": round(price, dec),
        "change_24h": chg_24h,
        "bias": bias,
        "summary": summary,
        "zone_type": zone_type,
        "zone_range": f"{zone_low} - {zone_high}",
        "liquidity_target": target_liq,
        "ultron_note": ultron_note,
    }

def fetch_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    allowed_currencies = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    events = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            raw = resp.json()
            for item in raw:
                if item.get("currency") in allowed_currencies and item.get("impact") in ("High", "Medium"):
                    dt_str = item.get("date", "")
                    date_label = dt_str[:10] if len(dt_str) >= 10 else "Esta semana"
                    time_label = dt_str[11:16] if len(dt_str) >= 16 else "--:--"
                    impact_es = "ALTO IMPACTO" if item.get("impact") == "High" else "MEDIO IMPACTO"
                    forecast = item.get("forecast") or "N/D"
                    previous = item.get("previous") or "N/D"
                    events.append({
                        "date": date_label,
                        "time": time_label,
                        "currency": item.get("currency"),
                        "impact": impact_es,
                        "title": item.get("title"),
                        "note": f"Pronóstico: {forecast} | Anterior: {previous}. Evitar entradas 15 min antes; operar reacción post-barrido."
                    })
    except Exception:
        pass

    if not events:
        events = [{
            "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
            "time": "13:30 UTC",
            "currency": "USD",
            "impact": "ALTO IMPACTO",
            "title": "Datos Macroeconómicos EE.UU. / Sesiones Activas",
            "note": "Verificar calendario antes de apertura de Nueva York para evitar deslizamientos."
        }]
    return events[:14]

def main():
    dxy = get_ticker_metrics("DX-Y.NYB", 2) or {"price": 105.50, "change_pct": 0.0, "ema20": 105.0}
    us10y = get_ticker_metrics("^TNX", 3) or {"price": 4.400, "change_pct": 0.0, "ema20": 4.35}
    brent = get_ticker_metrics("BZ=F", 2) or {"price": 75.00, "change_pct": 0.0, "ema20": 75.0}

    if dxy["price"] > dxy["ema20"] and dxy["change_pct"] >= 0:
        regime = "FORTALEZA DEL DÓLAR · FLUJO DEFENSIVO"
        headline = f"DXY consolida impulso alcista en {dxy['price']} con bono US10Y en {us10y['price']}%"
        macro_body = (
            f"El índice del dólar (DXY) cotiza por encima de su media institucional ({dxy['ema20']}) con variación diaria de {dxy['change_pct']}%. "
            f"Los rendimientos del Tesoro a 10 años en {us10y['price']}% sostienen la demanda institucional por USD frente a divisas con bancos centrales en ciclo de recortes."
        )
    elif dxy["price"] < dxy["ema20"] and dxy["change_pct"] <= 0:
        regime = "DEBILIDAD DEL DÓLAR · APETITO POR RIESGO"
        headline = f"DXY cede presión hasta {dxy['price']} y favorece pares mayores contra el USD"
        macro_body = (
            f"El índice del dólar retrocede por debajo de su referencia de 20 días ({dxy['ema20']}) con cambio de {dxy['change_pct']}%. "
            f"La moderación en el bono US10Y ({us10y['price']}%) libera liquidez hacia divisas principales como EUR, GBP y AUD en sesiones de Londres y Nueva York."
        )
    else:
        regime = "ROTACIÓN INTRADÍA · DIVERGENCIA DE TASAS"
        headline = f"Mercado en equilibrio táctico: DXY en {dxy['price']} y US10Y en {us10y['price']}%"
        macro_body = (
            f"El dólar muestra movimientos mixtos ({dxy['change_pct']}%) mientras el mercado evalúa los diferenciales de tasas entre la Fed, el BCE y el BoJ. "
            f"Priorizar pares con divergencia monetaria clara y esperar barridos de liquidez en apertura de sesión."
        )

    assets = []
    for p in PAIRS:
        res = analyze_pair(p)
        if res:
            assets.append(res)

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "last_updated": now_utc,
        "regime": regime,
        "headline": headline,
        "macro_body": macro_body,
        "metrics": {
            "us10y": f"{us10y['price']}%",
            "us10y_chg": f"{us10y['change_pct']:+}%",
            "dxy": f"{dxy['price']}",
            "dxy_chg": f"{dxy['change_pct']:+}%",
            "brent": f"${brent['price']}",
            "brent_chg": f"{brent['change_pct']:+}%",
        },
        "assets": assets,
        "central_banks": CENTRAL_BANKS,
        "calendar": fetch_calendar()
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
