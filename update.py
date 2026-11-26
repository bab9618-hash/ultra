import json
import os
import time
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf

ACTIVE_SETUPS_FILE = "active_setups.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "laticce_brian_ultra_alerts")

ASSETS = [
    {"symbol": "XAUUSD", "yf": "GC=F", "type": "metal", "decimals": 2, "pip": 0.1, "base": "XAU", "quote": "USD"},
    {"symbol": "EURUSD", "yf": "EURUSD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "EUR", "quote": "USD"},
    {"symbol": "USDJPY", "yf": "JPY=X", "type": "forex", "decimals": 3, "pip": 0.01, "base": "USD", "quote": "JPY"},
    {"symbol": "GBPUSD", "yf": "GBPUSD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "GBP", "quote": "USD"},
    {"symbol": "GBPJPY", "yf": "GBPJPY=X", "type": "forex", "decimals": 3, "pip": 0.01, "base": "GBP", "quote": "JPY"},
    {"symbol": "GBPAUD", "yf": "GBPAUD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "GBP", "quote": "AUD"},
    {"symbol": "GBPNZD", "yf": "GBPNZD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "GBP", "quote": "NZD"},
    {"symbol": "GBPCAD", "yf": "GBPCAD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "GBP", "quote": "CAD"},
    {"symbol": "AUDUSD", "yf": "AUDUSD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "AUD", "quote": "USD"},
    {"symbol": "AUDJPY", "yf": "AUDJPY=X", "type": "forex", "decimals": 3, "pip": 0.01, "base": "AUD", "quote": "JPY"},
    {"symbol": "AUDCAD", "yf": "AUDCAD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "AUD", "quote": "CAD"},
    {"symbol": "AUDNZD", "yf": "AUDNZD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "AUD", "quote": "NZD"},
    {"symbol": "EURAUD", "yf": "EURAUD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "EUR", "quote": "AUD"},
    {"symbol": "AUDCHF", "yf": "AUDCHF=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "AUD", "quote": "CHF"},
    {"symbol": "NZDUSD", "yf": "NZDUSD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "NZD", "quote": "USD"},
    {"symbol": "USDCAD", "yf": "CAD=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "USD", "quote": "CAD"},
    {"symbol": "USDCHF", "yf": "CHF=X", "type": "forex", "decimals": 5, "pip": 0.0001, "base": "USD", "quote": "CHF"},
    {"symbol": "EURJPY", "yf": "EURJPY=X", "type": "forex", "decimals": 3, "pip": 0.01, "base": "EUR", "quote": "JPY"},
    {"symbol": "BTCUSD", "yf": "BTC-USD", "type": "crypto", "decimals": 2, "pip": 1.0, "base": "BTC", "quote": "USD"},
    {"symbol": "US30", "yf": "^DJI", "type": "index", "decimals": 2, "pip": 1.0, "base": "US30", "quote": "USD"},
    {"symbol": "USTEC", "yf": "^IXIC", "type": "index", "decimals": 2, "pip": 1.0, "base": "USTEC", "quote": "USD"},
    {"symbol": "US500", "yf": "^GSPC", "type": "index", "decimals": 2, "pip": 1.0, "base": "US500", "quote": "USD"},
]


def load_active_setups():
    if os.path.exists(ACTIVE_SETUPS_FILE):
        try:
            with open(ACTIVE_SETUPS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_active_setups(store):
    with open(ACTIVE_SETUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def send_push(title, message, tags="chart_with_upwards_trend"):
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title.encode("latin-1", "ignore"), "Tags": tags, "Priority": "high"},
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass


def fetch_df(ticker, period="60d", interval="1h"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        return df
    except Exception:
        return None


def df_to_candles(df, decimals, limit=50):
    if df is None or df.empty:
        return []
    sub = df.tail(limit)
    out = []
    for idx, row in sub.iterrows():
        ts = int(idx.timestamp()) if hasattr(idx, "timestamp") else int(time.time())
        out.append({
            "t": ts,
            "o": round(float(row["Open"]), decimals),
            "h": round(float(row["High"]), decimals),
            "l": round(float(row["Low"]), decimals),
            "c": round(float(row["Close"]), decimals),
        })
    return out


def compute_tf_bias(df):
    if df is None or len(df) < 15:
        return "NEUTRAL"
    closes = df["Close"].astype(float)
    ema9 = closes.ewm(span=9).mean().iloc[-1]
    ema21 = closes.ewm(span=21).mean().iloc[-1]
    last_c = closes.iloc[-1]
    prev_c = closes.iloc[-4]
    if last_c > ema9 > ema21 and last_c > prev_c:
        return "SUBE"
    if last_c < ema9 < ema21 and last_c < prev_c:
        return "BAJA"
    return "NEUTRAL"


def compute_atr(df, period=14):
    if df is None or len(df) < period + 2:
        return 0.0
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    c = df["Close"].astype(float)
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def fetch_forexfactory_calendar():
    events = []
    try:
        req = urllib.request.Request(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        raw = urllib.request.urlopen(req, timeout=8).read()
        root = ET.fromstring(raw)
        today_str = datetime.now(timezone.utc).strftime("%m-%d-%Y")
        for ev in root.findall("event"):
            impact = (ev.findtext("impact") or "").strip()
            date_txt = (ev.findtext("date") or "").strip()
            if impact == "High" and date_txt == today_str:
                ccy = (ev.findtext("country") or "").strip()
                title = (ev.findtext("title") or "").strip()
                tm = (ev.findtext("time") or "").strip()
                events.append({
                    "currency": ccy,
                    "title": title,
                    "time": tm,
                    "date": date_txt,
                    "impact": "ALTO",
                    "plain_es": f"Dato macro de alto impacto en {ccy} ({title}). Evita abrir órdenes 15 min antes.",
                })
    except Exception:
        pass
    return events


def fetch_market_news():
    items = []
    try:
        url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F,EURUSD=X,^GSPC&region=US&lang=en-US"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=8).read()
        root = ET.fromstring(raw)
        for it in root.findall(".//item")[:6]:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "#").strip()
            pub = (it.findtext("pubDate") or "")[:16]
            items.append({
                "title": title,
                "link": link,
                "source": "Yahoo Finance",
                "time": pub,
                "plain_es": "Titular institucional de seguimiento macro en vivo.",
            })
    except Exception:
        pass
    return items


def compute_currency_strength(dfs_1d, dfs_4h):
    currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
    scores = {c: 0.0 for c in currencies}
    pairs_map = [
        ("EURUSD", "EUR", "USD"), ("GBPUSD", "GBP", "USD"), ("AUDUSD", "AUD", "USD"),
        ("NZDUSD", "NZD", "USD"), ("USDJPY", "USD", "JPY"), ("USDCAD", "USD", "CAD"),
        ("USDCHF", "USD", "CHF"), ("GBPJPY", "GBP", "JPY"), ("EURJPY", "EUR", "JPY"),
        ("AUDJPY", "AUD", "JPY"), ("GBPAUD", "GBP", "AUD"), ("EURAUD", "EUR", "AUD"),
        ("AUDNZD", "AUD", "NZD"), ("AUDCAD", "AUD", "CAD"), ("GBPCAD", "GBP", "CAD"),
    ]
    for sym, b, q in pairs_map:
        d1 = dfs_1d.get(sym)
        h4 = dfs_4h.get(sym)
        if d1 is not None and len(d1) >= 5 and h4 is not None and len(h4) >= 6:
            chg_d = (float(d1["Close"].iloc[-1]) - float(d1["Close"].iloc[-4])) / float(d1["Close"].iloc[-4])
            chg_h = (float(h4["Close"].iloc[-1]) - float(h4["Close"].iloc[-6])) / float(h4["Close"].iloc[-6])
            combo = (chg_d * 0.6 + chg_h * 0.4) * 100
            scores[b] += combo
            scores[q] -= combo

    labels = {}
    for c, sc in scores.items():
        if sc >= 0.45:
            labels[c] = "FUERTE"
        elif sc <= -0.45:
            labels[c] = "DEBIL"
        else:
            labels[c] = "NEUTRAL"
    return {"scores": {k: round(v, 2) for k, v in scores.items()}, "labels": labels}


def detect_institutional_zone(df_4h, df_1h, direction, price, pip, decimals, eq50):
    """Cascada de 3 niveles: 1) OB + FVG, 2) OB estructural, 3) FVG limpio de retroceso."""
    ob_candidates = []
    fvg_candidates = []

    for tf_name, df in [("4H", df_4h), ("1H", df_1h)]:
        if df is None or len(df) < 20:
            continue
        sub = df.tail(38).reset_index(drop=True)
        for i in range(len(sub) - 4, 2, -1):
            c0 = sub.iloc[i]
            c1 = sub.iloc[i + 1]
            c2 = sub.iloc[i + 2]
            body0 = abs(float(c0["Close"]) - float(c0["Open"]))
            body1 = abs(float(c1["Close"]) - float(c1["Open"]))

            # Nivel 1 y 2: Order Block (con o sin FVG)
            if body1 >= max(body0 * 1.25, pip * 6):
                if direction == "BUY" and float(c0["Close"]) < float(c0["Open"]) and float(c1["Close"]) > float(c1["Open"]):
                    ob_low = float(c0["Low"])
                    ob_high = float(c0["High"])
                    has_fvg = float(c2["Low"]) > float(c0["High"])
                    entry = round((ob_high + ob_low) / 2.0, decimals)
                    if entry < price and (price - entry) / price <= 0.025:
                        sl = round(ob_low - pip * 6, decimals)
                        tag = f"COMPRA OB + FVG ({tf_name})" if has_fvg else f"COMPRA OB REAL ({tf_name})"
                        ob_candidates.append({
                            "valid": True, "has_fvg": has_fvg, "is_pure_fvg": False, "tf": tf_name,
                            "entry": entry, "sl": sl, "ob_high": round(ob_high, decimals),
                            "ob_low": round(ob_low, decimals), "signal_tag": tag,
                            "safe_eq": entry <= eq50, "dist": abs(price - entry),
                        })

                if direction == "SELL" and float(c0["Close"]) > float(c0["Open"]) and float(c1["Close"]) < float(c1["Open"]):
                    ob_low = float(c0["Low"])
                    ob_high = float(c0["High"])
                    has_fvg = float(c2["High"]) < float(c0["Low"])
                    entry = round((ob_high + ob_low) / 2.0, decimals)
                    if entry > price and (entry - price) / price <= 0.025:
                        sl = round(ob_high + pip * 6, decimals)
                        tag = f"VENTA OB + FVG ({tf_name})" if has_fvg else f"VENTA OB REAL ({tf_name})"
                        ob_candidates.append({
                            "valid": True, "has_fvg": has_fvg, "is_pure_fvg": False, "tf": tf_name,
                            "entry": entry, "sl": sl, "ob_high": round(ob_high, decimals),
                            "ob_low": round(ob_low, decimals), "signal_tag": tag,
                            "safe_eq": entry >= eq50, "dist": abs(price - entry),
                        })

            # Nivel 3: FVG aislado de retroceso (hueco limpio entre c0 y c2)
            if direction == "BUY" and float(c2["Low"]) > float(c0["High"]) + pip * 2:
                fvg_low = float(c0["High"])
                fvg_high = float(c2["Low"])
                entry = round((fvg_high + fvg_low) / 2.0, decimals)
                if entry < price and (price - entry) / price <= 0.02:
                    sl = round(float(c1["Low"]) - pip * 5, decimals)
                    fvg_candidates.append({
                        "valid": True, "has_fvg": True, "is_pure_fvg": True, "tf": tf_name,
                        "entry": entry, "sl": sl, "ob_high": round(fvg_high, decimals),
                        "ob_low": round(fvg_low, decimals), "signal_tag": f"COMPRA FVG RETROCESO ({tf_name})",
                        "safe_eq": entry <= eq50, "dist": abs(price - entry),
                    })

            if direction == "SELL" and float(c2["High"]) < float(c0["Low"]) - pip * 2:
                fvg_high = float(c0["Low"])
                fvg_low = float(c2["High"])
                entry = round((fvg_high + fvg_low) / 2.0, decimals)
                if entry > price and (entry - price) / price <= 0.02:
                    sl = round(float(c1["High"]) + pip * 5, decimals)
                    fvg_candidates.append({
                        "valid": True, "has_fvg": True, "is_pure_fvg": True, "tf": tf_name,
                        "entry": entry, "sl": sl, "ob_high": round(fvg_high, decimals),
                        "ob_low": round(fvg_low, decimals), "signal_tag": f"VENTA FVG RETROCESO ({tf_name})",
                        "safe_eq": entry >= eq50, "dist": abs(price - entry),
                    })

    # Priorizar primero zonas que respeten EQ-50% y tengan OB+FVG, luego OB limpio, luego FVG limpio
    all_zones = ob_candidates + fvg_candidates
    if not all_zones:
        return {"valid": False}

    all_zones.sort(
        key=lambda z: (
            1 if z["safe_eq"] else 0,
            1 if (not z["is_pure_fvg"] and z["has_fvg"]) else 0,
            1 if not z["is_pure_fvg"] else 0,
            1 if z["tf"] == "4H" else 0,
            -z["dist"],
        ),
        reverse=True,
    )
    return all_zones[0]


def main():
    now_utc = datetime.now(timezone.utc)
    active_store = load_active_setups()
    calendar = fetch_forexfactory_calendar()
    news = fetch_market_news()

    dxy_df = fetch_df("DX-Y.NYB", period="15d", interval="1d")
    us10y_df = fetch_df("^TNX", period="15d", interval="1d")
    dxy_val = round(float(dxy_df["Close"].iloc[-1]), 2) if dxy_df is not None and not dxy_df.empty else 104.20
    us10y_val = round(float(us10y_df["Close"].iloc[-1]), 2) if us10y_df is not None and not us10y_df.empty else 4.25

    dfs_1d, dfs_4h, dfs_1h, dfs_1w = {}, {}, {}, {}
    for item in ASSETS:
        sym, ticker = item["symbol"], item["yf"]
        dfs_1w[sym] = fetch_df(ticker, period="1y", interval="1wk")
        dfs_1d[sym] = fetch_df(ticker, period="90d", interval="1d")
        dfs_4h[sym] = fetch_df(ticker, period="30d", interval="1h")
        if dfs_4h[sym] is not None and not dfs_4h[sym].empty:
            dfs_1h[sym] = dfs_4h[sym].copy()
            dfs_4h[sym] = dfs_4h[sym].resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()

    strength = compute_currency_strength(dfs_1d, dfs_4h)
    assets_out = []

    for item in ASSETS:
        sym = item["symbol"]
        dec = item["decimals"]
        pip = item["pip"]
        d1, h4, h1, w1 = dfs_1d.get(sym), dfs_4h.get(sym), dfs_1h.get(sym), dfs_1w.get(sym)
        if d1 is None or d1.empty or h1 is None or h1.empty:
            continue

        price = round(float(h1["Close"].iloc[-1]), dec)
        prev_day = float(d1["Close"].iloc[-2]) if len(d1) >= 2 else price
        chg_day = round(((price - prev_day) / prev_day) * 100, 2)

        bias_w = compute_tf_bias(w1)
        bias_d = compute_tf_bias(d1)
        bias_4h = compute_tf_bias(h4)
        bias_1h = compute_tf_bias(h1)

        b_lbl = strength["labels"].get(item["base"], "NEUTRAL")
        q_lbl = strength["labels"].get(item["quote"], "NEUTRAL")
        economy_short = f"{item['base']} {b_lbl} / {item['quote']} {q_lbl}"

        if b_lbl == "FUERTE" and q_lbl in ("DEBIL", "NEUTRAL"):
            macro_dir = "SUBE"
        elif b_lbl == "DEBIL" and q_lbl in ("FUERTE", "NEUTRAL"):
            macro_dir = "BAJA"
        elif q_lbl == "FUERTE" and b_lbl == "NEUTRAL":
            macro_dir = "BAJA"
        elif q_lbl == "DEBIL" and b_lbl == "NEUTRAL":
            macro_dir = "SUBE"
        else:
            macro_dir = "NEUTRAL"

        chart_bias = bias_d if bias_d != "NEUTRAL" else bias_4h
        direction = "BUY" if chart_bias == "SUBE" else ("SELL" if chart_bias == "BAJA" else "BUY")

        atr_val = compute_atr(d1, 14)
        atr_units = round(atr_val / pip, 1) if pip else 0
        r20_val = float(d1["High"].tail(20).max() - d1["Low"].tail(20).min())
        r20_units = round(r20_val / pip, 1) if pip else 0

        recent_h1 = h1.tail(44)
        bsl = round(float(recent_h1["High"].max()), dec)
        ssl = round(float(recent_h1["Low"].min()), dec)
        eq50 = round((bsl + ssl) / 2.0, dec)

        ev_today = [e["title"] for e in calendar if e["currency"] in (item["base"], item["quote"])]
        has_news = len(ev_today) > 0

        # Congelamiento vigente mientras el precio esté entre SL y TP1
        saved = active_store.get(sym)
        use_saved = False
        if saved and saved.get("has_valid_ob"):
            s_dir = saved["direction"]
            s_sl = saved["sl"]
            s_tp1 = saved["tp1"]
            if s_dir == "BUY" and s_sl < price < s_tp1:
                use_saved = True
            elif s_dir == "SELL" and s_tp1 < price < s_sl:
                use_saved = True

        if use_saved:
            entry = saved["entry"]
            sl = saved["sl"]
            be_trigger = saved["be_trigger"]
            tp1 = saved["tp1"]
            tp2 = saved["tp2"]
            ob_high = saved["ob_high"]
            ob_low = saved["ob_low"]
            signal_tag = saved["signal_tag"]
            has_valid_ob = True
            has_fvg = saved.get("has_fvg", False)
            is_pure_fvg = saved.get("is_pure_fvg", False)
            created_at = saved.get("created_at", int(now_utc.timestamp()))
        else:
            zone = detect_institutional_zone(h4, h1, direction, price, pip, dec, eq50)
            if zone["valid"] and chart_bias in ("SUBE", "BAJA"):
                entry = zone["entry"]
                sl = zone["sl"]
                risk = abs(entry - sl)
                be_trigger = round(entry + risk if direction == "BUY" else entry - risk, dec)
                tp1 = round(entry + risk * 2.5 if direction == "BUY" else entry - risk * 2.5, dec)
                tp2 = round(entry + risk * 4.5 if direction == "BUY" else entry - risk * 4.5, dec)
                ob_high = zone["ob_high"]
                ob_low = zone["ob_low"]
                signal_tag = zone["signal_tag"]
                has_valid_ob = True
                has_fvg = zone["has_fvg"]
                is_pure_fvg = zone["is_pure_fvg"]
                created_at = int(now_utc.timestamp())
                active_store[sym] = {
                    "has_valid_ob": True, "has_fvg": has_fvg, "is_pure_fvg": is_pure_fvg,
                    "direction": direction, "entry": entry, "sl": sl, "be_trigger": be_trigger,
                    "tp1": tp1, "tp2": tp2, "ob_high": ob_high, "ob_low": ob_low,
                    "signal_tag": signal_tag, "created_at": created_at,
                }
            else:
                entry = price
                sl = round(price - atr_val * 0.6 if direction == "BUY" else price + atr_val * 0.6, dec)
                risk = abs(entry - sl)
                be_trigger = round(entry + risk if direction == "BUY" else entry - risk, dec)
                tp1 = round(entry + risk * 2.5 if direction == "BUY" else entry - risk * 2.5, dec)
                tp2 = round(entry + risk * 4.5 if direction == "BUY" else entry - risk * 4.5, dec)
                ob_high = round(price + pip * 4, dec)
                ob_low = round(price - pip * 4, dec)
                signal_tag = "SIN OB NI FVG - ESPERAR"
                has_valid_ob = False
                has_fvg = False
                is_pure_fvg = False
                created_at = int(now_utc.timestamp())
                active_store.pop(sym, None)

        # Filtro estricto de seguridad (EQ-50% + 1D + 4H + Macro + Noticias)
        caution_reasons = []
        if has_valid_ob:
            if direction == "BUY" and entry > eq50:
                caution_reasons.append("Zona cara (arriba de EQ-50%)")
            if direction == "SELL" and entry < eq50:
                caution_reasons.append("Zona barata (debajo de EQ-50%)")
            if bias_4h == "NEUTRAL":
                caution_reasons.append("4H en NEUTRAL")
            elif bias_4h != chart_bias:
                caution_reasons.append(f"4H en {bias_4h}")
            if bias_d != chart_bias:
                caution_reasons.append(f"1D en {bias_d}")
            if macro_dir != chart_bias:
                caution_reasons.append(f"Macro en {macro_dir}")
            if has_news:
                caution_reasons.append("Noticia roja hoy")

        is_safe_entry = has_valid_ob and len(caution_reasons) == 0

        # Especialización Swing (1D + 4H + Macro + Zona segura) vs Intraday selectivo (OB+FVG doble o FVG seguro en EQ-50%)
        swing_active = is_safe_entry and (bias_d == chart_bias) and (bias_4h == chart_bias) and (macro_dir == chart_bias)
        intraday_selective = is_safe_entry and (not swing_active) and (has_fvg or is_pure_fvg)

        if not swing_active and not intraday_selective and is_safe_entry:
            caution_reasons.append("Sin confluencia FVG para Intraday")
            is_safe_entry = False

        score = 45
        if has_valid_ob:
            score += 18 if not is_pure_fvg else 14
        if has_fvg:
            score += 10
        if bias_d == bias_4h == chart_bias:
            score += 12
        if macro_dir == chart_bias:
            score += 8
        if is_safe_entry:
            score += 5
        else:
            score -= min(22, len(caution_reasons) * 7)
        win_prob = max(30, min(96, score))

        alignment = "ALIGNED" if (macro_dir == chart_bias and chart_bias != "NEUTRAL") else ("OPPOSED" if (macro_dir != "NEUTRAL" and chart_bias != "NEUTRAL" and macro_dir != chart_bias) else "NEUTRAL")

        macro_reason = (
            f"{economy_short} en cesta híbrida 4H/1D. Jerarquía (1S:{bias_w}, 1D:{bias_d}, 4H:{bias_4h}, 1H:{bias_1h}). "
            f"Equilibrio EQ-50% en {eq50}. "
            + ("SWING SEGURO validado para recorrido multi-día." if swing_active else ("INTRADAY SELECTIVO OB/FVG validado." if intraday_selective else ("CON PRECAUCIÓN: " + ", ".join(caution_reasons) if caution_reasons else "Sin bloque institucional vigente.")))
        )

        swing_plan = (
            f"1) Entrada base en {entry} con SL estructural en {sl}. "
            f"2) Al tocar {be_trigger} (+1R), sube SL a Break Even. "
            f"3) Cobra parciales en TP1 ({tp1}) y deja correr el resto hacia Swing TP ({tp2})."
        )

        assets_out.append({
            "symbol": sym,
            "type": item["type"],
            "base": item["base"],
            "quote": item["quote"],
            "decimals": dec,
            "pip": pip,
            "price": price,
            "chg_day": chg_day,
            "win_prob": win_prob,
            "has_valid_ob": has_valid_ob,
            "is_safe_entry": is_safe_entry,
            "caution_reasons": caution_reasons,
            "economy_short": economy_short,
            "macro_dir": macro_dir,
            "chart_bias": chart_bias,
            "structure_event": "⚡ BULLISH BOS" if direction == "BUY" else "⚡ BEARISH BOS",
            "tf_bias": {"weekly": bias_w, "daily": bias_d, "h4": bias_4h, "h1": bias_1h},
            "volatility": {"atr_units": atr_units, "range20_units": r20_units},
            "liquidity": {"bsl": bsl, "ssl": ssl, "eq50": eq50},
            "ob_high": ob_high,
            "ob_low": ob_low,
            "created_at": created_at,
            "macro_reason": macro_reason,
            "confluence": {
                "score": win_prob,
                "alignment": alignment,
                "verdict_title": "SWING SEGURO" if swing_active else ("INTRADAY OB/FVG" if intraday_selective else ("CON PRECAUCIÓN" if has_valid_ob else "ESPERAR")),
                "verdict_sub": signal_tag,
            },
            "setup": {
                "direction": direction,
                "signal_tag": signal_tag,
                "entry": entry,
                "sl": sl,
                "be": be_trigger,
                "tp1": tp1,
                "tp2": tp2,
            },
            "swing_potential": {"active": swing_active, "plan": swing_plan},
            "news_warning": {"active": has_news, "currencies": f"{item['base']}/{item['quote']}", "events": ev_today},
            "candles": {
                "1w": df_to_candles(w1, dec, 45),
                "1d": df_to_candles(d1, dec, 45),
                "4h": df_to_candles(h4, dec, 45),
                "1h": df_to_candles(h1, dec, 45),
            },
        })

    save_active_setups(active_store)

    ranked = sorted(
        assets_out,
        key=lambda x: (1 if x["swing_potential"]["active"] else 0, 1 if x["is_safe_entry"] else 0, x["win_prob"]),
        reverse=True,
    )
    top = ranked[0] if ranked else None
    focus_pick = {}
    if top:
        focus_pick = {
            "primary": {
                "symbol": top["symbol"],
                "dir_label": "COMPRA" if top["setup"]["direction"] == "BUY" else "VENTA",
                "probability": top["win_prob"],
                "signal_tag": top["setup"]["signal_tag"],
                "entry": top["setup"]["entry"],
                "sl": top["setup"]["sl"],
                "tp1": top["setup"]["tp1"],
                "is_safe": top["is_safe_entry"],
                "is_swing": top["swing_potential"]["active"],
            }
        }
        if top["swing_potential"]["active"] and not use_saved:
            send_push(
                f"🌊 SWING SEGURO: {top['symbol']} ({top['win_prob']}%)",
                f"{top['setup']['signal_tag']} | Entrada: {top['setup']['entry']} | SL: {top['setup']['sl']} | TP1: {top['setup']['tp1']}",
            )

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"Radar Swing Institucional · DXY {dxy_val} · Bonos US10Y {us10y_val}%",
            "summary": "LATICCE opera en modo Especialista Swing (1D + 4H + Macro + EQ-50%) con entradas Intraday selectivas en OB+FVG o FVG limpios.",
        },
        "currency_strength": strength,
        "calendar": calendar,
        "news": news,
        "focus_pick": focus_pick,
        "assets": assets_out,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Actualizado LATICCE v12.3 ({len(assets_out)} activos)")


if __name__ == "__main__":
    main()
