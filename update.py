import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import yfinance as yf

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
ALERTS_STATE_FILE = "alerts_sent.json"
SETUPS_STATE_FILE = "active_setups.json"
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


def load_json_state(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_json_state(path, state):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def send_ntfy_alert(title, message, priority="default", tags="chart_with_upwards_trend"):
    if not NTFY_TOPIC:
        return False
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        clean_title = title.encode("ascii", "ignore").decode("ascii").strip() or "LATICCE ALERTA"
        req = urllib.request.Request(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": clean_title,
                "Priority": priority,
                "Tags": tags,
                "Content-Type": "text/plain; charset=utf-8"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def get_candles(ticker, period, interval, decimals, max_bars=60):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        if df is None or df.empty:
            return []
        if hasattr(df.columns, "levels") and len(df.columns.levels) > 1:
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        out = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp()) if hasattr(idx, "timestamp") else 0
            out.append({
                "t": ts,
                "o": round(float(row["Open"]), decimals),
                "h": round(float(row["High"]), decimals),
                "l": round(float(row["Low"]), decimals),
                "c": round(float(row["Close"]), decimals),
            })
        return out[-max_bars:] if max_bars else out
    except Exception:
        return []


def group_4h(candles_1h):
    if not candles_1h:
        return []
    grouped = []
    for i in range(0, len(candles_1h), 4):
        chunk = candles_1h[i:i + 4]
        if not chunk:
            continue
        grouped.append({
            "t": chunk[0]["t"],
            "o": chunk[0]["o"],
            "h": max(x["h"] for x in chunk),
            "l": min(x["l"] for x in chunk),
            "c": chunk[-1]["c"],
        })
    return grouped[-45:]


def calc_ema(values, period):
    if not values:
        return 0.0
    k = 2.0 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1.0 - k)
    return ema


def calc_atr(candles, period=14):
    if not candles or len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["h"]
        l = candles[i]["l"]
        pc = candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return 0.0
    recent = trs[-period:]
    return sum(recent) / len(recent)


def analyze_tf_bias(candles):
    if not candles or len(candles) < 8:
        return "NEUTRAL", 0.0
    closes = [x["c"] for x in candles]
    last = closes[-1]
    ema_fast = calc_ema(closes[-18:], 8)
    ema_slow = calc_ema(closes[-30:], 21)
    prev_ref = closes[-6]
    pct = ((last - prev_ref) / prev_ref) * 100.0 if prev_ref else 0.0

    if last > ema_fast and ema_fast >= ema_slow and pct > 0.03:
        return "SUBE", round(pct, 2)
    if last < ema_fast and ema_fast <= ema_slow and pct < -0.03:
        return "BAJA", round(pct, 2)
    return "NEUTRAL", round(pct, 2)


def detect_exhaustion(candles, bias):
    if not candles or len(candles) < 8 or bias not in ("SUBE", "BAJA"):
        return False, ""
    recent = candles[-8:]
    c_last = recent[-1]
    c_prev = recent[-2]
    body_last = abs(c_last["c"] - c_last["o"])
    upper_wick = c_last["h"] - max(c_last["o"], c_last["c"])
    lower_wick = min(c_last["o"], c_last["c"]) - c_last["l"]

    if bias == "SUBE":
        hi_8 = max(x["h"] for x in recent[:-1])
        if c_last["h"] >= hi_8 * 0.9995 and (upper_wick > body_last * 1.4 or c_last["c"] < c_prev["c"]):
            return True, "Mecha de rechazo en techo reciente (posible toma de ganancias)."
    else:
        lo_8 = min(x["l"] for x in recent[:-1])
        if c_last["l"] <= lo_8 * 1.0005 and (lower_wick > body_last * 1.4 or c_last["c"] > c_prev["c"]):
            return True, "Mecha de rechazo en piso reciente (posible rebote tecnico)."
    return False, ""


