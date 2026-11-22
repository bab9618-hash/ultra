import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import yfinance as yf

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
ALERTS_STATE_FILE = "alerts_sent.json"

ASSETS_CONFIG = [
    {"symbol": "XAUUSD", "yf": "GC=F",       "type": "metal",  "pip": 0.1,    "decimals": 2, "base": "XAU", "quote": "USD"},
    {"symbol": "EURUSD", "yf": "EURUSD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "EUR", "quote": "USD"},
    {"symbol": "USDJPY", "yf": "JPY=X",      "type": "forex",  "pip": 0.01,   "decimals": 3, "base": "USD", "quote": "JPY"},
    {"symbol": "GBPUSD", "yf": "GBPUSD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "USD"},
    {"symbol": "GBPJPY", "yf": "GBPJPY=X",   "type": "forex",  "pip": 0.01,   "decimals": 3, "base": "GBP", "quote": "JPY"},
    {"symbol": "GBPAUD", "yf": "GBPAUD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "AUD"},
    {"symbol": "GBPNZD", "yf": "GBPNZD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "NZD"},
    {"symbol": "GBPCAD", "yf": "GBPCAD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "GBP", "quote": "CAD"},
    {"symbol": "AUDUSD", "yf": "AUDUSD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "AUD", "quote": "USD"},
    {"symbol": "AUDJPY", "yf": "AUDJPY=X",   "type": "forex",  "pip": 0.01,   "decimals": 3, "base": "AUD", "quote": "JPY"},
    {"symbol": "AUDCAD", "yf": "AUDCAD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "AUD", "quote": "CAD"},
    {"symbol": "AUDNZD", "yf": "AUDNZD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "AUD", "quote": "NZD"},
    {"symbol": "EURAUD", "yf": "EURAUD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "EUR", "quote": "AUD"},
    {"symbol": "AUDCHF", "yf": "AUDCHF=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "AUD", "quote": "CHF"},
    {"symbol": "NZDUSD", "yf": "NZDUSD=X",   "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "NZD", "quote": "USD"},
    {"symbol": "USDCAD", "yf": "CAD=X",      "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "USD", "quote": "CAD"},
    {"symbol": "USDCHF", "yf": "CHF=X",      "type": "forex",  "pip": 0.0001, "decimals": 5, "base": "USD", "quote": "CHF"},
    {"symbol": "EURJPY", "yf": "EURJPY=X",   "type": "forex",  "pip": 0.01,   "decimals": 3, "base": "EUR", "quote": "JPY"},
    {"symbol": "BTCUSD", "yf": "BTC-USD",    "type": "crypto", "pip": 1.0,    "decimals": 2, "base": "BTC", "quote": "USD"},
    {"symbol": "US30",   "yf": "^DJI",       "type": "index",  "pip": 1.0,    "decimals": 2, "base": "USD", "quote": "USD"},
    {"symbol": "USTEC",  "yf": "^IXIC",      "type": "index",  "pip": 1.0,    "decimals": 2, "base": "USD", "quote": "USD"},
    {"symbol": "US500",  "yf": "^GSPC",      "type": "index",  "pip": 1.0,    "decimals": 2, "base": "USD", "quote": "USD"},
]

def load_sent_alerts():
    if os.path.exists(ALERTS_STATE_FILE):
        try:
            with open(ALERTS_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sent_alerts(state):
    with open(ALERTS_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_mobile_push(title, body, priority="high", tags="chart_with_upwards_trend"):
    if not NTFY_TOPIC:
        return
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": title.encode("latin-1", "ignore").decode("latin-1"),
                "Priority": priority,
                "Tags": tags,
                "Click": "https://bab9618-hash.github.io/ultra/"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
        print(f"Push enviado: {title}")
    except Exception as e:
        print(f"Aviso push ntfy: {e}")

def get_candles(ticker_str, period, interval, decimals, limit=45):
    try:
        t = yf.Ticker(ticker_str)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty:
            return []
        df = df.dropna(subset=["Open", "High", "Low", "Close"]).tail(limit)
        out = []
        for idx, row in df.iterrows():
            try:
                o_val = round(float(row["Open"]), decimals)
                h_val = round(float(row["High"]), decimals)
                l_val = round(float(row["Low"]), decimals)
                c_val = round(float(row["Close"]), decimals)
                if o_val > 0 and h_val > 0 and l_val > 0 and c_val > 0:
                    out.append({"t": int(idx.timestamp()), "o": o_val, "h": h_val, "l": l_val, "c": c_val})
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"Aviso {ticker_str} ({interval}): {e}")
        return []

def group_4h(c_1h_long):
    if not c_1h_long:
        return []
    grouped = []
    for i in range(0, len(c_1h_long), 4):
        chunk = c_1h_long[i:i+4]
        grouped.append({
            "t": chunk[0]["t"],
            "o": chunk[0]["o"],
            "h": max(x["h"] for x in chunk),
            "l": min(x["l"] for x in chunk),
            "c": chunk[-1]["c"],
        })
    return grouped[-45:]

def group_weekly(c_1d):
    if not c_1d:
        return []
    grouped = []
    for i in range(0, len(c_1d), 5):
        chunk = c_1d[i:i+5]
        grouped.append({
            "t": chunk[0]["t"],
            "o": chunk[0]["o"],
            "h": max(x["h"] for x in chunk),
            "l": min(x["l"] for x in chunk),
            "c": chunk[-1]["c"],
        })
    return grouped[-20:]

def calc_bias(candles, lookback=6, threshold=0.0006):
    if not candles or len(candles) < lookback:
        return "NEUTRAL"
    first = candles[-lookback]["c"]
    last = candles[-1]["c"]
    if last > first * (1.0 + threshold):
        return "SUBE"
    if last < first * (1.0 - threshold):
        return "BAJA"
    return "NEUTRAL"

def calc_atr_and_range(c_1d, pip, dec):
    if not c_1d or len(c_1d) < 3:
        return {"atr": 0, "atr_units": 0, "range20": 0, "range20_units": 0}
    trs = []
    for i in range(1, len(c_1d)):
        h = c_1d[i]["h"]
        l = c_1d[i]["l"]
        pc = c_1d[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    recent_tr = trs[-14:] if len(trs) >= 14 else trs
    atr = round(sum(recent_tr) / max(1, len(recent_tr)), dec)
    atr_units = round((atr / pip) * 10) / 10 if pip else atr

    last20 = c_1d[-20:] if len(c_1d) >= 20 else c_1d
    r20 = round(max(x["h"] for x in last20) - min(x["l"] for x in last20), dec)
    r20_units = round((r20 / pip) * 10) / 10 if pip else r20
    return {"atr": atr, "atr_units": atr_units, "range20": r20, "range20_units": r20_units}

def pct_change_lookback(candles, lookback=6):
    if not candles or len(candles) < lookback:
        return 0.0
    first = candles[-lookback]["c"]
    last = candles[-1]["c"]
    return ((last - first) / first) * 100.0 if first else 0.0

def detect_reversal_and_structure(c_1h, dec):
    if len(c_1h) < 18:
        swing_h = round(max((x["h"] for x in c_1h), default=0), dec)
        swing_l = round(min((x["l"] for x in c_1h), default=0), dec)
        return {"choch": "NONE", "sweep": "NONE", "bos": "NONE", "reversal_dir": "NONE", "bsl": swing_h, "ssl": swing_l}

    window = c_1h[-20:-2]
    last_two = c_1h[-2:]
    curr = last_two[-1]
    prev = c_1h[-3]
    swing_high = round(max(x["h"] for x in window), dec)
    swing_low = round(min(x["l"] for x in window), dec)

    choch = "NONE"
    bos = "NONE"
    if curr["c"] > swing_high:
        if prev["c"] < (swing_high + swing_low) / 2.0:
            choch = "BULLISH_CHOCH"
        else:
            bos = "BULLISH_BOS"
    elif curr["c"] < swing_low:
        if prev["c"] > (swing_high + swing_low) / 2.0:
            choch = "BEARISH_CHOCH"
        else:
            bos = "BEARISH_BOS"

    sweep = "NONE"
    for c in last_two:
        lower_wick = min(c["o"], c["c"]) - c["l"]
        upper_wick = c["h"] - max(c["o"], c["c"])
        body = max(1e-9, abs(c["c"] - c["o"]))
        if c["l"] <= swing_low and c["c"] > swing_low and lower_wick >= body * 0.6:
            sweep = "SSL_SWEEP_BUY"
        elif c["h"] >= swing_high and c["c"] < swing_high and upper_wick >= body * 0.6:
            sweep = "BSL_SWEEP_SELL"

    reversal_dir = "NONE"
    if choch == "BULLISH_CHOCH" or sweep == "SSL_SWEEP_BUY":
        reversal_dir = "SUBE"
    elif choch == "BEARISH_CHOCH" or sweep == "BSL_SWEEP_SELL":
        reversal_dir = "BAJA"

    return {
        "choch": choch,
        "bos": bos,
        "sweep": sweep,
        "reversal_dir": reversal_dir,
        "bsl": swing_high,
        "ssl": swing_low
    }

def detect_exhaustion_warning(c_1h, chart_bias, macro_dir, intraday_high, intraday_low):
    if len(c_1h) < 12:
        return {"active": False, "reason": ""}

    span = max(1e-9, intraday_high - intraday_low)
    price = c_1h[-1]["c"]
    pos_ratio = (price - intraday_low) / span

    prev_candles = c_1h[-10:-3]
    last_three = c_1h[-3:]
    avg_prev_body = sum(abs(x["c"] - x["o"]) for x in prev_candles) / max(1, len(prev_candles))
    avg_last_body = sum(abs(x["c"] - x["o"]) for x in last_three) / 3.0

    losing_momentum = avg_prev_body > 0 and (avg_last_body <= avg_prev_body * 0.65)
    macro_turning = (macro_dir != "NEUTRAL" and macro_dir != chart_bias)

    if chart_bias == "SUBE" and pos_ratio >= 0.80:
        upper_wicks = sum(x["h"] - max(x["o"], x["c"]) for x in last_three)
        bodies_sum = max(1e-9, sum(abs(x["c"] - x["o"]) for x in last_three))
        wick_rejection = upper_wicks >= bodies_sum * 0.85
        if losing_momentum and (macro_turning or wick_rejection):
            return {
                "active": True,
                "reason": "Agotamiento alcista en techo de rango (3 velas perdiendo cuerpo + rechazo/macro en contra). Proteger compras."
            }

    if chart_bias == "BAJA" and pos_ratio <= 0.20:
        lower_wicks = sum(min(x["o"], x["c"]) - x["l"] for x in last_three)
        bodies_sum = max(1e-9, sum(abs(x["c"] - x["o"]) for x in last_three))
        wick_rejection = lower_wicks >= bodies_sum * 0.85
        if losing_momentum and (macro_turning or wick_rejection):
            return {
                "active": True,
                "reason": "Agotamiento bajista en piso de rango (3 velas perdiendo cuerpo + absorción/macro en contra). Proteger ventas."
            }

    return {"active": False, "reason": ""}

def fetch_high_impact_calendar(now_utc):
    today_ff = now_utc.strftime("%m-%d-%Y")
    today_iso = now_utc.strftime("%Y-%m-%d")
    events_today = []
    high_impact_by_ccy = {}

    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for ev in root.findall(".//event"):
            date_el = ev.find("date")
            time_el = ev.find("time")
            ccy_el = ev.find("country")
            imp_el = ev.find("impact")
            title_el = ev.find("title")
            if date_el is None or ccy_el is None or imp_el is None or title_el is None:
                continue
            ev_date = (date_el.text or "").strip()
            if ev_date != today_ff:
                continue
            ccy = (ccy_el.text or "").strip().upper()
            imp = (imp_el.text or "").strip()
            title = (title_el.text or "").strip()
            ev_time = (time_el.text or "").strip() if time_el is not None else ""

            if imp.lower() == "high":
                high_impact_by_ccy.setdefault(ccy, []).append(f"{title} ({ev_time})")
                events_today.append({
                    "date": today_iso,
                    "time": ev_time or "Hoy",
                    "currency": ccy,
                    "impact": "ALTO",
                    "title": title
                })
            elif imp.lower() == "medium" and len(events_today) < 8:
                events_today.append({
                    "date": today_iso,
                    "time": ev_time or "Hoy",
                    "currency": ccy,
                    "impact": "MEDIO",
                    "title": title
                })
    except Exception as e:
        print(f"Aviso calendario económico: {e}")

    if not events_today:
        events_today = [
            {"date": today_iso, "time": "07:00 UTC", "currency": "EUR/GBP", "impact": "ALTO", "title": "Apertura Killzone Londres · Barrido de Liquidez Asiática"},
            {"date": today_iso, "time": "12:30 UTC", "currency": "USD", "impact": "ALTO", "title": "Apertura Killzone Nueva York · Flujo Institucional"},
            {"date": today_iso, "time": "23:50 UTC", "currency": "AUD/JPY", "impact": "MEDIO", "title": "Apertura Sesión Tokio & Sídney · Flujo Asia-Pacífico"}
        ]

    return events_today[:10], high_impact_by_ccy

def compute_currency_strength_matrix(c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, spx_4h, spx_1d):
    def blend_chg(c4, c1d):
        return (pct_change_lookback(c4, 6) * 0.60) + (pct_change_lookback(c1d, 5) * 0.40)

    dxy_chg = blend_chg(dxy_4h, dxy_1d)
    us10y_chg = blend_chg(us10y_4h, us10y_1d)
    spx_chg = blend_chg(spx_4h, spx_1d)

    usd_score = (dxy_chg * 1.4) + (us10y_chg * 0.35)
    gbp_score = (blend_chg(c4_map.get("GBPUSD"), c1d_map.get("GBPUSD")) +
                 blend_chg(c4_map.get("GBPJPY"), c1d_map.get("GBPJPY")) +
                 blend_chg(c4_map.get("GBPAUD"), c1d_map.get("GBPAUD"))) / 3.0
    aud_score = ((blend_chg(c4_map.get("AUDUSD"), c1d_map.get("AUDUSD")) +
                  blend_chg(c4_map.get("AUDJPY"), c1d_map.get("AUDJPY")) +
                  blend_chg(c4_map.get("AUDNZD"), c1d_map.get("AUDNZD"))) / 3.0) + (spx_chg * 0.25)
    eur_score = (blend_chg(c4_map.get("EURUSD"), c1d_map.get("EURUSD")) +
                 blend_chg(c4_map.get("EURJPY"), c1d_map.get("EURJPY")) +
                 blend_chg(c4_map.get("EURAUD"), c1d_map.get("EURAUD"))) / 3.0
    jpy_score = -((blend_chg(c4_map.get("USDJPY"), c1d_map.get("USDJPY")) +
                   blend_chg(c4_map.get("GBPJPY"), c1d_map.get("GBPJPY")) +
                   blend_chg(c4_map.get("EURJPY"), c1d_map.get("EURJPY")) +
                   blend_chg(c4_map.get("AUDJPY"), c1d_map.get("AUDJPY"))) / 4.0)
    nzd_score = (blend_chg(c4_map.get("NZDUSD"), c1d_map.get("NZDUSD")) -
                 blend_chg(c4_map.get("AUDNZD"), c1d_map.get("AUDNZD"))) / 2.0
    cad_score = (-blend_chg(c4_map.get("USDCAD"), c1d_map.get("USDCAD")) -
                 blend_chg(c4_map.get("AUDCAD"), c1d_map.get("AUDCAD"))) / 2.0
    chf_score = (-blend_chg(c4_map.get("USDCHF"), c1d_map.get("USDCHF")) -
                 blend_chg(c4_map.get("AUDCHF"), c1d_map.get("AUDCHF"))) / 2.0
    xau_score = -usd_score * 0.9

    raw = {
        "USD": usd_score, "GBP": gbp_score, "AUD": aud_score,
        "EUR": eur_score, "JPY": jpy_score, "NZD": nzd_score,
        "CAD": cad_score, "CHF": chf_score, "XAU": xau_score,
        "BTC": spx_chg * 0.8 - usd_score * 0.5,
    }
    labels = {k: ("FUERTE" if v > 0.14 else ("DÉBIL" if v < -0.14 else "NEUTRAL")) for k, v in raw.items()}
    return raw, labels, round(spx_chg, 2)

def fetch_live_news():
    feeds = [
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("FXStreet / Macro", "https://www.investing.com/rss/news_1.rss"),
        ("Forex & Divisas", "https://www.investing.com/rss/news_14.rss"),
    ]
    news_items = []
    seen = set()
    for source_name, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:4]:
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    if title in seen:
                        continue
                    seen.add(title)
                    news_items.append({
                        "source": source_name,
                        "title": title,
                        "link": link_el.text.strip() if (link_el is not None and link_el.text) else "#",
                        "time": (pub_el.text.strip()[:22] if (pub_el is not None and pub_el.text) else "Hoy")
                    })
        except Exception:
            pass
    if not news_items:
        news_items = [{"source": "Radar Institucional", "title": "Flujos de liquidez activos en sesiones principales.", "link": "#", "time": "En línea"}]
    return news_items[:8]

def get_central_banks(dxy_val, us10y_val, ccy_labels):
    return [
        {"bank": "FED (EE.UU.)", "currency": "USD", "stance": f"USD {ccy_labels.get('USD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("USD") == "FUERTE" else ("BEARISH" if ccy_labels.get("USD") == "DÉBIL" else "NEUTRAL"), "detail": f"DXY ({dxy_val}) + Bonos US10Y ({us10y_val}%) en cesta híbrida 4H/1D."},
        {"bank": "BoE (Reino Unido)", "currency": "GBP", "stance": f"GBP {ccy_labels.get('GBP', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("GBP") == "FUERTE" else ("BEARISH" if ccy_labels.get("GBP") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta híbrida GBPUSD + GBPJPY + GBPAUD (60% 4H + 40% 1D)."},
        {"bank": "RBA (Australia)", "currency": "AUD", "stance": f"AUD {ccy_labels.get('AUD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("AUD") == "FUERTE" else ("BEARISH" if ccy_labels.get("AUD") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta híbrida AUDUSD + AUDJPY + AUDNZD + riesgo US500 (4H/1D)."},
        {"bank": "BCE (Eurozona)", "currency": "EUR", "stance": f"EUR {ccy_labels.get('EUR', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("EUR") == "FUERTE" else ("BEARISH" if ccy_labels.get("EUR") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta híbrida EURUSD + EURJPY + EURAUD (60% 4H + 40% 1D)."},
        {"bank": "BoJ (Japón)", "currency": "JPY", "stance": f"JPY {ccy_labels.get('JPY', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("JPY") == "FUERTE" else ("BEARISH" if ccy_labels.get("JPY") == "DÉBIL" else "NEUTRAL"), "detail": "Flujo inverso en cruces JPY (60% 4H + 40% 1D)."}
    ]

def build_asset(cfg, candles_bundle, raw_strength, ccy_labels, high_impact_by_ccy, now_ts):
    try:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        pip = cfg["pip"]

        c_1d = candles_bundle.get("1d", [])
        c_4h = candles_bundle.get("4h", [])
        c_1h = candles_bundle.get("1h", [])
        c_1w = group_weekly(c_1d)

        if not c_1h and c_1d:
            c_1h = c_1d[-30:]
        if not c_4h and c_1d:
            c_4h = c_1d[-30:]
        if not c_1h:
            return None

        price = c_1h[-1]["c"]
        prev_close = c_1d[-2]["c"] if len(c_1d) >= 2 else c_1h[0]["o"]
        chg_day = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0

        b_w = calc_bias(c_1w, 4, 0.0015) if len(c_1w) >= 4 else calc_bias(c_1d, 6, 0.0010)
        b_d = calc_bias(c_1d, 6, 0.0010)
        b_4h = calc_bias(c_4h, 6, 0.0008)
        b_1h = calc_bias(c_1h, 6, 0.0006)
        vol_metrics = calc_atr_and_range(c_1d, pip, dec)

        w_up = (3 if b_d == "SUBE" else 0) + (2 if b_4h == "SUBE" else 0) + (1 if b_1h == "SUBE" else 0)
        w_dn = (3 if b_d == "BAJA" else 0) + (2 if b_4h == "BAJA" else 0) + (1 if b_1h == "BAJA" else 0)

        base_ccy = cfg["base"]
        quote_ccy = cfg["quote"]
        if cfg["type"] == "index":
            macro_diff = raw_strength.get("BTC", 0.0)
            macro_dir = "SUBE" if macro_diff > 0.10 else ("BAJA" if macro_diff < -0.10 else "NEUTRAL")
            macro_detail = f"Apetito al riesgo US500 y rendimiento USD ({ccy_labels.get('USD', 'NEUTRAL')})."
            economy_short = "FUERTE (ALCISTA)" if macro_dir == "SUBE" else ("DÉBIL (BAJISTA)" if macro_dir == "BAJA" else "NEUTRAL")
        else:
            b_str = raw_strength.get(base_ccy, 0.0)
            q_str = raw_strength.get(quote_ccy, 0.0)
            macro_diff = b_str - q_str
            macro_dir = "SUBE" if macro_diff > 0.14 else ("BAJA" if macro_diff < -0.14 else "NEUTRAL")
            b_lbl = ccy_labels.get(base_ccy, "NEUTRAL")
            q_lbl = ccy_labels.get(quote_ccy, "NEUTRAL")
            macro_detail = f"{base_ccy} ({b_lbl}) vs {quote_ccy} ({q_lbl}) en cesta híbrida 4H/1D."
            economy_short = f"{base_ccy} {b_lbl} / {quote_ccy} {q_lbl}"

        rev = detect_reversal_and_structure(c_1h, dec)
        base_label = ccy_labels.get(base_ccy, "NEUTRAL")
        base_supports_reversal = True
        if cfg["type"] == "forex":
            if rev["reversal_dir"] == "SUBE" and base_label == "DÉBIL":
                base_supports_reversal = False
            elif rev["reversal_dir"] == "BAJA" and base_label == "FUERTE":
                base_supports_reversal = False

        macro_backed_reversal = (
            rev["reversal_dir"] != "NONE"
            and rev["reversal_dir"] == macro_dir
            and base_supports_reversal
        )

        if macro_backed_reversal:
            chart_bias = rev["reversal_dir"]
            if chart_bias == "SUBE":
                w_up = max(w_up, w_dn + 2)
            else:
                w_dn = max(w_dn, w_up + 2)
        else:
            if rev["choch"] == "BULLISH_CHOCH" or rev["sweep"] == "SSL_SWEEP_BUY":
                w_up += 2
            elif rev["choch"] == "BEARISH_CHOCH" or rev["sweep"] == "BSL_SWEEP_SELL":
                w_dn += 2
            chart_bias = "SUBE" if w_up >= w_dn else "BAJA"

        recent = c_1h[-24:]
        intraday_high = max(x["h"] for x in recent)
        intraday_low = min(x["l"] for x in recent)

        exhaustion = detect_exhaustion_warning(c_1h, chart_bias, macro_dir, intraday_high, intraday_low)

        if chart_bias == "SUBE":
            direction = "BUY"
            ob_low = round(min(x["l"] for x in recent[-12:]), dec)
            ob_high = round(ob_low + (12 * pip), dec)
            entry = round((ob_low + ob_high) / 2.0, dec)
            if price < entry:
                entry = round(price - (6 * pip), dec)
                ob_low = round(entry - (5 * pip), dec)
                ob_high = round(entry + (5 * pip), dec)
            risk = max(12 * pip, round((intraday_high - intraday_low) * 0.22, dec))
            sl = round(entry - risk, dec)
            tp1 = round(entry + (risk * 2.0), dec)
            tp2 = round(entry + (risk * 3.0), dec)
            be_trigger = round(entry + risk, dec)

            touched_orig = any(x["l"] <= ob_high for x in c_1h[-6:])
            hit_tp1_real = touched_orig and price >= tp1
            is_reentry_active = False

            if hit_tp1_real:
                for idx in range(len(c_1h) - 2, max(1, len(c_1h) - 6), -1):
                    c_ob = c_1h[idx]
                    c_imp = c_1h[idx + 1]
                    body_ob = max(pip, abs(c_ob["c"] - c_ob["o"]))
                    body_imp = abs(c_imp["c"] - c_imp["o"])
                    if c_ob["c"] < c_ob["o"] and c_imp["c"] > c_ob["h"] and body_imp >= body_ob * 1.3 and c_ob["h"] < price:
                        ob_low = round(c_ob["l"], dec)
                        ob_high = round(max(c_ob["h"], ob_low + 8 * pip), dec)
                        entry = round((ob_low + ob_high) / 2.0, dec)
                        sl = round(min(ob_low - (6 * pip), entry - risk), dec)
                        actual_r = abs(entry - sl)
                        be_trigger = round(entry + actual_r, dec)
                        tp1 = round(max(entry + (actual_r * 2.0), price + (12 * pip)), dec)
                        tp2 = round(max(entry + (actual_r * 3.0), tp1 + actual_r), dec)
                        is_reentry_active = True
                        break

            if exhaustion["active"]:
                signal_tag = "⚠️ RIESGO GIRO · PROTEGER"
            elif is_reentry_active:
                signal_tag = "RE-ENTRADA OB (PIRÁMIDE)"
            elif hit_tp1_real:
                signal_tag = "TP1 CUMPLIDO · SIN RE-ENTRADA"
            elif macro_backed_reversal and rev["sweep"] == "SSL_SWEEP_BUY":
                signal_tag = "GIRO MACRO · BARRIDO SSL"
            elif macro_backed_reversal and rev["choch"] == "BULLISH_CHOCH":
                signal_tag = "GIRO MACRO · CHoCH ALCISTA"
            elif rev["choch"] == "BULLISH_CHOCH":
                signal_tag = "CHoCH ALCISTA · OB"
            else:
                signal_tag = "COMPRA OB"
        else:
            direction = "SELL"
            ob_high = round(max(x["h"] for x in recent[-12:]), dec)
            ob_low = round(ob_high - (12 * pip), dec)
            entry = round((ob_low + ob_high) / 2.0, dec)
            if price > entry:
                entry = round(price + (6 * pip), dec)
                ob_high = round(entry + (5 * pip), dec)
                ob_low = round(entry - (5 * pip), dec)
            risk = max(12 * pip, round((intraday_high - intraday_low) * 0.22, dec))
            sl = round(entry + risk, dec)
            tp1 = round(entry - (risk * 2.0), dec)
            tp2 = round(entry - (risk * 3.0), dec)
            be_trigger = round(entry - risk, dec)

            touched_orig = any(x["h"] >= ob_low for x in c_1h[-6:])
            hit_tp1_real = touched_orig and price <= tp1
            is_reentry_active = False

            if hit_tp1_real:
                for idx in range(len(c_1h) - 2, max(1, len(c_1h) - 6), -1):
                    c_ob = c_1h[idx]
                    c_imp = c_1h[idx + 1]
                    body_ob = max(pip, abs(c_ob["c"] - c_ob["o"]))
                    body_imp = abs(c_imp["c"] - c_imp["o"])
                    if c_ob["c"] > c_ob["o"] and c_imp["c"] < c_ob["l"] and body_imp >= body_ob * 1.3 and c_ob["l"] > price:
                        ob_high = round(c_ob["h"], dec)
                        ob_low = round(min(c_ob["l"], ob_high - 8 * pip), dec)
                        entry = round((ob_low + ob_high) / 2.0, dec)
                        sl = round(max(ob_high + (6 * pip), entry + risk), dec)
                        actual_r = abs(sl - entry)
                        be_trigger = round(entry - actual_r, dec)
                        tp1 = round(min(entry - (actual_r * 2.0), price - (12 * pip)), dec)
                        tp2 = round(min(entry - (actual_r * 3.0), tp1 - actual_r), dec)
                        is_reentry_active = True
                        break

            if exhaustion["active"]:
                signal_tag = "⚠️ RIESGO GIRO · PROTEGER"
            elif is_reentry_active:
                signal_tag = "RE-ENTRADA OB (PIRÁMIDE)"
            elif hit_tp1_real:
                signal_tag = "TP1 CUMPLIDO · SIN RE-ENTRADA"
            elif macro_backed_reversal and rev["sweep"] == "BSL_SWEEP_SELL":
                signal_tag = "GIRO MACRO · BARRIDO BSL"
            elif macro_backed_reversal and rev["choch"] == "BEARISH_CHOCH":
                signal_tag = "GIRO MACRO · CHoCH BAJISTA"
            elif rev["choch"] == "BEARISH_CHOCH":
                signal_tag = "CHoCH BAJISTA · OB"
            else:
                signal_tag = "VENTA OB"

        dominant_w = max(w_up, w_dn)
        if exhaustion["active"]:
            alignment = "OPPOSED" if macro_dir != chart_bias else "ALIGNED"
            conf_score = 44 if macro_dir != chart_bias else 58
            verdict_title = "⚠️ AGOTAMIENTO · RIESGO DE GIRO"
            verdict_sub = "Momentum en extremo se frena · Asegurar parciales / BE"
        elif macro_dir == chart_bias:
            alignment = "ALIGNED"
            conf_score = min(94, 68 + (dominant_w * 3) + (4 if macro_backed_reversal else 0))
            verdict_title = "GIRO CONFIRMADO · MACRO + TÉCNICO" if macro_backed_reversal else f"VAN JUNTOS · BUSCAR {'COMPRAS' if direction == 'BUY' else 'VENTAS'}"
            verdict_sub = f"Economía ({macro_dir}) y Gráfico ({chart_bias}) empujan juntos"
        elif macro_dir == "NEUTRAL":
            alignment = "NEUTRAL"
            conf_score = min(74, 52 + (dominant_w * 3))
            verdict_title = "SIN DIRECCIÓN CLARA · ECONOMÍA NEUTRAL"
            verdict_sub = f"Economía plana · Gráfico marca {chart_bias} (esperar confluencia)"
        else:
            alignment = "OPPOSED"
            conf_score = max(32, 46 - (dominant_w * 2))
            verdict_title = "SE CONTRADICEN · ESPERAR"
            verdict_sub = f"Economía en {macro_dir} rechaza gráfico en {chart_bias}"

        dist_ratio = abs(price - entry) / max(1e-9, price)
        max_swing_dist = 0.025 if cfg["type"] == "crypto" else 0.012
        ccy_swing_ok = True
        if cfg["type"] == "forex":
            if direction == "BUY" and ccy_labels.get(base_ccy) == "DÉBIL":
                ccy_swing_ok = False
            elif direction == "SELL" and ccy_labels.get(base_ccy) == "FUERTE":
                ccy_swing_ok = False

        is_swing_potential = (
            not exhaustion["active"]
            and ccy_swing_ok
            and b_d == chart_bias
            and b_4h == chart_bias
            and b_1h == chart_bias
            and macro_dir == chart_bias
            and conf_score >= 84
            and dist_ratio <= max_swing_dist
        )

        swing_tp = round(entry + (risk * 4.2), dec) if direction == "BUY" else round(entry - (risk * 4.2), dec)
        swing_info = None
        if is_swing_potential:
            swing_info = {
                "active": True,
                "label": "🌊 POTENCIAL SWING · PROTOCOLO PIRÁMIDE",
                "target": swing_tp,
                "be_trigger": be_trigger,
                "plan": (
                    f"1) Divide la entrada base en {entry} (SL {sl}). "
                    f"2) Al tocar {be_trigger} (+1R) o TP1 ({tp1}), cobra parciales y sube el SL a {entry} (Break Even). "
                    f"3) Solo con la orden base ya protegida, añade 2.ª entrada en retroceso (🔵 RE-ENTRADA OB en 4H/1H) hacia Swing TP {swing_tp}."
                )
            }

        ccys_to_check = {"USD"} if cfg["type"] in ("index", "crypto") else ({base_ccy, quote_ccy} - {"XAU"})
        if base_ccy == "XAU":
            ccys_to_check.add("USD")

        pair_news_titles = []
        affected_ccys = []
        for c in sorted(ccys_to_check):
            if c in high_impact_by_ccy:
                affected_ccys.append(c)
                pair_news_titles.extend(high_impact_by_ccy[c])

        news_warning = None
        if pair_news_titles:
            news_warning = {
                "active": True,
                "currencies": "/".join(affected_ccys),
                "label": f"⚠️ NOTICIA FUERTE {'/'.join(affected_ccys)} HOY · OPERAR CON CUIDADO",
                "events": pair_news_titles[:3]
            }

        swing_note = f" 🌊 Potencial Swing activo (BE en {be_trigger}, Swing TP {swing_tp})." if is_swing_potential else ""
        extra_note = f" {exhaustion['reason']}" if exhaustion["active"] else (f" Giro detectado ({rev['sweep'] if rev['sweep'] != 'NONE' else rev['choch']}) con respaldo macro." if macro_backed_reversal else "")
        macro_reason = f"{macro_detail} Jerarquía (1S:{b_w}, 1D:{b_d}, 4H:{b_4h}, 1H:{b_1h}).{extra_note}{swing_note}"

        return {
            "symbol": sym,
            "base": base_ccy,
            "quote": quote_ccy,
            "type": cfg["type"],
            "pip": pip,
            "decimals": dec,
            "price": price,
            "chg_day": chg_day,
            "chart_bias": chart_bias,
            "macro_dir": macro_dir,
            "economy_short": economy_short,
            "tf_bias": {"weekly": b_w, "daily": b_d, "h4": b_4h, "h1": b_1h},
            "liquidity": {
                "bsl": rev["bsl"],
                "ssl": rev["ssl"],
                "choch": rev["choch"],
                "bos": rev["bos"],
                "sweep": rev["sweep"]
            },
            "volatility": vol_metrics,
            "intraday_high": round(intraday_high, dec),
            "intraday_low": round(intraday_low, dec),
            "ob_high": ob_high,
            "ob_low": ob_low,
            "macro_reason": macro_reason,
            "news_warning": news_warning,
            "swing_potential": swing_info,
            "created_at": now_ts,
            "confluence": {
                "score": conf_score,
                "alignment": alignment,
                "verdict_title": verdict_title,
                "verdict_sub": verdict_sub,
            },
            "setup": {
                "direction": direction,
                "signal_tag": signal_tag,
                "entry": entry,
                "be_trigger": be_trigger,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
            },
            "candles": {
                "1d": c_1d,
                "4h": c_4h,
                "1h": c_1h,
            }
        }
    except Exception as e:
        print(f"Error procesando {cfg.get('symbol')}: {e}")
        return None

def build_correlated_baskets(assets, ccy_labels):
    baskets = []
    for ccy in ["USD", "GBP", "AUD", "EUR", "JPY", "CAD", "NZD", "CHF"]:
        st = ccy_labels.get(ccy, "NEUTRAL")
        if st == "NEUTRAL":
            continue
        matched_pairs = []
        for a in assets:
            if a["confluence"]["alignment"] != "ALIGNED":
                continue
            d = a["setup"]["direction"]
            if st == "FUERTE":
                if (a["base"] == ccy and d == "BUY") or (a["quote"] == ccy and d == "SELL"):
                    matched_pairs.append(f"{a['symbol']} ({'COMPRA' if d == 'BUY' else 'VENTA'})")
            elif st == "DÉBIL":
                if (a["base"] == ccy and d == "SELL") or (a["quote"] == ccy and d == "BUY"):
                    matched_pairs.append(f"{a['symbol']} ({'COMPRA' if d == 'BUY' else 'VENTA'})")
        if len(matched_pairs) >= 2:
            baskets.append({
                "currency": ccy,
                "status": st,
                "pairs": matched_pairs[:5]
            })
    return baskets

def dispatch_push_notifications(assets, now_ts):
    if not NTFY_TOPIC:
        return
    sent_state = load_sent_alerts()
    updated = False
    cooldown = 6 * 3600

    for a in assets:
        sym = a["symbol"]
        d_txt = "COMPRA" if a["setup"]["direction"] == "BUY" else "VENTA"
        is_swing = bool(a.get("swing_potential") and a["swing_potential"].get("active"))
        is_reentry = "RE-ENTRADA" in (a["setup"].get("signal_tag") or "").upper()

        if is_swing:
            key = f"SWING_{sym}_{a['setup']['direction']}"
            last_t = sent_state.get(key, 0)
            if (now_ts - last_t) > cooldown:
                sw_tp = a["swing_potential"]["target"]
                be_p = a["setup"].get("be_trigger", a["setup"]["entry"])
                body = (
                    f"{sym} ({d_txt}) · Confluencia {a['confluence']['score']}/100\n"
                    f"Entrada OB: {a['setup']['entry']} | SL: {a['setup']['sl']}\n"
                    f"Gatillo BE (+1R): {be_p} | TP1: {a['setup']['tp1']} | Swing TP: {sw_tp}"
                )
                send_mobile_push(f"POTENCIAL SWING: {sym} ({d_txt})", body, "high", "ocean,chart_with_upwards_trend")
                sent_state[key] = now_ts
                updated = True

        if is_reentry:
            key = f"REENTRY_{sym}_{a['setup']['direction']}"
            last_t = sent_state.get(key, 0)
            if (now_ts - last_t) > cooldown:
                body = (
                    f"{sym} ({d_txt}) confirmó re-entrada estructural.\n"
                    f"Nuevo bloque: {a['setup']['entry']} | SL: {a['setup']['sl']} | TP1: {a['setup']['tp1']}"
                )
                send_mobile_push(f"RE-ENTRADA PIRAMIDE: {sym}", body, "high", "large_blue_circle,rocket")
                sent_state[key] = now_ts
                updated = True

    if updated:
        save_sent_alerts(sent_state)

def main():
    now_utc = datetime.now(timezone.utc)
    now_ts = int(now_utc.timestamp())
    dxy_1d = get_candles("DX-Y.NYB", "3mo", "1d", 2, 45)
    dxy_4h = group_4h(get_candles("DX-Y.NYB", "1mo", "1h", 2, 180))
    us10y_1d = get_candles("^TNX", "3mo", "1d", 2, 45)
    us10y_4h = group_4h(get_candles("^TNX", "1mo", "1h", 2, 180))

    dxy_val = dxy_4h[-1]["c"] if dxy_4h else 104.20
    us10y_val = us10y_4h[-1]["c"] if us10y_4h else 4.25

    calendar_events, high_impact_by_ccy = fetch_high_impact_calendar(now_utc)

    bundles = {}
    c4_map = {}
    c1d_map = {}
    for cfg in ASSETS_CONFIG:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        c_1d = get_candles(cfg["yf"], "3mo", "1d", dec, 45)
        c_1h_long = get_candles(cfg["yf"], "1mo", "1h", dec, 180)
        c_4h = group_4h(c_1h_long)
        c_1h = c_1h_long[-45:] if c_1h_long else []
        bundles[sym] = {"1d": c_1d, "4h": c_4h, "1h": c_1h}
        c4_map[sym] = c_4h
        c1d_map[sym] = c_1d

    raw_strength, ccy_labels, spx_chg = compute_currency_strength_matrix(
        c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, c4_map.get("US500", []), c1d_map.get("US500", [])
    )
    assets = [item for cfg in ASSETS_CONFIG if (item := build_asset(cfg, bundles.get(cfg["symbol"], {}), raw_strength, ccy_labels, high_impact_by_ccy, now_ts))]
    banks = get_central_banks(dxy_val, us10y_val, ccy_labels)
    baskets = build_correlated_baskets(assets, ccy_labels)
    news = fetch_live_news()

    dispatch_push_notifications(assets, now_ts)

    alert_ccys = sorted(high_impact_by_ccy.keys())
    news_alert_str = f" · ⚠️ Noticias fuertes hoy en: {', '.join(alert_ccys)}" if alert_ccys else ""

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"USD {ccy_labels.get('USD')} (DXY {dxy_val} · US10Y {us10y_val}%) | GBP {ccy_labels.get('GBP')} | AUD {ccy_labels.get('AUD')}{news_alert_str}",
            "summary": f"App PWA v7.8 · Mesa Economía vs Gráfico, liquidez BSL/SSL, CHoCH/BOS, ATR y notificaciones Push sobre {len(assets)} activos."
        },
        "correlated_baskets": baskets,
        "banks": banks,
        "news": news,
        "calendar": calendar_events,
        "assets": assets
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(assets)} activos actualizados (v7.8 PWA + Notificaciones Push).")

if __name__ == "__main__":
    main()
