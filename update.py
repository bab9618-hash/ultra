import json
import datetime
import requests
import yfinance as yf
import pandas as pd

ASSETS_CONFIG = [
    {"symbol": "USTEC", "name": "Nasdaq 100", "ticker": "NQ=F", "base": "USD", "quote": "USTEC", "decimals": 2, "pip": 1.0, "type": "index"},
    {"symbol": "US500", "name": "S&P 500", "ticker": "ES=F", "base": "USD", "quote": "US500", "decimals": 2, "pip": 0.25, "type": "index"},
    {"symbol": "US30", "name": "Dow Jones", "ticker": "YM=F", "base": "USD", "quote": "US30", "decimals": 2, "pip": 1.0, "type": "index"},
    {"symbol": "EURUSD", "name": "Euro Dólar", "ticker": "EURUSD=X", "base": "EUR", "quote": "USD", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "USDJPY", "name": "Dólar Yen", "ticker": "USDJPY=X", "base": "USD", "quote": "JPY", "decimals": 3, "pip": 0.01, "type": "forex"},
    {"symbol": "GBPUSD", "name": "Cable", "ticker": "GBPUSD=X", "base": "GBP", "quote": "USD", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "AUDUSD", "name": "Aussie", "ticker": "AUDUSD=X", "base": "AUD", "quote": "USD", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "NZDUSD", "name": "Kiwi", "ticker": "NZDUSD=X", "base": "NZD", "quote": "USD", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "USDCAD", "name": "Loonie", "ticker": "USDCAD=X", "base": "USD", "quote": "CAD", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "USDCHF", "name": "Swissy", "ticker": "USDCHF=X", "base": "USD", "quote": "CHF", "decimals": 5, "pip": 0.0001, "type": "forex"},
    {"symbol": "EURJPY", "name": "Euro Yen", "ticker": "EURJPY=X", "base": "EUR", "quote": "JPY", "decimals": 3, "pip": 0.01, "type": "forex"},
]

CENTRAL_BANKS = [
    {"bank": "Fed", "currency": "USD", "rate": "4.50%", "stance": "HAWKISH", "score": 2, "note": "Mantiene piso restrictivo vigilando inflación y rendimientos US10Y."},
    {"bank": "BCE", "currency": "EUR", "rate": "3.00%", "stance": "DOVISH", "score": -2, "note": "Presión por desaceleración industrial en la Eurozona."},
    {"bank": "BoJ", "currency": "JPY", "rate": "0.25%", "stance": "NEUTRAL", "score": -1, "note": "Diferencial amplio frente a EE.UU. mantiene presión de carry trade."},
    {"bank": "BoE", "currency": "GBP", "rate": "4.75%", "stance": "NEUTRAL", "score": 0, "note": "Inflación de servicios frena recortes acelerados."},
    {"bank": "RBA", "currency": "AUD", "rate": "4.35%", "stance": "HAWKISH", "score": 1, "note": "Postura firme hasta consolidar rango meta de inflación."},
    {"bank": "RBNZ", "currency": "NZD", "rate": "4.25%", "stance": "DOVISH", "score": -2, "note": "Ciclo de recortes activo ante enfriamiento interno."},
    {"bank": "BoC", "currency": "CAD", "rate": "3.75%", "stance": "DOVISH", "score": -2, "note": "Flexibilización monetaria debilita al dólar canadiense."},
    {"bank": "SNB", "currency": "CHF", "rate": "1.00%", "stance": "DOVISH", "score": -1, "note": "Tasas bajas para contener apreciación del franco suizo."},
]

CURRENCY_SCORE = {cb["currency"]: cb["score"] for cb in CENTRAL_BANKS}

def get_ticker_metrics(ticker_str, decimals=2):
    try:
        df = yf.Ticker(ticker_str).history(period="3mo", interval="1d")
        if df.empty or len(df) < 20:
            return None
        close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        change_pct = ((close - prev_close) / prev_close) * 100
        ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
        return {
            "price": round(close, decimals),
            "change_pct": round(change_pct, 2),
            "ema20": round(ema20, decimals),
        }
    except Exception:
        return None