def detect_liquidity_and_structure(candles, dec):
    if not candles or len(candles) < 10:
        return {
            "bsl": 0.0, "ssl": 0.0, "event_type": None, "event_dir": None,
            "event_price": 0.0, "event_desc": ""
        }
    window = candles[-25:-1] if len(candles) > 25 else candles[:-1]
    bsl = round(max(x["h"] for x in window), dec)
    ssl = round(min(x["l"] for x in window), dec)
    last = candles[-1]
    prev = candles[-2]

    event_type = None
    event_dir = None
    event_price = 0.0
    event_desc = ""

    if last["h"] > bsl and last["c"] < bsl:
        event_type = "BARRIDO BSL"
        event_dir = "BAJA"
        event_price = bsl
        event_desc = f"Barrido de liquidez sobre {bsl} con cierre debajo (posible giro bajista)."
    elif last["l"] < ssl and last["c"] > ssl:
        event_type = "BARRIDO SSL"
        event_dir = "SUBE"
        event_price = ssl
        event_desc = f"Barrido de liquidez bajo {ssl} con absorcion alcista (posible giro alcista)."
    elif last["c"] > bsl and prev["c"] <= bsl:
        event_type = "BOS / CHoCH ALCISTA"
        event_dir = "SUBE"
        event_price = bsl
        event_desc = f"Quiebre con cuerpo sobre {bsl}."
    elif last["c"] < ssl and prev["c"] >= ssl:
        event_type = "BOS / CHoCH BAJISTA"
        event_dir = "BAJA"
        event_price = ssl
        event_desc = f"Quiebre con cuerpo bajo {ssl}."

    return {
        "bsl": bsl,
        "ssl": ssl,
        "event_type": event_type,
        "event_dir": event_dir,
        "event_price": event_price,
        "event_desc": event_desc,
    }


def scan_institutional_zone(candles, direction, price, atr, pip, dec):
    if not candles or len(candles) < 12 or direction not in ("SUBE", "BAJA"):
        return None

    recent = candles[-24:]
    min_imp = max(atr * 0.45, pip * 6)
    candidates = []

    for i in range(len(recent) - 3, 1, -1):
        c0 = recent[i - 1]
        c1 = recent[i]
        c2 = recent[i + 1]
        c3 = recent[i + 2]

        if direction == "SUBE":
            is_bear_ob = c1["c"] < c1["o"]
            imp_size = c2["c"] - c1["l"]
            has_fvg = c3["l"] > c1["h"]
            if is_bear_ob and imp_size >= min_imp:
                zone_hi = round(max(c1["o"], c1["h"]), dec)
                zone_lo = round(min(c1["l"], c0["l"]), dec)
                entry = zone_hi
                sl = round(zone_lo - max(pip * 3, atr * 0.12), dec)
                if price >= sl and entry < price * 1.015:
                    tier = 1 if has_fvg else 2
                    tag = "COMPRA OB + FVG" if has_fvg else "COMPRA OB ESTRUCTURAL"
                    candidates.append((tier, i, tag, entry, sl, zone_hi, zone_lo))
            elif has_fvg and (c2["c"] - c2["o"]) >= min_imp * 0.8:
                zone_hi = round(c3["l"], dec)
                zone_lo = round(c1["h"], dec)
                entry = zone_hi
                sl = round(c1["l"] - max(pip * 3, atr * 0.12), dec)
                if price >= sl and entry < price * 1.015:
                    candidates.append((3, i, "COMPRA FVG RETROCESO", entry, sl, zone_hi, zone_lo))
        else:
            is_bull_ob = c1["c"] > c1["o"]
            imp_size = c1["h"] - c2["c"]
            has_fvg = c3["h"] < c1["l"]
            if is_bull_ob and imp_size >= min_imp:
                zone_lo = round(min(c1["o"], c1["l"]), dec)
                zone_hi = round(max(c1["h"], c0["h"]), dec)
                entry = zone_lo
                sl = round(zone_hi + max(pip * 3, atr * 0.12), dec)
                if price <= sl and entry > price * 0.985:
                    tier = 1 if has_fvg else 2
                    tag = "VENTA OB + FVG" if has_fvg else "VENTA OB ESTRUCTURAL"
                    candidates.append((tier, i, tag, entry, sl, zone_hi, zone_lo))
            elif has_fvg and (c2["o"] - c2["c"]) >= min_imp * 0.8:
                zone_lo = round(c3["h"], dec)
                zone_hi = round(c1["l"], dec)
                entry = zone_lo
                sl = round(c1["h"] + max(pip * 3, atr * 0.12), dec)
                if price <= sl and entry > price * 0.985:
                    candidates.append((3, i, "VENTA FVG RETROCESO", entry, sl, zone_hi, zone_lo))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], -x[1]))
    tier, _, tag, entry, sl, z_hi, z_lo = candidates[0]
    risk = abs(entry - sl)
    if risk <= 0:
        return None

    if direction == "SUBE":
        be_trigger = round(entry + risk * 1.0, dec)
        tp1 = round(entry + risk * 2.0, dec)
        tp2 = round(entry + risk * 3.0, dec)
        swing_tp = round(entry + risk * 4.2, dec)
        side = "BUY"
    else:
        be_trigger = round(entry - risk * 1.0, dec)
        tp1 = round(entry - risk * 2.0, dec)
        tp2 = round(entry - risk * 3.0, dec)
        swing_tp = round(entry - risk * 4.2, dec)
        side = "SELL"

    return {
        "tier": tier,
        "direction": side,
        "signal_tag": tag,
        "entry": entry,
        "sl": sl,
        "be_trigger": be_trigger,
        "tp1": tp1,
        "tp2": tp2,
        "swing_tp": swing_tp,
        "ob_high": z_hi,
        "ob_low": z_lo,
    }


