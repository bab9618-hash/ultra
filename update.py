import json
import datetime
import requests
import yfinance as yf

DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

PAIRS = [
    {"symbol": "EURUSD", "ticker": "EURUSD=X", "base": "EUR", "quote": "USD", "decimals": 5, "pip": 0.0001},
    {"symbol": "USDJPY", "ticker": "USDJPY=X", "base": "USD", "quote": "JPY", "decimals": 3, "pip": 0.01},
    {"symbol": "GBPUSD", "ticker": "GBPUSD=X", "base": "GBP", "quote": "USD", "decimals": 5, "pip": 0.0001},
    {"symbol": "AUDUSD", "ticker": "AUDUSD=X", "base": "AUD", "quote": "USD", "decimals": 5, "pip": 0.0001},
    {"symbol": "NZDUSD", "ticker": "NZDUSD=X", "base": "NZD", "quote": "USD", "decimals": 5, "pip": 0.0001},
    {"symbol": "USDCAD", "ticker": "USDCAD=X", "base": "USD", "quote": "CAD", "decimals": 5, "pip": 0.0001},
    {"symbol": "USDCHF", "ticker": "USDCHF=X", "base": "USD", "quote": "CHF", "decimals": 5, "pip": 0.0001},
    {"symbol": "EURJPY", "ticker": "EURJPY=X", "base": "EUR", "quote": "JPY", "decimals": 3, "pip": 0.01},
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
        return {
            "price": round(close, decimals),
            "change_pct": round(change_pct, 2),
            "ema20": round(ema20, decimals),
            "ema50": round(ema50, decimals),
        }
    except Exception:
        return None

def find_intraday_ob(df_1h, bias, price, day_high, day_low, dec):
    # Busca el último Order Block real en 1H dentro de las últimas 28 horas
    recent = df_1h.tail(28)
    if bias == "BAJISTA":
        for i in range(len(recent) - 2, 0, -1):
            c_open = float(recent["Open"].iloc[i])
            c_close = float(recent["Close"].iloc[i])
            c_high = float(recent["High"].iloc[i])
            next_close = float(recent["Close"].iloc[i + 1])
            # Última vela alcista antes de impulso bajista por encima del precio actual
            if c_close > c_open and next_close < c_open and c_high > price:
                return round(c_open, dec), round(c_high, dec)
        # Respaldo: techo intradía de las últimas 24h
        rng = day_high - day_low
        return round(day_high - rng * 0.18, dec), round(day_high, dec)

    elif bias == "ALCISTA":
        for i in range(len(recent) - 2, 0, -1):
            c_open = float(recent["Open"].iloc[i])
            c_close = float(recent["Close"].iloc[i])
            c_low = float(recent["Low"].iloc[i])
            next_close = float(recent["Close"].iloc[i + 1])
            # Última vela bajista antes de impulso alcista por debajo del precio actual
            if c_close < c_open and next_close > c_open and c_low < price:
                return round(c_low, dec), round(c_open, dec)
        # Respaldo: suelo intradía de las últimas 24h
        rng = day_high - day_low
        return round(day_low, dec), round(day_low + rng * 0.18, dec)

    rng = day_high - day_low
    return round(day_low + rng * 0.35, dec), round(day_high - rng * 0.35, dec)

def analyze_pair(pair_cfg):
    df_1h = yf.Ticker(pair_cfg["ticker"]).history(period="15d", interval="1h")
    df_15m = yf.Ticker(pair_cfg["ticker"]).history(period="5d", interval="15m")
    dec = pair_cfg["decimals"]
    pip = pair_cfg["pip"]

    if df_1h.empty or len(df_1h) < 50 or df_15m.empty:
        return None

    price = float(df_15m["Close"].iloc[-1])
    prev_24h = float(df_1h["Close"].iloc[-24])
    chg_24h = round(((price - prev_24h) / prev_24h) * 100, 2)

    ema20 = float(df_1h["Close"].ewm(span=20).mean().iloc[-1])
    ema50 = float(df_1h["Close"].ewm(span=50).mean().iloc[-1])

    # Rango intradía real de las últimas 24 horas (96 velas de 15m)
    day_high = float(df_15m["High"].tail(96).max())
    day_low = float(df_15m["Low"].tail(96).min())

    today_idx = datetime.datetime.now(datetime.timezone.utc).weekday()
    day_en = DAYS_EN[today_idx]

    if price > ema20 and ema20 > ema50:
        bias = "ALCISTA"
        summary = f"Estructura intradía alcista sobre EMA20/50 en 1H ({round(ema20, dec)}). Priorizar compras en retroceso de sesión."
        zone_type = f"OB Demanda 1H ({day_en})"
        zone_low, zone_high = find_intraday_ob(df_1h, bias, price, day_high, day_low, dec)
        target_liq = f"{round(day_high, dec)} (High {day_en})"
        dist_pips = max(0.0, round((price - zone_high) / pip, 1))
        ultron_note = f"Esperar mitigación en OB intradía ({zone_low} - {zone_high}) y confirmar CHOCH en 15m/5m hacia liquidez en {round(day_high, dec)}."
        if dist_pips <= 5:
            jarvis_action = "EN ZONA DE GATILLO · BUSCAR CHOCH 15m/5m"
            jarvis_detail = f"El precio está tocando tu Order Block intradía ({zone_low}-{zone_high}). Valida absorción en Delta y quiebre alcista antes de entrar."
        else:
            jarvis_action = f"ESPERAR RETROCESO ({dist_pips} PIPS)"
            jarvis_detail = f"El precio está a {dist_pips} pips de tu Order Block de demanda ({zone_low}-{zone_high}). No compres arriba; espera el descuento."

    elif price < ema20 and ema20 < ema50:
        bias = "BAJISTA"
        summary = f"Estructura intradía bajista bajo EMA20/50 en 1H ({round(ema20, dec)}). Priorizar ventas tras barrido de máximos."
        zone_type = f"OB Oferta 1H ({day_en})"
        zone_low, zone_high = find_intraday_ob(df_1h, bias, price, day_high, day_low, dec)
        target_liq = f"{round(day_low, dec)} (Low {day_en})"
        dist_pips = max(0.0, round((zone_low - price) / pip, 1))
        ultron_note = f"Esperar mitigación en OB de oferta ({zone_low} - {zone_high}) tras barrido intradía hacia liquidez en {round(day_low, dec)}."
        if dist_pips <= 5:
            jarvis_action = "EN ZONA DE GATILLO · BUSCAR CHOCH 15m/5m"
            jarvis_detail = f"El precio está dentro de tu Order Block de oferta ({zone_low}-{zone_high}). Busca rechazo y CHOCH bajista en 15m/5m."
        else:
            jarvis_action = f"ESPERAR REBOTE ({dist_pips} PIPS)"
            jarvis_detail = f"El precio está a {dist_pips} pips por debajo de la oferta intradía ({zone_low}-{zone_high}). Evita vender en suelos; espera mitigación arriba."

    else:
        bias = "NEUTRAL"
        summary = f"Rango intradía entre EMA20/50 1H ({round(ema20, dec)} / {round(ema50, dec)}). Esperar barrido de extremos de sesión."
        zone_type = f"Rango Intraday ({day_en})"
        zone_low, zone_high = find_intraday_ob(df_1h, bias, price, day_high, day_low, dec)
        liq_val = round(day_high if price > ema50 else day_low, dec)
        target_liq = f"{liq_val} ({day_en})"
        ultron_note = f"Evitar operar en medio del rango ({zone_low} - {zone_high}); esperar toma de liquidez en extremos de sesión ({round(day_low, dec)} / {round(day_high, dec)})."
        jarvis_action = "NO OPERAR EN RANGO · ESPERAR BARRIDO"
        jarvis_detail = f"Sin dirección clara en 1H. Espera a que el precio barra {round(day_high, dec)} o {round(day_low, dec)} y confirme reversión."

    return {
        "symbol": pair_cfg["symbol"],
        "base": pair_cfg["base"],
        "quote": pair_cfg["quote"],
        "decimals": dec,
        "pip": pip,
        "price": round(price, dec),
        "change_24h": chg_24h,
        "bias": bias,
        "summary": summary,
        "zone_type": zone_type,
        "zone_range": f"{zone_low} - {zone_high}",
        "liquidity_target": target_liq,
        "ultron_note": ultron_note,
        "jarvis_action": jarvis_action,
        "jarvis_detail": jarvis_detail,
    }

def fetch_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    allowed_currencies = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    events = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            raw = resp.json()
            for item in raw:
                if item.get("currency") in allowed_currencies and item.get("impact") in ("High", "Medium"):
                    dt_str = item.get("date", "")
                    date_iso = dt_str[:10] if len(dt_str) >= 10 else ""
                    time_label = dt_str[11:16] if len(dt_str) >= 16 else "--:--"
                    try:
                        d_obj = datetime.date.fromisoformat(date_iso)
                        day_label = f"{DAYS_EN[d_obj.weekday()].upper()} ({DAYS_ES[d_obj.weekday()]})"
                        hoy_tag = " · HOY" if d_obj == today_utc else ""
                        date_label = f"{day_label} · {date_iso}{hoy_tag}"
                    except Exception:
                        date_label = date_iso or "Esta semana"

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
        idx = today_utc.weekday()
        events = [{
            "date": f"{DAYS_EN[idx].upper()} ({DAYS_ES[idx]}) · {today_utc} · HOY",
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

    now_dt = datetime.datetime.now(datetime.timezone.utc)
    day_name = DAYS_EN[now_dt.weekday()]
    now_utc = f"{day_name} {now_dt.strftime('%Y-%m-%d %H:%M UTC')}"

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