def serialize_candles(df, dec, limit=42):
    sub = df.tail(limit)
    candles = []
    for idx, row in sub.iterrows():
        try:
            label = idx.strftime("%d %b") if hasattr(idx, "strftime") else str(idx)[:10]
            candles.append({
                "t": label,
                "o": round(float(row["Open"]), dec),
                "h": round(float(row["High"]), dec),
                "l": round(float(row["Low"]), dec),
                "c": round(float(row["Close"]), dec),
            })
        except Exception:
            continue
    return candles

def determine_tf_bias(df):
    if df.empty or len(df) < 15:
        return "NEUTRAL"
    close = float(df["Close"].iloc[-1])
    ema9 = float(df["Close"].ewm(span=9).mean().iloc[-1])
    ema21 = float(df["Close"].ewm(span=21).mean().iloc[-1])
    if close > ema9 and ema9 > ema21:
        return "SUBE"
    elif close < ema9 and ema9 < ema21:
        return "BAJA"
    return "NEUTRAL"

def compute_macro_bias(cfg, dxy_bull, us10y_high):
    if cfg["type"] == "index":
        if us10y_high and cfg["symbol"] == "USTEC":
            return "BAJA", "Yields altos comprimen múltiplos tecnológicos del Nasdaq."
        elif not us10y_high:
            return "SUBE", "Moderación de rendimientos impulsa flujo comprador en índices."
        else:
            return "SUBE", "Rotación hacia renta variable pese a tasas restrictivas."
    else:
        base_s = CURRENCY_SCORE.get(cfg["base"], 0) + (1 if (cfg["base"] == "USD" and dxy_bull) else (-1 if (cfg["base"] == "USD" and not dxy_bull) else 0))
        quote_s = CURRENCY_SCORE.get(cfg["quote"], 0) + (1 if (cfg["quote"] == "USD" and dxy_bull) else (-1 if (cfg["quote"] == "USD" and not dxy_bull) else 0))
        diff = base_s - quote_s
        if diff >= 2:
            return "SUBE", f"Divergencia monetaria favorece a {cfg['base']} frente a {cfg['quote']}."
        elif diff <= -2:
            return "BAJA", f"Diferencial de tasas y flujo institucional favorecen ventas en {cfg['symbol']}."
        return "NEUTRAL", f"Fuerzas equilibradas entre {cfg['base']} y {cfg['quote']}; esperar catalizador."