def find_clean_weekly_pivots_pre2017(candles_1w, dec):
    buys, sells = [], []
    if not candles_1w or len(candles_1w) < 6:
        return buys, sells

    for i in range(3, len(candles_1w) - 2):
        c = candles_1w[i]
        if c["t"] >= HISTORICAL_CUTOFF_TS:
            continue
        prev1 = candles_1w[i - 1]
        prev2 = candles_1w[i - 2]
        nxt = candles_1w[i + 1]

        rng = max(1e-9, c["h"] - c["l"])
        body = abs(c["c"] - c["o"])
        date_str = datetime.fromtimestamp(c["t"], tz=timezone.utc).strftime("%Y-%m-%d")

        if prev1["c"] < prev1["o"] and c["l"] < prev1["l"] and c["l"] < prev2["l"] and nxt["c"] > c["h"]:
            if body / rng >= 0.35 or (min(c["o"], c["c"]) - c["l"]) >= rng * 0.45:
                buys.append({
                    "direction": "BUY",
                    "entry": round(max(c["o"], c["c"]), dec),
                    "extreme": round(c["l"], dec),
                    "date": date_str
                })

        if prev1["c"] > prev1["o"] and c["h"] > prev1["h"] and c["h"] > prev2["h"] and nxt["c"] < c["l"]:
            if body / rng >= 0.35 or (c["h"] - max(c["o"], c["c"])) >= rng * 0.45:
                sells.append({
                    "direction": "SELL",
                    "entry": round(min(c["o"], c["c"]), dec),
                    "extreme": round(c["h"], dec),
                    "date": date_str
                })

    return buys[-40:], sells[-40:]


def pct_change_4h(candles, bars=6):
    if not candles or len(candles) <= bars:
        return 0.0
    p0 = candles[-1 - bars]["c"]
    p1 = candles[-1]["c"]
    return ((p1 - p0) / p0) * 100.0 if p0 else 0.0


def compute_currency_strength_matrix(c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, spx_4h, spx_1d):
    def blend_chg(c4, c1d):
        return (pct_change_4h(c4, 6) * 0.60) + (pct_change_4h(c1d, 5) * 0.40)

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
    labels = {k: ("FUERTE" if v > 0.14 else ("DEBIL" if v < -0.14 else "NEUTRAL")) for k, v in raw.items()}
    return raw, labels, round(spx_chg, 2)


