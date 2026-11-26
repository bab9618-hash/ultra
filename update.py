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


def is_within_max_distance(asset_type, price, entry, pip):
    diff = abs(price - entry)
    if diff <= 0:
        return False
    if asset_type == "forex":
        units = diff / pip if pip else diff
        return 4.0 <= units <= 35.0
    if asset_type == "metal":
        units = diff / pip if pip else diff
        return 10.0 <= units <= 180.0
    return (diff / max(price, 1e-9)) <= 0.01


def is_near_entry(asset_type, price, entry, pip):
    diff = abs(price - entry)
    if asset_type == "forex":
        units = diff / pip if pip else diff
        return units <= 25.0
    if asset_type == "metal":
        units = diff / pip if pip else diff
        return units <= 40.0
    return (diff / max(price, 1e-9)) <= 0.0025


def load_active_setups():
    if os.path.exists(ACTIVE_SETUPS_FILE):
        try:
            with open(ACTIVE_SETUPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_active_setups(store):
    tmp_path = f"{ACTIVE_SETUPS_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, ACTIVE_SETUPS_FILE)


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
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        required = {"Open", "High", "Low", "Close"}
        if not required.issubset(set(df.columns)):
            return None
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        return df if not df.empty else None
    except Exception:
        return None


def df_to_candles(df, decimals, limit=50):
    if df is None or df.empty:
        return []
    sub = df.tail(limit)
    out = []
    for idx, row in sub.iterrows():
        try:
            ts = int(idx.timestamp()) if hasattr(idx, "timestamp") else int(time.time())
            out.append({
                "t": ts,
                "o": round(float(row["Open"]), decimals),
                "h": round(float(row["High"]), decimals),
                "l": round(float(row["Low"]), decimals),
                "c": round(float(row["Close"]), decimals),
            })
        except Exception:
            continue
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
    val = tr.rolling(period).mean().iloc[-1]
    return float(val) if pd.notna(val) else 0.0


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
                    "plain_es": f"Dato macro de alto impacto en {ccy} ({title}). Evita abrir ordenes 15 min antes.",
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
            try:
                chg_d = (float(d1["Close"].iloc[-1]) - float(d1["Close"].iloc[-4])) / float(d1["Close"].iloc[-4])
                chg_h = (float(h4["Close"].iloc[-1]) - float(h4["Close"].iloc[-6])) / float(h4["Close"].iloc[-6])
                combo = (chg_d * 0.6 + chg_h * 0.4) * 100
                scores[b] += combo
                scores[q] -= combo
            except Exception:
                continue

    labels = {}
    for c, sc in scores.items():
        if sc >= 0.45:
            labels[c] = "FUERTE"
        elif sc <= -0.45:
            labels[c] = "DEBIL"
        else:
            labels[c] = "NEUTRAL"
    return {"scores": {k: round(v, 2) for k, v in scores.items()}, "labels": labels}


def detect_institutional_zone(df_4h, df_1h, direction, price, pip, decimals, eq50, asset_type):
    """Cascada de 3 niveles: 1) OB + FVG, 2) OB estructural, 3) FVG limpio de retroceso."""
    candidates = []

    for tf_name, df in [("1H", df_1h), ("4H", df_4h)]:
        if df is None or len(df) < 20:
            continue
        sub = df.tail(36).reset_index(drop=True)
        for i in range(len(sub) - 4, 2, -1):
            c0 = sub.iloc[i]
            c1 = sub.iloc[i + 1]
            c2 = sub.iloc[i + 2]
            body0 = abs(float(c0["Close"]) - float(c0["Open"]))
            body1 = abs(float(c1["Close"]) - float(c1["Open"]))

            if body1 >= max(body0 * 1.2, pip * 4):
                if direction == "BUY" and float(c0["Close"]) < float(c0["Open"]) and float(c1["Close"]) > float(c1["Open"]):
                    ob_low = float(c0["Low"])
                    ob_high = float(c0["High"])
                    has_fvg = float(c2["Low"]) > float(c0["High"])
                    entry = round((ob_high + ob_low) / 2.0, decimals)
                    if entry < price and is_within_max_distance(asset_type, price, entry, pip):
                        sl = round(ob_low - pip * 5, decimals)
                        tag = f"COMPRA OB + FVG ({tf_name})" if has_fvg else f"COMPRA OB REAL ({tf_name})"
                        kind = "OB_FVG" if has_fvg else "OB"
                        candidates.append({
                            "valid": True, "has_fvg": has_fvg, "is_pure_fvg": False, "kind": kind, "tf": tf_name,
                            "entry": entry, "sl": sl, "ob_high": round(ob_high, decimals),
                            "ob_low": round(ob_low, decimals), "signal_tag": tag,
                            "safe_eq": entry <= eq50, "dist": abs(price - entry),
                        })

                if direction == "SELL" and float(c0["Close"]) > float(c0["Open"]) and float(c1["Close"]) < float(c1["Open"]):
                    ob_low = float(c0["Low"])
                    ob_high = float(c0["High"])
                    has_fvg = float(c2["High"]) < float(c0["Low"])
                    entry = round((ob_high + ob_low) / 2.0, decimals)
                    if entry > price and is_within_max_distance(asset_type, price, entry, pip):
                        sl = round(ob_high + pip * 5, decimals)
                        tag = f"VENTA OB + FVG ({tf_name})" if has_fvg else f"VENTA OB REAL ({tf_name})"
                        kind = "OB_FVG" if has_fvg else "OB"
                        candidates.append({
                            "valid": True, "has_fvg": has_fvg, "is_pure_fvg": False, "kind": kind, "tf": tf_name,
                            "entry": entry, "sl": sl, "ob_high": round(ob_high, decimals),
                            "ob_low": round(ob_low, decimals), "signal_tag": tag,
                            "safe_eq": entry >= eq50, "dist": abs(price - entry),
                        })

            if direction == "BUY" and float(c2["Low"]) > float(c0["High"]) + pip * 1.5:
                fvg_low = float(c0["High"])
                fvg_high = float(c2["Low"])
                entry = round((fvg_high + fvg_low) / 2.0, decimals)
                if entry < price and is_within_max_distance(asset_type, price, entry, pip):
                    sl = round(float(c1["Low"]) - pip * 4, decimals)
                    candidates.append({
                        "valid": True, "has_fvg": True, "is_pure_fvg": True, "kind": "FVG", "tf": tf_name,
                        "entry": entry, "sl": sl, "ob_high": round(fvg_high, decimals),
                        "ob_low": round(fvg_low, decimals), "signal_tag": f"COMPRA FVG ({tf_name})",
                        "safe_eq": entry <= eq50, "dist": abs(price - entry),
                    })

            if direction == "SELL" and float(c2["High"]) < float(c0["Low"]) - pip * 1.5:
                fvg_high = float(c0["Low"])
                fvg_low = float(c2["High"])
                entry = round((fvg_high + fvg_low) / 2.0, decimals)
                if entry > price and is_within_max_distance(asset_type, price, entry, pip):
                    sl = round(float(c1["High"]) + pip * 4, decimals)
                    candidates.append({
                        "valid": True, "has_fvg": True, "is_pure_fvg": True, "kind": "FVG", "tf": tf_name,
                        "entry": entry, "sl": sl, "ob_high": round(fvg_high, decimals),
                        "ob_low": round(fvg_low, decimals), "signal_tag": f"VENTA FVG ({tf_name})",
                        "safe_eq": entry >= eq50, "dist": abs(price - entry),
                    })

    if not candidates:
        return {"valid": False}

    candidates.sort(
        key=lambda z: (
            1 if z["safe_eq"] else 0,
            1 if z["kind"] == "OB_FVG" else (0.6 if z["kind"] == "OB" else 0.4),
            -z["dist"],
        ),
        reverse=True,
    )
    return candidates[0]


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
        h1_raw = fetch_df(ticker, period="30d", interval="1h")
        dfs_1h[sym] = h1_raw
        if h1_raw is not None and not h1_raw.empty:
            try:
                dfs_4h[sym] = h1_raw.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
            except Exception:
                dfs_4h[sym] = None
        else:
            dfs_4h[sym] = None

    strength = compute_currency_strength(dfs_1d, dfs_4h)
    assets_out = []

    for item in ASSETS:
        sym = item["symbol"]
        dec = item["decimals"]
        pip = item["pip"]
        d1, h4, h1, w1 = dfs_1d.get(sym), dfs_4h.get(sym), dfs_1h.get(sym), dfs_1w.get(sym)

        ref_df = h1 if (h1 is not None and not h1.empty) else d1
        if ref_df is None or ref_df.empty:
            continue

        price = round(float(ref_df["Close"].iloc[-1]), dec)
        prev_day = float(d1["Close"].iloc[-2]) if (d1 is not None and len(d1) >= 2) else price
        chg_day = round(((price - prev_day) / prev_day) * 100, 2) if prev_day else 0.0

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

        chart_bias = bias_d if bias_d != "NEUTRAL" else (bias_4h if bias_4h != "NEUTRAL" else bias_1h)
        direction = "BUY" if chart_bias == "SUBE" else ("SELL" if chart_bias == "BAJA" else "BUY")

        atr_val = compute_atr(d1 if d1 is not None else ref_df, 14)
        if atr_val <= 0:
            atr_val = max(price * 0.004, pip * 15)
        atr_units = round(atr_val / pip, 1) if pip else 0

        r_df = d1 if (d1 is not None and len(d1) >= 20) else ref_df
        r20_val = float(r_df["High"].tail(20).max() - r_df["Low"].tail(20).min())
        r20_units = round(r20_val / pip, 1) if pip else 0

        recent_h1 = ref_df.tail(44)
        bsl = round(float(recent_h1["High"].max()), dec)
        ssl = round(float(recent_h1["Low"].min()), dec)
        eq50 = round((bsl + ssl) / 2.0, dec)

        ev_today = [e["title"] for e in calendar if e["currency"] in (item["base"], item["quote"])]
        has_news = len(ev_today) > 0

        saved = active_store.get(sym)
        use_saved = False
        if saved and saved.get("has_valid_ob") and is_within_max_distance(item["type"], price, saved["entry"], pip):
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
            zone_kind = saved.get("zone_kind", "OB")
            has_valid_ob = True
            has_fvg = saved.get("has_fvg", False)
            is_pure_fvg = saved.get("is_pure_fvg", False)
            created_at = saved.get("created_at", int(now_utc.timestamp()))
        else:
            zone = detect_institutional_zone(h4, h1, direction, price, pip, dec, eq50, item["type"])
            if zone["valid"] and chart_bias in ("SUBE", "BAJA"):
                entry = zone["entry"]
                sl = zone["sl"]
                risk = max(pip * 4, abs(entry - sl))
                be_trigger = round(entry + risk if direction == "BUY" else entry - risk, dec)
                tp1 = round(entry + risk * 2.5 if direction == "BUY" else entry - risk * 2.5, dec)
                tp2 = round(entry + risk * 4.5 if direction == "BUY" else entry - risk * 4.5, dec)
                ob_high = zone["ob_high"]
                ob_low = zone["ob_low"]
                signal_tag = zone["signal_tag"]
                zone_kind = zone["kind"]
                has_valid_ob = True
                has_fvg = zone["has_fvg"]
                is_pure_fvg = zone["is_pure_fvg"]
                created_at = int(now_utc.timestamp())
                active_store[sym] = {
                    "has_valid_ob": True, "has_fvg": has_fvg, "is_pure_fvg": is_pure_fvg,
                    "zone_kind": zone_kind, "direction": direction, "entry": entry, "sl": sl,
                    "be_trigger": be_trigger, "tp1": tp1, "tp2": tp2, "ob_high": ob_high,
                    "ob_low": ob_low, "signal_tag": signal_tag, "created_at": created_at,
                }
            else:
                entry = price
                sl = round(price - atr_val * 0.6 if direction == "BUY" else price + atr_val * 0.6, dec)
                risk = max(pip * 4, abs(entry - sl))
                be_trigger = round(entry + risk if direction == "BUY" else entry - risk, dec)
                tp1 = round(entry + risk * 2.5 if direction == "BUY" else entry - risk * 2.5, dec)
                tp2 = round(entry + risk * 4.5 if direction == "BUY" else entry - risk * 4.5, dec)
                ob_high = round(price + pip * 4, dec)
                ob_low = round(price - pip * 4, dec)
                signal_tag = "SIN ZONA - ESPERAR"
                zone_kind = "NONE"
                has_valid_ob = False
                has_fvg = False
                is_pure_fvg = False
                created_at = int(now_utc.timestamp())
                active_store.pop(sym, None)

        # Precaucion reservada a casos criticos reales: choque de estructura/macro, noticia roja o reentrada swing
        caution_reasons = []
        if has_valid_ob:
            if bias_4h != "NEUTRAL" and bias_4h != chart_bias:
                caution_reasons.append(f"4H en contra ({bias_4h})")
            if bias_d != "NEUTRAL" and bias_d != chart_bias:
                caution_reasons.append(f"1D en contra ({bias_d})")
            if macro_dir != "NEUTRAL" and macro_dir != chart_bias:
                caution_reasons.append(f"Macro en contra ({macro_dir})")
            if has_news:
                caution_reasons.append("Noticia roja hoy")

        swing_active = has_valid_ob and (bias_d == chart_bias) and (bias_4h == chart_bias) and (macro_dir == chart_bias) and (not has_news)
        near_entry = has_valid_ob and is_near_entry(item["type"], price, entry, pip)

        if not has_valid_ob:
            entry_mode = "ESPERAR"
            verdict_title = "ESPERAR"
        elif swing_active and use_saved:
            entry_mode = "REENTRADA_SWING_PRECAUCION"
            verdict_title = "REENTRADA SWING · CON PRECAUCIÓN"
            if "Reentrada Swing: validar BE en operacion base" not in caution_reasons:
                caution_reasons.append("Reentrada Swing: validar BE en operacion base")
        elif swing_active:
            entry_mode = "SWING_ENTRADA_NORMAL"
            verdict_title = "ENTRADA NORMAL · SWING"
        else:
            entry_mode = "ENTRADA_NORMAL"
            verdict_title = "ENTRADA NORMAL" if not caution_reasons else "ENTRADA NORMAL · CON PRECAUCIÓN"

        is_safe_entry = has_valid_ob and len(caution_reasons) == 0

        score = 55
        if has_valid_ob:
            score += 20 if zone_kind == "OB_FVG" else (16 if zone_kind == "OB" else 13)
        if near_entry:
            score += 10
        if bias_d == bias_4h == chart_bias:
            score += 8
        if macro_dir == chart_bias:
            score += 6
        if caution_reasons:
            score -= min(20, len(caution_reasons) * 6)
        win_prob = max(35, min(96, score))

        alignment = "ALIGNED" if (macro_dir == chart_bias and chart_bias != "NEUTRAL") else ("OPPOSED" if (macro_dir != "NEUTRAL" and chart_bias != "NEUTRAL" and macro_dir != chart_bias) else "NEUTRAL")

        zone_desc = "OB + FVG" if zone_kind == "OB_FVG" else ("FVG limpio" if zone_kind == "FVG" else ("OB estructural" if zone_kind == "OB" else "Sin zona"))
        macro_reason = (
            f"{economy_short} | Zona: {zone_desc} | 1S:{bias_w}, 1D:{bias_d}, 4H:{bias_4h}, 1H:{bias_1h} | EQ-50%: {eq50}. "
            + (f"Estado: {verdict_title}." if has_valid_ob else "Sin bloque cercano dentro del rango permitido.")
        )

        swing_plan = (
            f"1) Entrada en {entry} con SL estructural en {sl}. "
            f"2) Al tocar {be_trigger} (+1R), mover SL a Break Even. "
            f"3) Asegurar parciales en TP1 ({tp1}) y buscar Swing TP ({tp2})."
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
            "zone_kind": zone_kind,
            "entry_mode": entry_mode,
            "near_entry": near_entry,
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
                "verdict_title": verdict_title,
                "verdict_sub": f"{zone_desc} · {signal_tag}",
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
        key=lambda x: (1 if x["near_entry"] else 0, 1 if x["has_valid_ob"] else 0, x["win_prob"]),
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
                "near_entry": top["near_entry"],
                "entry_mode": top["entry_mode"],
            }
        }
        if top["has_valid_ob"] and not use_saved:
            send_push(
                f"LATICCE: {top['symbol']} ({top['win_prob']}%)",
                f"{top['confluence']['verdict_title']} | {top['setup']['signal_tag']} | Ent: {top['setup']['entry']} | SL: {top['setup']['sl']} | TP1: {top['setup']['tp1']}",
            )

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"Radar Institucional LATICCE v12.6 · DXY {dxy_val} · Bonos US10Y {us10y_val}%",
            "summary": "Escaner en cascada (OB + FVG, OB, FVG) con alerta amarilla en cercania a entrada y precaucion enfocada en riesgos reales.",
        },
        "currency_strength": strength,
        "calendar": calendar,
        "news": news,
        "focus_pick": focus_pick,
        "assets": assets_out,
    }

    tmp_data = "data.json.tmp"
    with open(tmp_data, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_data, "data.json")
    print(f"Actualizado LATICCE v12.6 ({len(assets_out)} activos)")


if __name__ == "__main__":
    main()
