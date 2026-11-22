import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import yfinance as yf

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
ALERTS_STATE_FILE = "alerts_sent.json"
HISTORICAL_CUTOFF_TS = int(datetime(2017, 1, 1, tzinfo=timezone.utc).timestamp())

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

def send_mobile_push(title, body, priority="high", tags="dart,bell"):
    if not NTFY_TOPIC:
        return
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={
                "Title": title.encode("ascii", "ignore").decode("ascii"),
                "Priority": priority,
                "Tags": tags,
                "Click": "https://bab9618-hash.github.io/ultra/"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
        print(f"Alarma enviada: {title}")
    except Exception as e:
        print(f"Aviso push ntfy: {e}")

def get_candles(ticker_str, period, interval, decimals, limit=45):
    try:
        t = yf.Ticker(ticker_str)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty:
            return []
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if limit:
            df = df.tail(limit)
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

def find_clean_weekly_pivots_pre2017(c_1w_all, dec, pip):
    """
    Escanea el historial semanal anterior a 2017 buscando giros limpios en V (sin acumulación):
    - VENTA LIMPIA: 1 vela semanal alcista (verde) seguida inmediatamente de 1 vela semanal bajista (roja)
      con caída directa posterior y sin consolidación previa.
    - COMPRA LIMPIA: 1 vela semanal bajista (roja) seguida inmediatamente de 1 vela semanal alcista (verde)
      con subida directa posterior y sin consolidación previa.
    """
    buy_pivots = []
    sell_pivots = []
    if not c_1w_all or len(c_1w_all) < 10:
        return buy_pivots, sell_pivots

    for i in range(4, len(c_1w_all) - 3):
        c1 = c_1w_all[i]      # Vela de llegada
        c2 = c_1w_all[i + 1]  # Vela única de rechazo / cambio de dirección
        if c2["t"] >= HISTORICAL_CUTOFF_TS:
            break

        prev_slice = c_1w_all[i - 3:i]
        next_slice = c_1w_all[i + 2:i + 4]

        b1 = abs(c1["c"] - c1["o"])
        b2 = abs(c2["c"] - c2["o"])
        r1 = max(pip, c1["h"] - c1["l"])
        r2 = max(pip, c2["h"] - c2["l"])

        if b1 < r1 * 0.45 or b2 < r2 * 0.45:
            continue

        year_str = datetime.fromtimestamp(c2["t"], tz=timezone.utc).strftime("%Y-%m-%d")

        # --- PATRÓN VENTA LIMPIA: 1 Verde + 1 Roja sin acumulación ---
        if c1["c"] > c1["o"] and c2["c"] < c2["o"]:
            came_up_clean = (prev_slice[0]["o"] < c1["o"]) and (max(x["h"] for x in prev_slice) <= c1["h"])
            drops_clean = (c2["c"] <= c1["o"] + b1 * 0.35) and (min(x["l"] for x in next_slice) < c2["l"])
            pivot_high = max(c1["h"], c2["h"])
            no_immediate_chop = max(x["h"] for x in next_slice) < pivot_high
            if came_up_clean and drops_clean and no_immediate_chop:
                entry_lvl = round((c1["c"] + pivot_high) / 2.0, dec)
                sell_pivots.append({
                    "entry": entry_lvl,
                    "extreme": round(pivot_high, dec),
                    "date": year_str
                })

        # --- PATRÓN COMPRA LIMPIA: 1 Roja + 1 Verde sin acumulación ---
        if c1["c"] < c1["o"] and c2["c"] > c2["o"]:
            came_down_clean = (prev_slice[0]["o"] > c1["o"]) and (min(x["l"] for x in prev_slice) >= c1["l"])
            rises_clean = (c2["c"] >= c1["o"] - b1 * 0.35) and (max(x["h"] for x in next_slice) > c2["h"])
            pivot_low = min(c1["l"], c2["l"])
            no_immediate_chop = min(x["l"] for x in next_slice) > pivot_low
            if came_down_clean and rises_clean and no_immediate_chop:
                entry_lvl = round((c1["c"] + pivot_low) / 2.0, dec)
                buy_pivots.append({
                    "entry": entry_lvl,
                    "extreme": round(pivot_low, dec),
                    "date": year_str
                })

    return buy_pivots, sell_pivots

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
        return {
            "choch": "NONE", "sweep": "NONE", "bos": "NONE",
            "reversal_dir": "NONE", "strong_pullback": False,
            "bsl": swing_h, "ssl": swing_l
        }

    window = c_1h[-20:-2]
    last_two = c_1h[-2:]
    curr = last_two[-1]
    prev = c_1h[-3]
    swing_high = round(max(x["h"] for x in window), dec)
    swing_low = round(min(x["l"] for x in window), dec)

    avg_body = sum(abs(x["c"] - x["o"]) for x in c_1h[-12:-2]) / 10.0
    curr_body = abs(curr["c"] - curr["o"])
    has_displacement = avg_body > 0 and (curr_body >= avg_body * 1.4)

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
    strong_pullback = False
    if choch == "BULLISH_CHOCH" and has_displacement:
        reversal_dir = "SUBE"
        strong_pullback = True
    elif choch == "BEARISH_CHOCH" and has_displacement:
        reversal_dir = "BAJA"
        strong_pullback = True

    return {
        "choch": choch,
        "bos": bos,
        "sweep": sweep,
        "reversal_dir": reversal_dir,
        "strong_pullback": strong_pullback,
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

def get_central_banks(dxy_val, us10