def fetch_high_impact_calendar(now_utc):
    events = []
    high_by_ccy = {}
    today_str = now_utc.strftime("%Y-%m-%d")
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for ev in data:
            if ev.get("impact") != "High":
                continue
            ev_date = str(ev.get("date", ""))[:10]
            if ev_date != today_str:
                continue
            ccy = str(ev.get("country", "")).upper()
            title = str(ev.get("title", "Evento Alto Impacto"))
            t_str = str(ev.get("date", ""))[11:16] or "Hoy"
            events.append({
                "time": f"{t_str} UTC",
                "currency": ccy,
                "impact": "ALTO",
                "title": title,
                "forecast": ev.get("forecast", "-"),
                "previous": ev.get("previous", "-"),
            })
            high_by_ccy.setdefault(ccy, []).append(title)
    except Exception:
        pass

    if not events:
        events = [
            {"time": "13:30 UTC", "currency": "USD", "impact": "MEDIO", "title": "Apertura Sesion Nueva York / Flujo Institucional", "forecast": "-", "previous": "-"},
            {"time": "15:00 UTC", "currency": "USD", "impact": "MEDIO", "title": "Fijacion de Liquidez Londres / NY", "forecast": "-", "previous": "-"},
        ]
    return events[:12], high_by_ccy


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
        news_items = [{"source": "Radar Institucional", "title": "Flujos de liquidez activos en sesiones principales.", "link": "#", "time": "En linea"}]
    return news_items[:8]