def analyze_asset(cfg, dxy_bull, us10y_high):
    dec = cfg["decimals"]
    df_1d = yf.Ticker(cfg["ticker"]).history(period="4mo", interval="1d")
    df_1h = yf.Ticker(cfg["ticker"]).history(period="20d", interval="1h")

    if df_1d.empty or len(df_1d) < 25 or df_1h.empty or len(df_1h) < 30:
        return None

    # Resample 1H -> 4H
    df_4h = df_1h.resample("4h").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last"
    }).dropna()

    price = round(float(df_1h["Close"].iloc[-1]), dec)
    prev_day = float(df_1d["Close"].iloc[-2])
    chg_day = round(((price - prev_day) / prev_day) * 100, 2)

    week_open = float(df_1d["Close"].iloc[-6]) if len(df_1d) >= 6 else prev_day
    chg_week = round(((price - week_open) / week_open) * 100, 2)

    # ATR 14 diario
    tr = pd.concat([
        df_1d["High"] - df_1d["Low"],
        (df_1d["High"] - df_1d["Close"].shift()).abs(),
        (df_1d["Low"] - df_1d["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    atr_14 = round(float(tr.tail(14).mean()), dec)

    # Rangos institucionales (20 días y últimas 48h intradía)
    range_20_high = round(float(df_1d["High"].tail(20).max()), dec)
    range_20_low = round(float(df_1d["Low"].tail(20).min()), dec)
    eq_50 = round((range_20_high + range_20_low) / 2, dec)

    intraday_high = round(float(df_1h["High"].tail(48).max()), dec)
    intraday_low = round(float(df_1h["Low"].tail(48).min()), dec)
    intraday_rng = intraday_high - intraday_low

    weekly_bias = determine_tf_bias(df_1d.tail(35))
    daily_bias = determine_tf_bias(df_1d.tail(18))
    h4_bias = determine_tf_bias(df_4h.tail(25))
    h1_bias = determine_tf_bias(df_1h.tail(30))

    # Sesgo técnico consolidado (Gráfico)
    bull_votes = [weekly_bias, daily_bias, h4_bias, h1_bias].count("SUBE")
    bear_votes = [weekly_bias, daily_bias, h4_bias, h1_bias].count("BAJA")
    if bull_votes >= 2 and bull_votes > bear_votes:
        chart_bias = "SUBE"
    elif bear_votes >= 2 and bear_votes > bull_votes:
        chart_bias = "BAJA"
    else:
        chart_bias = "NEUTRAL"

    economy_bias, macro_reason = compute_macro_bias(cfg, dxy_bull, us10y_high)

    # Cálculo de confluencia y trade setup (Entrada, SL, TP1, TP2)
    trade_dir = "BUY" if (economy_bias == "SUBE" or chart_bias == "SUBE") else "SELL"
    if economy_bias == chart_bias and economy_bias != "NEUTRAL":
        alignment = "ALIGNED"
        score = min(92, 62 + max(bull_votes, bear_votes) * 7)
        quality = "Excelente" if score >= 75 else ("Buena" if score >= 63 else "Moderada")
        action_label = "COMPRAS" if economy_bias == "SUBE" else "VENTAS"
        verdict_title = f"Van juntos: buscar {action_label}"
        verdict_sub = f"Alineación {'fuerte' if score >= 70 else 'moderada'}"
        trade_dir = "BUY" if economy_bias == "SUBE" else "SELL"
    elif economy_bias != "NEUTRAL" and chart_bias != "NEUTRAL" and economy_bias != chart_bias:
        alignment = "OPPOSED"
        score = 48
        quality = "Débil"
        action_label = "ESPERAR"
        verdict_title = "Se contradicen: esperar"
        verdict_sub = "La economía y el gráfico van a lados distintos"
        trade_dir = "BUY" if chart_bias == "SUBE" else "SELL"
    else:
        alignment = "NEUTRAL"
        score = 42
        quality = "Débil"
        action_label = "ESPERAR"
        verdict_title = "Sin dirección clara"
        verdict_sub = "Uno de los dos está neutral"
        trade_dir = "BUY" if (economy_bias == "SUBE" or chart_bias == "SUBE") else "SELL"

    # Cálculo de niveles institucionales exactos (OB, Entrada, SL, TP1 1:2, TP2 1:3)
    if trade_dir == "BUY":
        ob_low = round(intraday_low + intraday_rng * 0.12, dec)
        ob_high = round(intraday_low + intraday_rng * 0.32, dec)
        entry_price = round(min(price, ob_high), dec) if price > ob_low else round(price, dec)
        sl_price = round(min(ob_low, entry_price) - max(intraday_rng * 0.14, cfg["pip"] * 8), dec)
        risk = max(entry_price - sl_price, cfg["pip"] * 5)
        tp1_price = round(entry_price + risk * 2.0, dec)
        tp2_price = round(entry_price + risk * 3.0, dec)
        bsl = range_20_high
        ssl = intraday_low
        signal_tag = "SU COMPRA"
    else:
        ob_low = round(intraday_high - intraday_rng * 0.32, dec)
        ob_high = round(intraday_high - intraday_rng * 0.12, dec)
        entry_price = round(max(price, ob_low), dec) if price < ob_high else round(price, dec)
        sl_price = round(max(ob_high, entry_price) + max(intraday_rng * 0.14, cfg["pip"] * 8), dec)
        risk = max(sl_price - entry_price, cfg["pip"] * 5)
        tp1_price = round(entry_price - risk * 2.0, dec)
        tp2_price = round(entry_price - risk * 3.0, dec)
        bsl = intraday_high
        ssl = range_20_low
        signal_tag = "SU VENTA"

    return {
        "symbol": cfg["symbol"],
        "name": cfg["name"],
        "type": cfg["type"],
        "base": cfg["base"],
        "quote": cfg["quote"],
        "decimals": dec,
        "pip": cfg["pip"],
        "price": price,
        "chg_day": chg_day,
        "chg_week": chg_week,
        "atr": atr_14,
        "range_20_high": range_20_high,
        "range_20_low": range_20_low,
        "eq_50": eq_50,
        "intraday_high": intraday_high,
        "intraday_low": intraday_low,
        "bsl": bsl,
        "ssl": ssl,
        "ob_low": ob_low,
        "ob_high": ob_high,
        "economy_bias": economy_bias,
        "macro_reason": macro_reason,
        "chart_bias": chart_bias,
        "tf_bias": {
            "weekly": weekly_bias,
            "daily": daily_bias,
            "h4": h4_bias,
            "h1": h1_bias
        },
        "confluence": {
            "score": score,
            "quality": quality,
            "alignment": alignment,
            "action_label": action_label,
            "verdict_title": verdict_title,
            "verdict_sub": verdict_sub,
        },
        "setup": {
            "direction": trade_dir,
            "signal_tag": signal_tag,
            "entry": entry_price,
            "sl": sl_price,
            "tp1": tp1_price,
            "tp2": tp2_price,
            "rr": "1:2 / 1:3"
        },
        "candles": {
            "1d": serialize_candles(df_1d, dec, 42),
            "4h": serialize_candles(df_4h, dec, 42),
            "1h": serialize_candles(df_1h, dec, 42),
        }
    }

def fetch_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    allowed = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    events = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for item in resp.json():
                if item.get("currency") in allowed and item.get("impact") in ("High", "Medium"):
                    dt = item.get("date", "")
                    d_iso = dt[:10] if len(dt) >= 10 else ""
                    t_lbl = dt[11:16] if len(dt) >= 16 else "--:--"
                    events.append({
                        "date": d_iso,
                        "is_today": d_iso == today_str,
                        "time": t_lbl,
                        "currency": item.get("currency"),
                        "impact": "ALTO" if item.get("impact") == "High" else "MEDIO",
                        "title": item.get("title"),
                        "forecast": item.get("forecast") or "N/D",
                        "previous": item.get("previous") or "N/D"
                    })
    except Exception:
        pass
    return events[:16]

def main():
    dxy = get_ticker_metrics("DX-Y.NYB", 2) or {"price": 103.20, "change_pct": 0.1, "ema20": 102.5}
    us10y = get_ticker_metrics("^TNX", 3) or {"price": 4.450, "change_pct": 0.2, "ema20": 4.35}
    brent = get_ticker_metrics("BZ=F", 2) or {"price": 76.50, "change_pct": -0.3, "ema20": 77.0}

    dxy_bull = dxy["price"] >= dxy["ema20"]
    us10y_high = us10y["price"] >= 4.40

    if dxy_bull and us10y_high:
        headline = f"Bono US10Y en {us10y['price']}% y DXY firme en {dxy['price']}: presión bajista sobre pares contra el USD"
        summary = (
            f"Los rendimientos del Tesoro a 10 años en {us10y['price']}% ({us10y['change_pct']:+}%) sostienen la demanda institucional por el dólar (DXY en {dxy['price']}). "
            f"Mientras los bancos centrales de Europa y Oceanía mantienen sesgo acomodaticio, Jarvis prioriza ventas en pares mayores con confirmación estructural en Ultrón."
        )
    elif not dxy_bull:
        headline = f"DXY retrocede a {dxy['price']} con US10Y en {us10y['price']}%: apetito por riesgo en índices y divisas mayores"
        summary = (
            f"La caída del índice del dólar por debajo de su media institucional ({dxy['ema20']}) libera liquidez hacia índices estadounidenses (USTEC, US500, US30) "
            f"y favorece compras en EURUSD, GBPUSD y AUDUSD tras mitigación de bloques de demanda."
        )
    else:
        headline = f"Divergencia de tasas activa: DXY en {dxy['price']} y bono US10Y en {us10y['price']}%"
        summary = (
            f"El mercado opera con rotación selectiva entre divisas e índices. Evitar entradas donde economía y gráfico se contradicen; "
            f"priorizar únicamente activos con alineación confirmada en la Mesa de Swing de Jarvis."
        )

    assets = []
    for cfg in ASSETS_CONFIG:
        res = analyze_asset(cfg, dxy_bull, us10y_high)
        if res:
            assets.append(res)

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "last_updated": now_utc,
        "brief": {
            "headline": headline,
            "summary": summary,
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
