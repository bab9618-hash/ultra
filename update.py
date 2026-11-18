import json
import os
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# CONFIGURACIÓN DE 17 ACTIVOS (INCLUYE XAUUSD Y CRUCES GBP)
# =========================================================
ASSETS = [
    {"symbol": "XAUUSD", "ticker": "GC=F",     "type": "commodity", "pip": 0.1,    "decimals": 2, "base": "XAU", "quote": "USD"},
    {"symbol": "BTCUSD", "ticker": "BTC-USD",  "type": "crypto",    "pip": 1.0,    "decimals": 2, "base": "BTC", "quote": "USD"},
    {"symbol": "USTEC",  "ticker": "NQ=F",     "type": "index",     "pip": 1.0,    "decimals": 2, "base": "US",  "quote": "USD"},
    {"symbol": "US500",  "ticker": "ES=F",     "type": "index",     "pip": 1.0,    "decimals": 2, "base": "US",  "quote": "USD"},
    {"symbol": "US30",   "ticker": "YM=F",     "type": "index",     "pip": 1.0,    "decimals": 2, "base": "US",  "quote": "USD"},
    {"symbol": "EURUSD", "ticker": "EURUSD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "EUR", "quote": "USD"},
    {"symbol": "USDJPY", "ticker": "USDJPY=X", "type": "forex",     "pip": 0.01,   "decimals": 3, "base": "USD", "quote": "JPY"},
    {"symbol": "GBPUSD", "ticker": "GBPUSD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "USD"},
    {"symbol": "GBPJPY", "ticker": "GBPJPY=X", "type": "forex",     "pip": 0.01,   "decimals": 3, "base": "GBP", "quote": "JPY"},
    {"symbol": "GBPAUD", "ticker": "GBPAUD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "AUD"},
    {"symbol": "GBPNZD", "ticker": "GBPNZD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "NZD"},
    {"symbol": "GBPCAD", "ticker": "GBPCAD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "CAD"},
    {"symbol": "AUDUSD", "ticker": "AUDUSD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "AUD", "quote": "USD"},
    {"symbol": "NZDUSD", "ticker": "NZDUSD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "NZD", "quote": "USD"},
    {"symbol": "USDCAD", "ticker": "USDCAD=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "USD", "quote": "CAD"},
    {"symbol": "USDCHF", "ticker": "USDCHF=X", "type": "forex",     "pip": 0.0001, "decimals": 5, "base": "USD", "quote": "CHF"},
    {"symbol": "EURJPY", "ticker": "EURJPY=X", "type": "forex",     "pip": 0.01,   "decimals": 3, "base": "EUR", "quote": "JPY"}
]

def get_trend(df):
    if df is None or len(df) < 22:
        return "NEUTRAL"
    close = df["Close"].squeeze()
    ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
    if ema9 > ema21 * 1.0002:
        return "SUBE"
    elif ema9 < ema21 * 0.9998:
        return "BAJA"
    return "NEUTRAL"

def format_candles(df, decimals, limit=45):
    if df is None or df.empty:
        return []
    sub = df.tail(limit)
    out = []
    for idx, row in sub.iterrows():
        o = float(row["Open"].iloc[0] if isinstance(row["Open"], pd.Series) else row["Open"])
        h = float(row["High"].iloc[0] if isinstance(row["High"], pd.Series) else row["High"])
        l = float(row["Low"].iloc[0] if isinstance(row["Low"], pd.Series) else row["Low"])
        c = float(row["Close"].iloc[0] if isinstance(row["Close"], pd.Series) else row["Close"])
        if pd.isna(o) or pd.isna(c):
            continue
        out.append({
            "t": idx.strftime("%d %b %H:%M"),
            "o": round(o, decimals),
            "h": round(h, decimals),
            "l": round(l, decimals),
            "c": round(c, decimals)
        })
    return out

def get_macro_context():
    dxy_val, dxy_trend = 104.20, "NEUTRAL"
    us10y_val, us10y_trend = 4.25, "NEUTRAL"
    try:
        dxy_df = yf.download("DX-Y.NYB", period="15d", interval="1h", progress=False)
        if not dxy_df.empty:
            c = dxy_df["Close"].squeeze()
            dxy_val = round(float(c.iloc[-1]), 2)
            dxy_trend = get_trend(dxy_df)
    except Exception:
        pass

    try:
        tnx_df = yf.download("^TNX", period="15d", interval="1h", progress=False)
        if not tnx_df.empty:
            c = tnx_df["Close"].squeeze()
            us10y_val = round(float(c.iloc[-1]), 2)
            us10y_trend = get_trend(tnx_df)
    except Exception:
        pass

    return dxy_val, dxy_trend, us10y_val, us10y_trend

def evaluate_macro_for_asset(asset, dxy_trend, us10y_trend):
    base, quote = asset["base"], asset["quote"]

    if base == "XAU":
        if dxy_trend == "UP" or (dxy_trend == "SUBE" and us10y_trend == "SUBE"):
            return "BAJA", "El fortalecimiento del dólar (DXY) y los rendimientos US10Y presionan al oro a la baja."
        elif dxy_trend == "BAJA" and us10y_trend == "BAJA":
            return "SUBE", "La debilidad del dólar y caída en rendimientos impulsan demanda institucional en XAU/USD."
        return "NEUTRAL", "Flujos mixtos entre el dólar y los bonos mantienen al oro en rango intradía."

    if base in ["BTC", "US"]:
        if dxy_trend == "BAJA" and us10y_trend == "BAJA":
            return "SUBE", "Menor presión de tasas y dólar débil favorecen activos de riesgo e índices."
        elif dxy_trend == "SUBE" and us10y_trend == "SUBE":
            return "BAJA", "Repunte en rendimientos y dólar fuerte drenan liquidez de riesgo."
        return "NEUTRAL", "Rendimientos estables; el activo depende de su estructura intradía."

    if quote == "USD":
        if dxy_trend == "SUBE":
            return "BAJA", f"Dólar fuerte (DXY alcista) presiona a la baja al par {asset['symbol']}."
        elif dxy_trend == "BAJA":
            return "SUBE", f"Debilidad del índice dólar impulsa compras en {asset['symbol']}."
        return "NEUTRAL", f"DXY lateral; {asset['symbol']} sin catalizador macro dominante."

    if base == "USD":
        if dxy_trend == "SUBE":
            return "SUBE", f"Fortaleza del DXY respalda continuidad alcista en {asset['symbol']}."
        elif dxy_trend == "BAJA":
            return "BAJA", f"Retroceso del dólar debilita al par {asset['symbol']}."
        return "NEUTRAL", f"Dólar en equilibrio; esperar confirmación técnica en {asset['symbol']}."

    if quote == "JPY":
        if us10y_trend == "SUBE":
            return "SUBE", f"Subida en bonos US10Y debilita al yen e impulsa al cruce {asset['symbol']}."
        elif us10y_trend == "BAJA":
            return "BAJA", f"Caída en rendimientos fortalece al yen y presiona a {asset['symbol']}."
        return "NEUTRAL", f"Diferencial de tasas estable para {asset['symbol']}."

    return "NEUTRAL", f"Cruce {asset['symbol']} guiado por flujos relativos de sesión."

def load_previous_state():
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                old = json.load(f)
                return {a["symbol"]: a for a in old.get("assets", [])}
        except Exception:
            pass
    return {}

def main():
    prev_map = load_previous_state()
    dxy_val, dxy_trend, us10y_val, us10y_trend = get_macro_context()
    assets_output = []

    for asset in ASSETS:
        sym = asset["symbol"]
        dec = asset["decimals"]
        pip = asset["pip"]
        try:
            df_1h = yf.download(asset["ticker"], period="10d", interval="1h", progress=False)
            df_1d = yf.download(asset["ticker"], period="60d", interval="1d", progress=False)
            if df_1h.empty:
                continue

            close_1h = df_1h["Close"].squeeze()
            high_1h = df_1h["High"].squeeze()
            low_1h = df_1h["Low"].squeeze()

            price = round(float(close_1h.iloc[-1]), dec)
            prev_close = float(close_1h.iloc[-24]) if len(close_1h) >= 24 else float(close_1h.iloc[0])
            chg_day = round(((price - prev_close) / prev_close) * 100, 2)

            # Resample 4H
            df_4h = df_1h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()

            b_1d = get_trend(df_1d)
            b_4h = get_trend(df_4h)
            b_1h = get_trend(df_1h)

            votes = [b_1d, b_4h, b_1h]
            if votes.count("SUBE") >= 2:
                chart_bias = "SUBE"
            elif votes.count("BAJA") >= 2:
                chart_bias = "BAJA"
            else:
                chart_bias = b_1h if b_1h != "NEUTRAL" else "SUBE"

            macro_bias, macro_reason = evaluate_macro_for_asset(asset, dxy_trend, us10y_trend)

            # Rango intradía de 16 horas para EQ 50% y Order Block dinámico
            recent_high = float(high_1h.tail(16).max())
            recent_low = float(low_1h.tail(16).min())
            rng = max(recent_high - recent_low, pip * 15)
            eq_50 = (recent_high + recent_low) / 2.0

            # Verificar si existe una señal previa vigente que aún no ha tocado TP1 ni SL
            reuse_setup = False
            old_a = prev_map.get(sym)
            if old_a and "setup" in old_a:
                oset = old_a["setup"]
                odir = oset.get("direction")
                if odir == "BUY" and oset["sl"] < price < oset["tp1"]:
                    reuse_setup = True
                elif odir == "SELL" and oset["tp1"] < price < oset["sl"]:
                    reuse_setup = True

            if reuse_setup:
                setup = old_a["setup"]
                ob_high = old_a.get("ob_high", setup["entry"] + rng * 0.08)
                ob_low = old_a.get("ob_low", setup["entry"] - rng * 0.08)
            else:
                direction = "BUY" if chart_bias == "SUBE" else "SELL"
                risk_dist = max(rng * 0.28, pip * 12)
                if direction == "BUY":
                    entry = round(min(price - rng * 0.12, eq_50 - rng * 0.05), dec)
                    if entry >= price:
                        entry = round(price - rng * 0.15, dec)
                    sl = round(entry - risk_dist, dec)
                    tp1 = round(entry + risk_dist * 2.0, dec)
                    tp2 = round(entry + risk_dist * 3.0, dec)
                    ob_high = round(entry + risk_dist * 0.25, dec)
                    ob_low = round(entry - risk_dist * 0.25, dec)
                    sig_tag = "RE-ENTRADA COMPRA" if old_a else "COMPRA OB"
                else:
                    entry = round(max(price + rng * 0.12, eq_50 + rng * 0.05), dec)
                    if entry <= price:
                        entry = round(price + rng * 0.15, dec)
                    sl = round(entry + risk_dist, dec)
                    tp1 = round(entry - risk_dist * 2.0, dec)
                    tp2 = round(entry - risk_dist * 3.0, dec)
                    ob_high = round(entry + risk_dist * 0.25, dec)
                    ob_low = round(entry - risk_dist * 0.25, dec)
                    sig_tag = "RE-ENTRADA VENTA" if old_a else "VENTA OB"

                setup = {
                    "direction": direction,
                    "signal_tag": sig_tag,
                    "entry": entry,
                    "sl": sl,
                    "tp1": tp1,
                    "tp2": tp2
                }

            # Confluencia Visión + Ultrón
            if macro_bias == chart_bias and macro_bias != "NEUTRAL":
                alignment = "ALIGNED"
                score = 84
                v_title = "VAN JUNTOS · CONFLUENCIA"
                v_sub = f"Macro y gráfico apuntan a {chart_bias}"
            elif macro_bias != "NEUTRAL" and chart_bias != "NEUTRAL" and macro_bias != chart_bias:
                alignment = "OPPOSED"
                score = 32
                v_title = "TESIS ROTA · SE CONTRADICEN"
                v_sub = f"Macro {macro_bias} vs Gráfico {chart_bias}"
            else:
                alignment = "NEUTRAL"
                score = 58
                v_title = "EN OBSERVACIÓN"
                v_sub = "Uno de los dos está neutral"

            assets_output.append({
                "symbol": sym,
                "type": asset["type"],
                "pip": pip,
                "decimals": dec,
                "price": price,
                "chg_day": chg_day,
                "chart_bias": chart_bias,
                "macro_bias": macro_bias,
                "macro_reason": macro_reason,
                "intraday_high": round(recent_high, dec),
                "intraday_low": round(recent_low, dec),
                "ob_high": ob_high,
                "ob_low": ob_low,
                "tf_bias": {"weekly": b_1d, "daily": b_1d, "h4": b_4h, "h1": b_1h},
                "confluence": {
                    "alignment": alignment,
                    "score": score,
                    "verdict_title": v_title,
                    "verdict_sub": v_sub
                },
                "setup": setup,
                "candles": {
                    "1d": format_candles(df_1d, dec, 42),
                    "4h": format_candles(df_4h, dec, 42),
                    "1h": format_candles(df_1h, dec, 42)
                }
            })
        except Exception as e:
            print(f"Error en {sym}: {e}")

    payload = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": f"{us10y_val}%",
            "headline": f"DXY en {dxy_val} ({dxy_trend}) · Rendimiento US10Y en {us10y_val}% ({us10y_trend})",
            "summary": f"Telemetría actualizada sobre {len(assets_output)} activos incluyendo XAU/USD, índices, Bitcoin y pares mayores/GBP."
        },
        "calendar": [
            {"date": "Hoy", "time": "12:30", "currency": "USD", "impact": "ALTO", "title": "Apertura Sesión Nueva York / Flujos Bonos", "forecast": "Volatilidad", "previous": "Estable"},
            {"date": "Hoy", "time": "14:00", "currency": "USD", "impact": "MEDIO", "title": "Índice Manufacturero & Liquidez Intradía", "forecast": "--", "previous": "--"}
        ],
        "assets": assets_output
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"data.json actualizado correctamente con {len(assets_output)} activos.")

if __name__ == "__main__":
    main()