def build_asset(cfg, candles_bundle, raw_strength, ccy_labels, high_impact_by_ccy, now_ts, active_setups):
    try:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        pip = cfg["pip"]
        c_1d = candles_bundle.get("1d", [])
        c_4h = candles_bundle.get("4h", [])
        c_1h = candles_bundle.get("1h", [])
        c_1w = candles_bundle.get("1w_all", [])

        if not c_1h or not c_4h or not c_1d:
            return None

        price = c_1h[-1]["c"]
        b_w, _ = analyze_tf_bias(c_1w[-35:] if len(c_1w) >= 35 else c_1w)
        b_d, _ = analyze_tf_bias(c_1d)
        b_4h, _ = analyze_tf_bias(c_4h)
        b_1h, _ = analyze_tf_bias(c_1h)

        score_tech = 0
        for b, w in [(b_d, 3), (b_4h, 2), (b_1h, 1)]:
            if b == "SUBE":
                score_tech += w
            elif b == "BAJA":
                score_tech -= w

        chart_bias = "SUBE" if score_tech >= 2 else ("BAJA" if score_tech <= -2 else "NEUTRAL")

        base_c = cfg["base"]
        quote_c = cfg["quote"]
        if cfg["type"] in ("index", "crypto"):
            m_diff = raw_strength.get("BTC", 0.0)
        elif cfg["type"] == "metal":
            m_diff = raw_strength.get("XAU", 0.0)
        else:
            m_diff = raw_strength.get(base_c, 0.0) - raw_strength.get(quote_c, 0.0)

        macro_dir = "SUBE" if m_diff > 0.16 else ("BAJA" if m_diff < -0.16 else "NEUTRAL")

        atr_val = round(calc_atr(c_1d, 14), dec)
        atr_units = round(atr_val / pip, 1) if pip else 0.0
        r20_hi = max(x["h"] for x in c_1d[-20:])
        r20_lo = min(x["l"] for x in c_1d[-20:])
        r20_val = round(r20_hi - r20_lo, dec)
        r20_units = round(r20_val / pip, 1) if pip else 0.0

        exhausted, ex_reason = detect_exhaustion(c_4h, chart_bias)
        liq = detect_liquidity_and_structure(c_4h, dec)

        scan_dir = chart_bias if chart_bias in ("SUBE", "BAJA") else (macro_dir if macro_dir in ("SUBE", "BAJA") else "NEUTRAL")
        setup = scan_institutional_zone(c_1h if len(c_1h) >= 16 else c_4h, scan_dir, price, atr_val, pip, dec)

        if macro_dir == "NEUTRAL" or chart_bias == "NEUTRAL":
            alignment = "NEUTRAL"
            score = 52 if setup else 42
            verdict_title = "SIN DIRECCION CLARA - UNO ESTA NEUTRAL"
            verdict_sub = "Esperar a que Economia y Grafico definan tendencia."
        elif macro_dir == chart_bias:
            alignment = "ALIGNED"
            base_s = 78 + (6 if b_d == chart_bias else 0) + (4 if b_4h == chart_bias else 0) + (4 if setup and setup["tier"] == 1 else 0)
            score = min(96, base_s - (14 if exhausted else 0))
            if exhausted:
                verdict_title = "AGOTAMIENTO - RIESGO DE GIRO"
                verdict_sub = ex_reason
            elif setup:
                verdict_title = f"VAN JUNTOS - BUSCAR {'COMPRAS' if chart_bias == 'SUBE' else 'VENTAS'}"
                verdict_sub = f"{setup['signal_tag']} respaldado por flujo macro."
            else:
                verdict_title = "VAN JUNTOS - SIN OB/FVG LIMPIO AUN"
                verdict_sub = "Direccion confirmada; esperar bloque institucional."
        else:
            alignment = "BROKEN"
            score = 35
            verdict_title = "SE CONTRADICEN - ESPERAR"
            verdict_sub = f"Economia apunta {macro_dir} pero grafico muestra {chart_bias}."

        swing_potential = None
        if (
            setup
            and alignment == "ALIGNED"
            and b_d == chart_bias
            and b_4h == chart_bias
            and b_1h == chart_bias
            and score >= 84
            and not exhausted
        ):
            swing_potential = {
                "active": True,
                "swing_tp": setup["swing_tp"],
                "be_trigger": setup["be_trigger"],
                "plan": "1) Proteger en BE al tocar +1R. 2) Cobrar parcial en TP1. 3) Piramidar en retrocesos hacia Swing TP."
            }

        affected_news = []
        for ccy in {base_c, quote_c}:
            if ccy in high_impact_by_ccy:
                affected_news.extend([f"{ccy}: {t}" for t in high_impact_by_ccy[ccy]])
        news_warning = " | ".join(affected_news[:2]) if affected_news else None

        hist_buys, hist_sells = find_clean_weekly_pivots_pre2017(c_1w, dec)
        nearby_weekly_pivots = []
        current_trend = b_d if b_d in ("SUBE", "BAJA") else chart_bias
        for p in (hist_buys + hist_sells):
            if current_trend == "SUBE" and p["direction"] != "SELL":
                continue
            if current_trend == "BAJA" and p["direction"] != "BUY":
                continue
            if p["direction"] == "SELL" and price >= p["entry"]:
                continue
            if p["direction"] == "BUY" and price <= p["entry"]:
                continue

            dist_u = round((abs(price - p["entry"]) / pip) * 10) / 10 if pip else abs(price - p["entry"])
            pct_d = abs(price - p["entry"]) / max(1e-9, price)
            within_range = (dist_u <= 60.0) if cfg["type"] == "forex" else ((dist_u <= 100.0) if cfg["type"] == "metal" else (pct_d <= 0.004))
            if within_range:
                macro_ok = (p["direction"] == "BUY" and macro_dir == "SUBE") or (p["direction"] == "SELL" and macro_dir == "BAJA")
                nearby_weekly_pivots.append({
                    "symbol": sym,
                    "type": cfg["type"],
                    "decimals": dec,
                    "pip": pip,
                    "price": price,
                    "direction": p["direction"],
                    "entry": p["entry"],
                    "extreme": p["extreme"],
                    "date": p["date"],
                    "dist_units": dist_u,
                    "unit_label": "pips" if cfg["type"] in ("forex", "metal") else "pts",
                    "macro_aligned": macro_ok,
                })

        setup_sig = f"{setup['direction']}_{setup['entry']}" if setup else "NONE"
        prev_state = active_setups.get(sym, {})
        if setup and prev_state.get("sig") == setup_sig:
            created_at = prev_state.get("created_at", now_ts)
        else:
            created_at = now_ts
            active_setups[sym] = {"sig": setup_sig, "created_at": created_at}

        return {
            "symbol": sym,
            "type": cfg["type"],
            "pip": pip,
            "decimals": dec,
            "price": price,
            "chart_bias": chart_bias,
            "macro_dir": macro_dir,
            "tf_biases": {"1w": b_w, "1d": b_d, "4h": b_4h, "1h": b_1h},
            "volatility": {
                "atr": atr_val,
                "atr_units": atr_units,
                "range20": r20_val,
                "range20_units": r20_units,
            },
            "liquidity": liq,
            "intraday_high": round(max(x["h"] for x in c_1h[-12:]), dec),
            "intraday_low": round(min(x["l"] for x in c_1h[-12:]), dec),
            "ob_high": setup["ob_high"] if setup else round(max(x["h"] for x in c_1h[-12:]), dec),
            "ob_low": setup["ob_low"] if setup else round(min(x["l"] for x in c_1h[-12:]), dec),
            "macro_reason": f"Jerarquia (1S:{b_w}, 1D:{b_d}, 4H:{b_4h}, 1H:{b_1h}). {verdict_sub}",
            "news_warning": news_warning,
            "swing_potential": swing_potential,
            "weekly_pivots": nearby_weekly_pivots,
            "created_at": created_at,
            "confluence": {
                "score": score,
                "alignment": alignment,
                "verdict_title": verdict_title,
                "verdict_sub": verdict_sub,
            },
            "setup": setup,
            "candles": {
                "1d": c_1d[-35:],
                "4h": c_4h[-35:],
                "1h": c_1h[-35:],
            },
        }
    except Exception:
        return None


def get_central_banks(dxy_val, us10y_val, ccy_labels):
    return [
        {"bank": "FED (EE.UU.)", "currency": "USD", "stance": f"USD {ccy_labels.get('USD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("USD") == "FUERTE" else ("BEARISH" if ccy_labels.get("USD") == "DEBIL" else "NEUTRAL"), "detail": f"DXY ({dxy_val}) + Bonos US10Y ({us10y_val}%) en cesta hibrida 4H/1D."},
        {"bank": "BoE (Reino Unido)", "currency": "GBP", "stance": f"GBP {ccy_labels.get('GBP', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("GBP") == "FUERTE" else ("BEARISH" if ccy_labels.get("GBP") == "DEBIL" else "NEUTRAL"), "detail": "Cesta hibrida GBPUSD + GBPJPY + GBPAUD (60% 4H + 40% 1D)."},
        {"bank": "RBA (Australia)", "currency": "AUD", "stance": f"AUD {ccy_labels.get('AUD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("AUD") == "FUERTE" else ("BEARISH" if ccy_labels.get("AUD") == "DEBIL" else "NEUTRAL"), "detail": "Cesta hibrida AUDUSD + AUDJPY + AUDNZD + riesgo US500 (4H/1D)."},
        {"bank": "BCE (Eurozona)", "currency": "EUR", "stance": f"EUR {ccy_labels.get('EUR', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("EUR") == "FUERTE" else ("BEARISH" if ccy_labels.get("EUR") == "DEBIL" else "NEUTRAL"), "detail": "Cesta hibrida EURUSD + EURJPY + EURAUD (60% 4H + 40% 1D)."},
        {"bank": "BoJ (Japon)", "currency": "JPY", "stance": f"JPY {ccy_labels.get('JPY', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("JPY") == "FUERTE" else ("BEARISH" if ccy_labels.get("JPY") == "DEBIL" else "NEUTRAL"), "detail": "Flujo inverso en cruces JPY (60% 4H + 40% 1D)."}
    ]


def build_correlated_baskets(assets, ccy_labels):
    baskets = []
    for ccy in ["USD", "GBP", "AUD", "EUR", "JPY"]:
        st = ccy_labels.get(ccy, "NEUTRAL")
        if st == "NEUTRAL":
            continue
        members = []
        for a in assets:
            sym = a["symbol"]
            if ccy not in sym or a["type"] != "forex":
                continue
            is_base = sym.startswith(ccy)
            suggested = ("COMPRA" if is_base else "VENTA") if st == "FUERTE" else ("VENTA" if is_base else "COMPRA")
            members.append(f"{sym} ({suggested})")
        if members:
            baskets.append({"currency": ccy, "status": st, "pairs": members[:4]})
    return baskets


def compute_best_focus_pick(assets):
    ranked = []
    for a in assets:
        if not a.get("setup") or a["confluence"]["alignment"] != "ALIGNED":
            continue
        prob = a["confluence"]["score"]
        if a.get("swing_potential"):
            prob = min(98, prob + 5)
        if a["setup"]["tier"] == 1:
            prob = min(98, prob + 3)
        if a.get("news_warning"):
            prob -= 6
        ranked.append((prob, a))

    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return None

    best_prob, best = ranked[0]
    s = best["setup"]
    return {
        "primary": {
            "symbol": best["symbol"],
            "probability": best_prob,
            "direction": s["direction"],
            "signal_tag": s["signal_tag"],
            "entry": s["entry"],
            "sl": s["sl"],
            "tp1": s["tp1"],
            "swing_potential": bool(best.get("swing_potential")),
            "reason": best["confluence"]["verdict_sub"],
        }
    }


def dispatch_push_notifications(assets, now_ts):
    if not NTFY_TOPIC:
        return
    sent_state = load_json_state(ALERTS_STATE_FILE)
    cooldown = 6 * 3600

    for a in assets:
        sym = a["symbol"]
        s = a.get("setup")
        if not s:
            continue
        if a.get("swing_potential"):
            key = f"SWING_{sym}_{s['direction']}"
            if now_ts - sent_state.get(key, 0) > cooldown:
                msg = f"{sym} ({s['direction']}) | Entrada: {s['entry']} | SL: {s['sl']} | BE: {s['be_trigger']} | Swing TP: {s['swing_tp']}"
                if send_ntfy_alert(f"LATICCE SWING: {sym}", msg, priority="high", tags="rocket"):
                    sent_state[key] = now_ts

    save_json_state(ALERTS_STATE_FILE, sent_state)


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
        c_1w_all = get_candles(cfg["yf"], "max", "1wk", dec, None)
        bundles[sym] = {"1d": c_1d, "4h": c_4h, "1h": c_1h, "1w_all": c_1w_all}
        c4_map[sym] = c_4h
        c1d_map[sym] = c_1d

    raw_strength, ccy_labels, _ = compute_currency_strength_matrix(
        c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, c4_map.get("US500", []), c1d_map.get("US500", [])
    )

    active_setups = load_json_state(SETUPS_STATE_FILE)
    assets = [
        item for cfg in ASSETS_CONFIG
        if (item := build_asset(cfg, bundles.get(cfg["symbol"], {}), raw_strength, ccy_labels, high_impact_by_ccy, now_ts, active_setups))
    ]
    save_json_state(SETUPS_STATE_FILE, active_setups)

    banks = get_central_banks(dxy_val, us10y_val, ccy_labels)
    baskets = build_correlated_baskets(assets, ccy_labels)
    focus_pick = compute_best_focus_pick(assets)
    news = fetch_live_news()

    all_weekly_pivots = []
    for a in assets:
        all_weekly_pivots.extend(a.get("weekly_pivots", []))
    all_weekly_pivots.sort(key=lambda x: x["dist_units"])

    dispatch_push_notifications(assets, now_ts)

    alert_ccys = sorted(high_impact_by_ccy.keys())
    news_alert_str = f" - Noticias fuertes hoy en: {', '.join(alert_ccys)}" if alert_ccys else ""
    focus_str = f" | Foco #1: {focus_pick['primary']['symbol']} ({focus_pick['primary']['probability']}% prob)" if (focus_pick and focus_pick.get("primary")) else ""

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"USD {ccy_labels.get('USD')} (DXY {dxy_val} - US10Y {us10y_val}%) | GBP {ccy_labels.get('GBP')} | AUD {ccy_labels.get('AUD')}{news_alert_str}",
            "summary": f"LATICCE v10.0 - Radar Foco Principal + Mesa de Swing + Cascada OB/FVG ({len(all_weekly_pivots)} niveles 1S){focus_str}."
        },
        "focus_pick": focus_pick,
        "weekly_pivots": all_weekly_pivots,
        "correlated_baskets": baskets,
        "banks": banks,
        "news": news,
        "calendar": calendar_events,
        "assets": assets
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(assets)} activos actualizados (LATICCE v10.0).")


if __name__ == "__main__":
    main()
