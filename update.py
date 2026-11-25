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
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def save_json_state(path, state):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Aviso guardando {path}: {e}")


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
                "Content-Type": "text/plain; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
    except Exception as e:
        print(f"Aviso envio ntfy: {e}")


def get_candles(ticker, period, interval, decimals, max_bars=45):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if df is None or df.empty:
            return []
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        candles = []
        for idx, row in df.iterrows():
            try:
                o = float(row["Open"])
                h = float(row["High"])
                l = float(row["Low"])
                c = float(row["Close"])
                if any(v != v for v in (o, h, l, c)):
                    continue
                ts = int(idx.timestamp()) if hasattr(idx, "timestamp") else 0
                candles.append({
                    "t": ts,
                    "o": round(o, decimals),
                    "h": round(h, decimals),
                    "l": round(l, decimals),
                    "c": round(c, decimals),
                })
            except Exception:
                continue
        if max_bars is None:
            return candles
        return candles[-max_bars:]
    except Exception as e:
        print(f"Aviso descarga {ticker} ({interval}): {e}")
        return []


def group_4h(c_1h_long):
    if not c_1h_long:
        return []
    grouped = []
    for i in range(0, len(c_1h_long), 4):
        chunk = c_1h_long[i:i + 4]
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


def pct_change_lookback(candles, lookback=6):
    if not candles or len(candles) < lookback:
        return 0.0
    first = candles[-lookback]["c"]
    last = candles[-1]["c"]
    return ((last - first) / first) * 100.0 if first else 0.0


def calc_atr_14(c_1d, dec):
    if not c_1d or len(c_1d) < 3:
        return 0.0
    trs = []
    for i in range(1, len(c_1d)):
        h = c_1d[i]["h"]
        l = c_1d[i]["l"]
        pc = c_1d[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    recent = trs[-14:]
    return round(sum(recent) / len(recent), dec) if recent else 0.0


def calc_range_20d(c_1d, price, dec):
    if not c_1d:
        return {"high": price, "low": price, "pos_pct": 50}
    sub = c_1d[-20:]
    hi = round(max(x["h"] for x in sub), dec)
    lo = round(min(x["l"] for x in sub), dec)
    span = max(1e-9, hi - lo)
    pos = int(round(max(0.0, min(100.0, ((price - lo) / span) * 100.0))))
    return {"high": hi, "low": lo, "pos_pct": pos}


def detect_weekly_clean_pivots(c_1w_all, price, pip, dec, a_type, sym, macro_dir):
    if not c_1w_all or len(c_1w_all) < 10:
        return []
    max_units = 60.0 if (a_type in ("forex", "metal") or sym == "XAUUSD") else 999999.0
    max_pct = 0.015 if a_type not in ("forex", "metal") else 0.05
    pivots = []

    for i in range(4, len(c_1w_all) - 4):
        c_curr = c_1w_all[i]
        ts = c_curr.get("t", 0)
        if ts <= 0 or ts >= HISTORICAL_CUTOFF_TS:
            continue

        prev4 = c_1w_all[i - 4:i]
        next4 = c_1w_all[i + 1:i + 5]
        c_prev1 = c_1w_all[i - 1]
        c_next1 = c_1w_all[i + 1]

        prev_high = max(x["h"] for x in prev4)
        next_high = max(x["h"] for x in next4)
        prev_low = min(x["l"] for x in prev4)
        next_low = min(x["l"] for x in next4)

        rng = max(1e-9, c_curr["h"] - c_curr["l"])
        body_top = max(c_curr["o"], c_curr["c"])
        body_bot = min(c_curr["o"], c_curr["c"])
        upper_wick = c_curr["h"] - body_top
        lower_wick = body_bot - c_curr["l"]

        dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

        # Giro bajista limpio (1 vela sube + 1 vela unica rechaza arriba)
        if (
            c_curr["h"] > prev_high
            and c_curr["h"] > next_high
            and c_prev1["c"] > c_prev1["o"]
            and c_next1["c"] < c_next1["o"]
            and upper_wick >= rng * 0.30
        ):
            entry_lvl = round(body_top, dec)
            ext_lvl = round(c_curr["h"], dec)
            if price < entry_lvl:
                dist_u = round((entry_lvl - price) / max(1e-9, pip), 1)
                pct_d = (entry_lvl - price) / max(1e-9, price)
                if (a_type in ("forex", "metal") and dist_u <= max_units) or (
                    a_type not in ("forex", "metal") and pct_d <= max_pct
                ):
                    pivots.append({
                        "symbol": sym,
                        "type": a_type,
                        "decimals": dec,
                        "pip": pip,
                        "price": price,
                        "direction": "SELL",
                        "entry": entry_lvl,
                        "extreme": ext_lvl,
                        "date": dt_str,
                        "dist_units": dist_u,
                        "unit_label": "pips" if a_type in ("forex", "metal") else "pts",
                        "macro_aligned": (macro_dir == "BAJA"),
                    })

        # Giro alcista limpio (1 vela cae + 1 vela unica rechaza abajo)
        if (
            c_curr["l"] < prev_low
            and c_curr["l"] < next_low
            and c_prev1["c"] < c_prev1["o"]
            and c_next1["c"] > c_next1["o"]
            and lower_wick >= rng * 0.30
        ):
            entry_lvl = round(body_bot, dec)
            ext_lvl = round(c_curr["l"], dec)
            if price > entry_lvl:
                dist_u = round((price - entry_lvl) / max(1e-9, pip), 1)
                pct_d = (price - entry_lvl) / max(1e-9, price)
                if (a_type in ("forex", "metal") and dist_u <= max_units) or (
                    a_type not in ("forex", "metal") and pct_d <= max_pct
                ):
                    pivots.append({
                        "symbol": sym,
                        "type": a_type,
                        "decimals": dec,
                        "pip": pip,
                        "price": price,
                        "direction": "BUY",
                        "entry": entry_lvl,
                        "extreme": ext_lvl,
                        "date": dt_str,
                        "dist_units": dist_u,
                        "unit_label": "pips" if a_type in ("forex", "metal") else "pts",
                        "macro_aligned": (macro_dir == "SUBE"),
                    })

    pivots.sort(key=lambda x: x["dist_units"])
    return pivots[:2]


def detect_reversal_and_structure(c_1h, dec):
    if len(c_1h) < 18:
        swing_h = round(max((x["h"] for x in c_1h), default=0), dec)
        swing_l = round(min((x["l"] for x in c_1h), default=0), dec)
        return {
            "choch": "NONE",
            "sweep": "NONE",
            "bos": "NONE",
            "reversal_dir": "NONE",
            "strong_pullback": False,
            "bsl": swing_h,
            "ssl": swing_l,
        }

    recent = c_1h[-24:]
    prior = recent[:-4]
    last4 = recent[-4:]
    swing_h = round(max(x["h"] for x in prior), dec)
    swing_l = round(min(x["l"] for x in prior), dec)
    last_c = last4[-1]["c"]

    bull_sweep = any(x["l"] < swing_l and x["c"] > swing_l for x in last4)
    bear_sweep = any(x["h"] > swing_h and x["c"] < swing_h for x in last4)
    bull_bos = last_c > swing_h
    bear_bos = last_c < swing_l

    choch = "NONE"
    rev_dir = "NONE"
    if bull_sweep or bull_bos:
        choch = "ALCISTA"
        rev_dir = "SUBE"
    elif bear_sweep or bear_bos:
        choch = "BAJISTA"
        rev_dir = "BAJA"

    bodies = [abs(x["c"] - x["o"]) for x in last4]
    avg_prior = sum(abs(x["c"] - x["o"]) for x in prior[-10:]) / max(1, len(prior[-10:]))
    strong_pullback = (choch != "NONE") and (max(bodies) >= avg_prior * 1.35)

    return {
        "choch": choch,
        "sweep": "SSL BARRIDA" if bull_sweep else ("BSL BARRIDA" if bear_sweep else "NONE"),
        "bos": "BOS ALCISTA" if bull_bos else ("BOS BAJISTA" if bear_bos else "NONE"),
        "reversal_dir": rev_dir,
        "strong_pullback": strong_pullback,
        "bsl": swing_h,
        "ssl": swing_l,
    }


def detect_cascade_zone(c_1h, direction, price, pip, dec, a_type):
    """
    Escáner institucional en cascada de 3 niveles:
    1) OB + FVG (máxima confluencia)
    2) OB Estructural limpio
    3) FVG aislado de retroceso
    """
    if not c_1h or len(c_1h) < 12:
        return None

    spread_buf = pip * (18.0 if a_type == "metal" else (8.0 if a_type == "forex" else 15.0))
    bars = c_1h[-32:]
    n = len(bars)

    ob_fvg_candidates = []
    ob_only_candidates = []
    fvg_only_candidates = []

    for i in range(2, n - 2):
        c0 = bars[i - 1]
        c1 = bars[i]
        c2 = bars[i + 1]
        c3 = bars[i + 2]

        body1 = abs(c1["c"] - c1["o"])
        body2 = abs(c2["c"] - c2["o"])
        if body2 <= 0:
            continue

        if direction == "BUY":
            # FVG alcista: hueco entre máximo de c1 y mínimo de c3
            has_fvg = (c3["l"] > c1["h"]) and ((c3["l"] - c1["h"]) >= pip * 2.0)
            # OB alcista: última vela bajista (c1) antes de impulso alcista fuerte (c2)
            is_ob = (c1["c"] < c1["o"]) and (c2["c"] > c2["o"]) and (body2 > body1 * 1.15) and (c2["c"] > c1["h"])

            if is_ob:
                z_top = round(max(c1["o"], c1["c"]), dec)
                z_bot = round(c1["l"], dec)
                entry_p = round((z_top + z_bot) / 2.0, dec) if has_fvg else z_top
                sl_p = round(z_bot - spread_buf, dec)
                if price >= sl_p and entry_p > sl_p:
                    item = {
                        "zone_kind": "OB_FVG" if has_fvg else "OB",
                        "top": z_top,
                        "bottom": z_bot,
                        "entry": entry_p,
                        "sl": sl_p,
                        "idx": i,
                    }
                    if has_fvg:
                        ob_fvg_candidates.append(item)
                    else:
                        ob_only_candidates.append(item)
            elif has_fvg:
                z_top = round(c3["l"], dec)
                z_bot = round(c1["h"], dec)
                entry_p = round((z_top + z_bot) / 2.0, dec)
                sl_p = round(min(c1["l"], c2["l"]) - spread_buf, dec)
                if price >= sl_p and entry_p > sl_p:
                    fvg_only_candidates.append({
                        "zone_kind": "FVG",
                        "top": z_top,
                        "bottom": z_bot,
                        "entry": entry_p,
                        "sl": sl_p,
                        "idx": i,
                    })

        else:  # SELL
            has_fvg = (c1["l"] > c3["h"]) and ((c1["l"] - c3["h"]) >= pip * 2.0)
            is_ob = (c1["c"] > c1["o"]) and (c2["c"] < c2["o"]) and (body2 > body1 * 1.15) and (c2["c"] < c1["l"])

            if is_ob:
                z_top = round(c1["h"], dec)
                z_bot = round(min(c1["o"], c1["c"]), dec)
                entry_p = round((z_top + z_bot) / 2.0, dec) if has_fvg else z_bot
                sl_p = round(z_top + spread_buf, dec)
                if price <= sl_p and entry_p < sl_p:
                    item = {
                        "zone_kind": "OB_FVG" if has_fvg else "OB",
                        "top": z_top,
                        "bottom": z_bot,
                        "entry": entry_p,
                        "sl": sl_p,
                        "idx": i,
                    }
                    if has_fvg:
                        ob_fvg_candidates.append(item)
                    else:
                        ob_only_candidates.append(item)
            elif has_fvg:
                z_top = round(c1["l"], dec)
                z_bot = round(c3["h"], dec)
                entry_p = round((z_top + z_bot) / 2.0, dec)
                sl_p = round(max(c1["h"], c2["h"]) + spread_buf, dec)
                if price <= sl_p and entry_p < sl_p:
                    fvg_only_candidates.append({
                        "zone_kind": "FVG",
                        "top": z_top,
                        "bottom": z_bot,
                        "entry": entry_p,
                        "sl": sl_p,
                        "idx": i,
                    })

    if ob_fvg_candidates:
        return ob_fvg_candidates[-1]
    if ob_only_candidates:
        return ob_only_candidates[-1]
    if fvg_only_candidates:
        return fvg_only_candidates[-1]
    return None


def detect_exhaustion(c_1h, direction, r20_pos):
    if not c_1h or len(c_1h) < 4:
        return {"active": False, "reason": ""}
    last3 = c_1h[-3:]
    bodies = [abs(x["c"] - x["o"]) for x in last3]
    shrinking = bodies[2] < bodies[1] < bodies[0]
    if direction == "BUY" and (r20_pos >= 82 or shrinking):
        return {"active": True, "reason": f"Precio en techo del rango ({r20_pos}%) o velas perdiendo cuerpo."}
    if direction == "SELL" and (r20_pos <= 18 or shrinking):
        return {"active": True, "reason": f"Precio en suelo del rango ({r20_pos}%) o velas perdiendo cuerpo."}
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
                    "title": title,
                })
            elif imp.lower() == "medium" and len(events_today) < 10:
                events_today.append({
                    "date": today_iso,
                    "time": ev_time or "Hoy",
                    "currency": ccy,
                    "impact": "MEDIO",
                    "title": title,
                })
    except Exception as e:
        print(f"Aviso calendario economico: {e}")

    if not events_today:
        events_today = [
            {"date": today_iso, "time": "07:00 UTC", "currency": "EUR/GBP", "impact": "ALTO", "title": "Apertura Killzone Londres - Barrido de Liquidez Asiatica"},
            {"date": today_iso, "time": "12:30 UTC", "currency": "USD", "impact": "ALTO", "title": "Apertura Killzone Nueva York - Flujo Institucional"},
            {"date": today_iso, "time": "23:50 UTC", "currency": "AUD/JPY", "impact": "MEDIO", "title": "Apertura Sesion Tokio y Sidney - Flujo Asia-Pacifico"},
        ]

    return events_today[:12], high_impact_by_ccy


def compute_currency_strength_matrix(c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, spx_4h, spx_1d):
    def blend_chg(c4, c1d):
        return (pct_change_lookback(c4, 6) * 0.60) + (pct_change_lookback(c1d, 5) * 0.40)

    dxy_chg = blend_chg(dxy_4h, dxy_1d)
    us10y_chg = blend_chg(us10y_4h, us10y_1d)
    spx_chg = blend_chg(spx_4h, spx_1d)

    usd_score = (dxy_chg * 1.4) + (us10y_chg * 0.35)
    gbp_score = (
        blend_chg(c4_map.get("GBPUSD"), c1d_map.get("GBPUSD"))
        + blend_chg(c4_map.get("GBPJPY"), c1d_map.get("GBPJPY"))
        + blend_chg(c4_map.get("GBPAUD"), c1d_map.get("GBPAUD"))
    ) / 3.0
    aud_score = (
        (
            blend_chg(c4_map.get("AUDUSD"), c1d_map.get("AUDUSD"))
            + blend_chg(c4_map.get("AUDJPY"), c1d_map.get("AUDJPY"))
            + blend_chg(c4_map.get("AUDNZD"), c1d_map.get("AUDNZD"))
        )
        / 3.0
    ) + (spx_chg * 0.25)
    eur_score = (
        blend_chg(c4_map.get("EURUSD"), c1d_map.get("EURUSD"))
        + blend_chg(c4_map.get("EURJPY"), c1d_map.get("EURJPY"))
        + blend_chg(c4_map.get("EURAUD"), c1d_map.get("EURAUD"))
    ) / 3.0
    jpy_score = -(
        (
            blend_chg(c4_map.get("USDJPY"), c1d_map.get("USDJPY"))
            + blend_chg(c4_map.get("GBPJPY"), c1d_map.get("GBPJPY"))
            + blend_chg(c4_map.get("EURJPY"), c1d_map.get("EURJPY"))
            + blend_chg(c4_map.get("AUDJPY"), c1d_map.get("AUDJPY"))
        )
        / 4.0
    )
    nzd_score = (
        blend_chg(c4_map.get("NZDUSD"), c1d_map.get("NZDUSD"))
        - blend_chg(c4_map.get("AUDNZD"), c1d_map.get("AUDNZD"))
    ) / 2.0
    cad_score = (
        -blend_chg(c4_map.get("USDCAD"), c1d_map.get("USDCAD"))
        - blend_chg(c4_map.get("AUDCAD"), c1d_map.get("AUDCAD"))
    ) / 2.0
    chf_score = (
        -blend_chg(c4_map.get("USDCHF"), c1d_map.get("USDCHF"))
        - blend_chg(c4_map.get("AUDCHF"), c1d_map.get("AUDCHF"))
    ) / 2.0
    xau_score = -usd_score * 0.9

    raw = {
        "USD": round(usd_score, 3),
        "GBP": round(gbp_score, 3),
        "AUD": round(aud_score, 3),
        "EUR": round(eur_score, 3),
        "JPY": round(jpy_score, 3),
        "NZD": round(nzd_score, 3),
        "CAD": round(cad_score, 3),
        "CHF": round(chf_score, 3),
        "XAU": round(xau_score, 3),
        "BTC": round(spx_chg * 0.8 - usd_score * 0.5, 3),
    }
    labels = {k: ("FUERTE" if v > 0.14 else ("DEBIL" if v < -0.14 else "NEUTRAL")) for k, v in raw.items()}
    return raw, labels, round(spx_chg, 2)


def get_central_banks(dxy_val, us10y_val, ccy_labels):
    return [
        {
            "bank": "FED (EE.UU.)",
            "currency": "USD",
            "stance": f"USD {ccy_labels.get('USD', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("USD") == "FUERTE" else ("BEARISH" if ccy_labels.get("USD") == "DEBIL" else "NEUTRAL"),
            "detail": f"DXY ({dxy_val}) + Bonos US10Y ({us10y_val}%) en cesta hibrida 4H/1D.",
        },
        {
            "bank": "BCE (Eurozona)",
            "currency": "EUR",
            "stance": f"EUR {ccy_labels.get('EUR', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("EUR") == "FUERTE" else ("BEARISH" if ccy_labels.get("EUR") == "DEBIL" else "NEUTRAL"),
            "detail": "Flujo en EURUSD + EURJPY + EURAUD (60% 4H + 40% 1D).",
        },
        {
            "bank": "BoE (Reino Unido)",
            "currency": "GBP",
            "stance": f"GBP {ccy_labels.get('GBP', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("GBP") == "FUERTE" else ("BEARISH" if ccy_labels.get("GBP") == "DEBIL" else "NEUTRAL"),
            "detail": "Flujo en GBPUSD + GBPJPY + GBPAUD (60% 4H + 40% 1D).",
        },
        {
            "bank": "BoJ (Japon)",
            "currency": "JPY",
            "stance": f"JPY {ccy_labels.get('JPY', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("JPY") == "FUERTE" else ("BEARISH" if ccy_labels.get("JPY") == "DEBIL" else "NEUTRAL"),
            "detail": "Sensible al diferencial de bonos US10Y y cruces JPY.",
        },
        {
            "bank": "RBA (Australia)",
            "currency": "AUD",
            "stance": f"AUD {ccy_labels.get('AUD', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("AUD") == "FUERTE" else ("BEARISH" if ccy_labels.get("AUD") == "DEBIL" else "NEUTRAL"),
            "detail": "Correlacionado con apetito de riesgo (US500) y cesta AUD.",
        },
        {
            "bank": "RBNZ (Nueva Zelanda)",
            "currency": "NZD",
            "stance": f"NZD {ccy_labels.get('NZD', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("NZD") == "FUERTE" else ("BEARISH" if ccy_labels.get("NZD") == "DEBIL" else "NEUTRAL"),
            "detail": "Cesta NZDUSD y diferencial frente a AUDNZD.",
        },
        {
            "bank": "BoC (Canada)",
            "currency": "CAD",
            "stance": f"CAD {ccy_labels.get('CAD', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("CAD") == "FUERTE" else ("BEARISH" if ccy_labels.get("CAD") == "DEBIL" else "NEUTRAL"),
            "detail": "Flujo frente a USD (USDCAD) y cruces de materias primas.",
        },
        {
            "bank": "SNB (Suiza)",
            "currency": "CHF",
            "stance": f"CHF {ccy_labels.get('CHF', 'NEUTRAL')}",
            "bias": "BULLISH" if ccy_labels.get("CHF") == "FUERTE" else ("BEARISH" if ccy_labels.get("CHF") == "DEBIL" else "NEUTRAL"),
            "detail": "Divisa refugio medida contra USDCHF y AUDCHF.",
        },
    ]


def explain_news_for_trader(title, category):
    t = title.lower()
    if any(k in t for k in ["fed", "powell", "fomc", "rate", "yield", "treasury", "cpi", "ppi", "inflation", "nfp", "payroll"]):
        return (
            "USD · US10Y · XAUUSD · USTEC",
            "Impacta directamente las expectativas de tasas de interes en EE.UU. Si suben los rendimientos (US10Y), el Dolar se fortalece y presiona a la baja al Oro y Nasdaq.",
        )
    if any(k in t for k in ["gold", "bullion", "silver", "metal", "oil", "crude"]):
        return (
            "XAUUSD · USDCAD · AUDUSD",
            "Movimiento en materias primas y activos refugio. Afecta de forma directa la liquidez del Oro (XAUUSD) y divisas ligadas a commodities como CAD y AUD.",
        )
    if any(k in t for k in ["yen", "boj", "ueda", "japan", "intervention"]):
        return (
            "USDJPY · GBPJPY · EURJPY · AUDJPY",
            "Catalizador directo sobre el Yen japones. Aumenta la volatilidad en todos los cruces JPY; vigila posibles barridos de liquidez en sesion asiatica.",
        )
    if any(k in t for k in ["ecb", "lagarde", "euro", "germany", "eurozone"]):
        return (
            "EURUSD · EURJPY · EURAUD",
            "Define la fuerza institucional del Euro frente al Dolar y al Yen. Util para confirmar continuacion o giro en sesiones de Londres.",
        )
    if any(k in t for k in ["boe", "bailey", "pound", "sterling", "uk", "britain"]):
        return (
            "GBPUSD · GBPJPY · GBPAUD · GBPCAD",
            "Genera flujo institucional en la Libra Esterlina durante la Killzone de Londres.",
        )
    if any(k in t for k in ["nasdaq", "s&p", "dow", "nvidia", "tech", "wall st", "stocks", "equities"]):
        return (
            "USTEC · US500 · US30 · AUDJPY",
            "Marca el sentimiento de apetito o aversion al riesgo en Wall Street. Si suben los indices, suelen acompañarlo al alza AUD y NZD.",
        )
    if any(k in t for k in ["bitcoin", "crypto", "btc", "sec", "etf"]):
        return (
            "BTCUSD · USTEC",
            "Afecta la liquidez del mercado cripto y suele correlacionarse con el impulso tecnologico del Nasdaq.",
        )
    return (
        "MERCADO GENERAL",
        f"Titular relevante del bloque {category} que puede generar picos de volatilidad puntual en apertura de sesion.",
    )


def fetch_live_news():
    feeds = [
        ("WALL STREET & TASAS", "https://finance.yahoo.com/news/rssindex"),
        ("FOREX & BANCOS", "https://www.investing.com/rss/news_1.rss"),
        ("ORO & MACRO", "https://www.investing.com/rss/news_14.rss"),
    ]
    news_items = []
    seen = set()
    for category, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:6]:
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    if title in seen:
                        continue
                    seen.add(title)
                    pairs_affected, plain_es = explain_news_for_trader(title, category)
                    news_items.append({
                        "category": category,
                        "source": category,
                        "title": title,
                        "pairs": pairs_affected,
                        "plain_es": plain_es,
                        "link": link_el.text.strip() if (link_el is not None and link_el.text) else "#",
                        "time": (pub_el.text.strip()[:22] if (pub_el is not None and pub_el.text) else "Hoy"),
                    })
        except Exception:
            pass

    if not news_items:
        news_items = [
            {
                "category": "WALL STREET & TASAS",
                "source": "Radar Institucional",
                "title": "Flujos de liquidez activos en sesiones de Londres y Nueva York.",
                "pairs": "EURUSD · GBPUSD · XAUUSD · USTEC",
                "plain_es": "Sin noticias extraordinarias fuera de calendario; operar respetando zonas limpias de OB + FVG.",
                "link": "#",
                "time": "En linea",
            }
        ]
    return news_items[:18]


def build_asset(cfg, candles_bundle, raw_strength, ccy_labels, high_impact_by_ccy, now_ts, active_setups):
    try:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        pip = cfg["pip"]
        a_type = cfg["type"]
        base_ccy = cfg["base"]
        quote_ccy = cfg["quote"]

        c_1d = candles_bundle.get("1d", [])
        c_4h = candles_bundle.get("4h", [])
        c_1h = candles_bundle.get("1h", [])
        c_1w_all = candles_bundle.get("1w_all", [])
        c_1w = c_1w_all[-45:] if c_1w_all else []

        if not c_1h or len(c_1h) < 10:
            return None

        price = c_1h[-1]["c"]
        prev_close = c_1d[-2]["c"] if len(c_1d) >= 2 else c_1h[0]["o"]
        change_pct = round(((price - prev_close) / max(1e-9, prev_close)) * 100.0, 2)

        b_w = calc_bias(c_1w, 6, 0.0012)
        b_d = calc_bias(c_1d, 6, 0.0008)
        b_4h = calc_bias(c_4h, 6, 0.0006)
        b_1h = calc_bias(c_1h, 6, 0.0004)

        # Dirección macro según cesta de divisas o riesgo
        if a_type == "forex":
            diff = raw_strength.get(base_ccy, 0.0) - raw_strength.get(quote_ccy, 0.0)
            macro_dir = "SUBE" if diff > 0.12 else ("BAJA" if diff < -0.12 else "NEUTRAL")
        elif sym == "XAUUSD":
            s_xau = raw_strength.get("XAU", 0.0)
            macro_dir = "SUBE" if s_xau > 0.12 else ("BAJA" if s_xau < -0.12 else "NEUTRAL")
        elif sym == "BTCUSD":
            s_btc = raw_strength.get("BTC", 0.0)
            macro_dir = "SUBE" if s_btc > 0.12 else ("BAJA" if s_btc < -0.12 else "NEUTRAL")
        else:
            s_idx = raw_strength.get("BTC", 0.0)
            macro_dir = "SUBE" if s_idx > 0.10 else ("BAJA" if s_idx < -0.10 else "NEUTRAL")

        struct = detect_reversal_and_structure(c_1h, dec)
        atr_14 = calc_atr_14(c_1d, dec)
        r20 = calc_range_20d(c_1d, price, dec)

        # Sesgo técnico del gráfico
        votes_up = sum(1 for v in (b_d, b_4h, b_1h) if v == "SUBE")
        votes_dn = sum(1 for v in (b_d, b_4h, b_1h) if v == "BAJA")
        if votes_up >= 2:
            chart_bias = "SUBE"
        elif votes_dn >= 2:
            chart_bias = "BAJA"
        elif struct["reversal_dir"] in ("SUBE", "BAJA"):
            chart_bias = struct["reversal_dir"]
        else:
            chart_bias = b_4h if b_4h != "NEUTRAL" else b_1h

        direction = "BUY" if chart_bias == "SUBE" else "SELL"
        is_counter_daily = (b_d in ("SUBE", "BAJA")) and (b_d != chart_bias)

        # Escáner en cascada de 3 niveles (OB+FVG -> OB -> FVG)
        zone = detect_cascade_zone(c_1h, direction, price, pip, dec, a_type)
        has_valid_ob = zone is not None

        if zone:
            entry = zone["entry"]
            sl = zone["sl"]
            zone_kind = zone["zone_kind"]
            zone_top = zone["top"]
            zone_bot = zone["bottom"]
        else:
            # Referencia estructural de respaldo si aún no hay bloque limpio
            entry = round(price, dec)
            sl_dist = max(pip * 15, atr_14 * 0.45 if atr_14 else pip * 25)
            sl = round(entry - sl_dist, dec) if direction == "BUY" else round(entry + sl_dist, dec)
            zone_kind = "NONE"
            zone_top = entry
            zone_bot = entry

        risk_dist = max(pip, abs(entry - sl))
        if direction == "BUY":
            be_trigger = round(entry + risk_dist * 1.0, dec)
            tp1 = round(entry + risk_dist * 2.0, dec)
            tp2 = round(entry + risk_dist * 3.0, dec)
            swing_tp = round(entry + risk_dist * 4.2, dec)
        else:
            be_trigger = round(entry - risk_dist * 1.0, dec)
            tp1 = round(entry - risk_dist * 2.0, dec)
            tp2 = round(entry - risk_dist * 3.0, dec)
            swing_tp = round(entry - risk_dist * 4.2, dec)

        # Confluencia Economía vs Gráfico
        if macro_dir == "NEUTRAL" or chart_bias == "NEUTRAL":
            alignment = "NEUTRAL"
        elif macro_dir == chart_bias:
            alignment = "ALIGNED"
        else:
            alignment = "BROKEN"

        # Cálculo de puntaje de confluencia (0 - 100)
        score = 50
        if alignment == "ALIGNED":
            score += 22
        elif alignment == "BROKEN":
            score -= 18
        if zone_kind == "OB_FVG":
            score += 16
        elif zone_kind == "OB":
            score += 11
        elif zone_kind == "FVG":
            score += 7
        if b_d == chart_bias:
            score += 6
        if b_4h == chart_bias:
            score += 5
        if b_1h == chart_bias:
            score += 4
        if struct["choch"] != "NONE":
            score += 4
        conf_score = max(15, min(98, score))

        exhaustion = detect_exhaustion(c_1h, direction, r20["pos_pct"])

        # Filtro estricto de 8 candados para POTENCIAL SWING
        dist_ratio = abs(price - entry) / max(1e-9, price)
        max_swing_dist = 0.025 if a_type == "crypto" else 0.012
        ccy_swing_ok = True
        if a_type == "forex":
            if direction == "BUY" and ccy_labels.get(base_ccy) == "DEBIL":
                ccy_swing_ok = False
            elif direction == "SELL" and ccy_labels.get(base_ccy) == "FUERTE":
                ccy_swing_ok = False

        is_swing_potential = (
            has_valid_ob
            and not is_counter_daily
            and not exhaustion["active"]
            and ccy_swing_ok
            and b_d == chart_bias
            and b_4h == chart_bias
            and b_1h == chart_bias
            and macro_dir == chart_bias
            and conf_score >= 84
            and dist_ratio <= max_swing_dist
        )

        # Noticias de alto impacto hoy para este activo
        ccys_to_check = [base_ccy, quote_ccy] if a_type == "forex" else ["USD"]
        news_list = []
        for c in ccys_to_check:
            news_list.extend(high_impact_by_ccy.get(c, []))
        has_news = len(news_list) > 0

        weekly_pivots = detect_weekly_clean_pivots(c_1w_all, price, pip, dec, a_type, sym, macro_dir)

        dir_es = "COMPRA" if direction == "BUY" else "VENTA"
        z_es = "OB + FVG" if zone_kind == "OB_FVG" else ("OB Estructural" if zone_kind == "OB" else ("FVG Retroceso" if zone_kind == "FVG" else "Sin bloque limpio"))

        return {
            "symbol": sym,
            "type": a_type,
            "base": base_ccy,
            "quote": quote_ccy,
            "pip": pip,
            "decimals": dec,
            "price": price,
            "change_pct": change_pct,
            "has_valid_ob": has_valid_ob,
            "zone_kind": zone_kind,
            "is_counter_daily": is_counter_daily,
            "is_strong_pullback": bool(is_counter_daily and struct["strong_pullback"]),
            "has_news_today": has_news,
            "news_today": news_list[:3],
            "timeframes": {
                "1w": b_w,
                "1d": b_d,
                "4h": b_4h,
                "1h": b_1h,
                "macro": macro_dir,
            },
            "metrics": {
                "atr_14": atr_14,
                "range_20d": r20,
            },
            "structure": struct,
            "confluence": {
                "alignment": alignment,
                "score": conf_score,
                "macro_dir": macro_dir,
                "chart_bias": chart_bias,
            },
            "exhaustion": exhaustion,
            "swing_potential": {
                "active": is_swing_potential,
                "target": swing_tp,
                "note": "Protocolo Piramide activo: asegurar BE (+1R) antes de añadir retroceso." if is_swing_potential else "",
            },
            "setup": {
                "direction": direction,
                "dir_label": dir_es,
                "signal_tag": f"{dir_es} · {z_es}",
                "entry": entry,
                "zone_top": zone_top,
                "zone_bottom": zone_bot,
                "sl": sl,
                "be_trigger": be_trigger,
                "tp1": tp1,
                "tp2": tp2,
                "simple_reason": f"{z_es} en 1H con estructura 1D {b_d} / 4H {b_4h} y flujo macro {macro_dir}.",
                "risk_note": f"Noticia fuerte hoy: {', '.join(news_list)}" if has_news else "Respetar Stop estructural y proteger en +1R.",
            },
            "weekly_pivots": weekly_pivots,
            "candles": {
                "1d": c_1d[-35:],
                "4h": c_4h[-35:],
                "1h": c_1h[-35:],
            },
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
            if not a.get("has_valid_ob") or a["confluence"]["alignment"] != "ALIGNED":
                continue
            d = a["setup"]["direction"]
            if st == "FUERTE":
                if (a["base"] == ccy and d == "BUY") or (a["quote"] == ccy and d == "SELL"):
                    matched_pairs.append(f"{a['symbol']} ({'COMPRA' if d == 'BUY' else 'VENTA'})")
            elif st == "DEBIL":
                if (a["base"] == ccy and d == "SELL") or (a["quote"] == ccy and d == "BUY"):
                    matched_pairs.append(f"{a['symbol']} ({'COMPRA' if d == 'BUY' else 'VENTA'})")
        if len(matched_pairs) >= 2:
            baskets.append({
                "currency": ccy,
                "status": st,
                "pairs": matched_pairs[:5],
            })
    return baskets


def compute_best_focus_pick(assets, baskets):
    basket_ccys = {b["currency"] for b in baskets}
    candidates = []
    for a in assets:
        if not a.get("has_valid_ob"):
            continue
        prob = a["confluence"]["score"]
        if a["confluence"]["alignment"] == "ALIGNED":
            prob += 10
        if a["zone_kind"] == "OB_FVG":
            prob += 8
        if a["swing_potential"]["active"]:
            prob += 8
        if a["base"] in basket_ccys or a["quote"] in basket_ccys:
            prob += 4
        if a["has_news_today"]:
            prob -= 25
        if a["is_counter_daily"]:
            prob -= 10
        prob = max(20, min(95, prob))

        dist_u = round(abs(a["price"] - a["setup"]["entry"]) / max(1e-9, a["pip"]), 1)
        u_lbl = "pips" if a["type"] in ("forex", "metal") else "pts"
        candidates.append((
            prob,
            -dist_u,
            {
                "symbol": a["symbol"],
                "base": a["base"],
                "quote": a["quote"],
                "probability": prob,
                "direction": a["setup"]["direction"],
                "dir_label": a["setup"]["dir_label"],
                "zone_kind": a["zone_kind"],
                "signal_tag": f"{a['setup']['dir_label']} {a['zone_kind'].replace('_', ' + ')}",
                "price": a["price"],
                "entry": a["setup"]["entry"],
                "sl": a["setup"]["sl"],
                "be_trigger": a["setup"]["be_trigger"],
                "tp1": a["setup"]["tp1"],
                "tp2": a["setup"]["tp2"],
                "dist_units": dist_u,
                "unit_label": u_lbl,
                "swing_potential": a["swing_potential"]["active"],
                "reason": a["setup"]["simple_reason"],
            },
        ))

    if not candidates:
        return {"primary": None, "secondary": None}

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    primary = candidates[0][2]
    secondary = None
    for _, _, cand in candidates[1:]:
        if cand["base"] not in (primary["base"], primary["quote"]) and cand["quote"] not in (primary["base"], primary["quote"]):
            secondary = cand
            break
    return {"primary": primary, "secondary": secondary}


def dispatch_push_notifications(assets, now_ts):
    if not NTFY_TOPIC:
        return
    sent_state = load_json_state(ALERTS_STATE_FILE)
    updated = False

    for a in assets:
        sym = a["symbol"]
        a_type = a.get("type", "forex")
        direction = a["setup"]["direction"]
        d_txt = "COMPRA" if direction == "BUY" else "VENTA"
        is_aligned = (a.get("confluence", {}).get("alignment") == "ALIGNED")
        has_valid_ob = bool(a.get("has_valid_ob"))
        z_kind = a.get("zone_kind", "OB")

        price = a["price"]
        entry = a["setup"]["entry"]
        sl = a["setup"]["sl"]
        tp1 = a["setup"]["tp1"]
        pip = a.get("pip", 0.0001)

        units = round((abs(price - entry) / pip) * 10) / 10 if pip else abs(price - entry)
        pct_dist = abs(price - entry) / max(1e-9, price)
        right_side = (price > sl and price < tp1) if direction == "BUY" else (price < sl and price > tp1)

        if sym == "XAUUSD" or a_type == "metal":
            in_trigger_zone = (units <= 40.0)
            u_lbl = "pips"
        elif a_type == "forex":
            in_trigger_zone = (units <= 25.0)
            u_lbl = "pips"
        else:
            in_trigger_zone = (pct_dist <= 0.0015)
            u_lbl = "pts"

        if has_valid_ob and is_aligned and right_side and in_trigger_zone:
            entry_key = f"ALARM_{sym}_{direction}_{entry}"
            if entry_key not in sent_state:
                be_p = a["setup"].get("be_trigger", entry)
                is_swing = bool(a.get("swing_potential") and a["swing_potential"].get("active"))
                swing_line = f" | Swing TP: {a['swing_potential']['target']}" if is_swing else ""
                kind_tag = "OB + FVG" if z_kind == "OB_FVG" else ("FVG" if z_kind == "FVG" else "OB ESTRUCTURAL")
                body = (
                    f"{sym} ({d_txt}) a {units} {u_lbl} de {kind_tag} ({entry}).\n"
                    f"Precio: {price} | SL: {sl} | BE (+1R): {be_p} | TP1: {tp1}{swing_line}"
                )
                send_mobile_push(f"LATICCE {kind_tag}: {sym} ({d_txt}) a {units} {u_lbl}", body, "high", "dart,bell")
                sent_state[entry_key] = now_ts
                updated = True

        for wp in a.get("weekly_pivots", []):
            w_units = wp["dist_units"]
            w_in_zone = (w_units <= 40.0) if (sym == "XAUUSD" or a_type == "metal") else ((w_units <= 25.0) if a_type == "forex" else (abs(price - wp["entry"]) / max(1e-9, price) <= 0.0015))
            if w_in_zone:
                w_key = f"WEEKLY1S_{sym}_{wp['direction']}_{wp['entry']}_{wp['date']}"
                if w_key not in sent_state:
                    w_dir_txt = "COMPRA" if wp["direction"] == "BUY" else "VENTA"
                    w_body = (
                        f"Giro semanal limpio ({wp['date']}) en {sym} ({w_dir_txt}).\n"
                        f"Entrada 1S: {wp['entry']} (Extremo: {wp['extreme']}) | Actual: {price} ({w_units} {wp['unit_label']})."
                    )
                    send_mobile_push(f"LATICCE GIRO 1S ({wp['date']}): {sym} ({w_dir_txt})", w_body, "high", "dart,bell")
                    sent_state[w_key] = now_ts
                    updated = True

    if updated:
        if len(sent_state) > 180:
            sorted_items = sorted(sent_state.items(), key=lambda x: x[1])[-180:]
            sent_state = dict(sorted_items)
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
    dxy_prev = dxy_1d[-2]["c"] if len(dxy_1d) >= 2 else dxy_val
    us10y_prev = us10y_1d[-2]["c"] if len(us10y_1d) >= 2 else us10y_val
    dxy_chg_pct = round(((dxy_val - dxy_prev) / max(1e-9, dxy_prev)) * 100.0, 2)
    us10y_chg_pct = round(((us10y_val - us10y_prev) / max(1e-9, us10y_prev)) * 100.0, 2)

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

    raw_strength, ccy_labels, spx_chg = compute_currency_strength_matrix(
        c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, c4_map.get("US500", []), c1d_map.get("US500", [])
    )

    active_setups = load_json_state(SETUPS_STATE_FILE)
    assets = [
        item
        for cfg in ASSETS_CONFIG
        if (item := build_asset(cfg, bundles.get(cfg["symbol"], {}), raw_strength, ccy_labels, high_impact_by_ccy, now_ts, active_setups))
    ]
    save_json_state(SETUPS_STATE_FILE, active_setups)

    banks = get_central_banks(dxy_val, us10y_val, ccy_labels)
    baskets = build_correlated_baskets(assets, ccy_labels)
    focus_pick = compute_best_focus_pick(assets, baskets)
    news = fetch_live_news()

    # Resumen de Wall Street para el Brief Diario de VISIÓN
    idx_map = {a["symbol"]: a for a in assets if a["symbol"] in ("US500", "USTEC", "US30")}
    wall_street = []
    for sym_i, name_i in [("US500", "S&P 500"), ("USTEC", "Nasdaq 100"), ("US30", "Dow Jones 30")]:
        it = idx_map.get(sym_i)
        if it:
            wall_street.append({
                "symbol": sym_i,
                "name": name_i,
                "price": it["price"],
                "change_pct": it["change_pct"],
                "bias": it["confluence"]["chart_bias"],
            })

    all_weekly_pivots = []
    for a in assets:
        all_weekly_pivots.extend(a.get("weekly_pivots", []))
    all_weekly_pivots.sort(key=lambda x: x["dist_units"])

    dispatch_push_notifications(assets, now_ts)

    alert_ccys = sorted(high_impact_by_ccy.keys())
    news_alert_str = f" · Noticias fuertes hoy: {', '.join(alert_ccys)}" if alert_ccys else ""
    focus_str = f" | Foco #1: {focus_pick['primary']['symbol']} ({focus_pick['primary']['probability']}% prob)" if (focus_pick and focus_pick.get("primary")) else ""

    strong_list = [k for k, v in ccy_labels.items() if v == "FUERTE" and len(k) == 3]
    weak_list = [k for k, v in ccy_labels.items() if v == "DEBIL" and len(k) == 3]
    brief_narrative = (
        f"DXY en {dxy_val} ({dxy_chg_pct:+.2f}%) y Bonos US10Y en {us10y_val}% ({us10y_chg_pct:+.2f}%). "
        f"Divisas liderando fuerza: {', '.join(strong_list) if strong_list else 'Sin liderazgo extremo'}. "
        f"Divisas bajo presion: {', '.join(weak_list) if weak_list else 'Equilibrio general'}{news_alert_str}."
    )

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "dxy_chg": dxy_chg_pct,
            "us10y": us10y_val,
            "us10y_chg": us10y_chg_pct,
            "spx_chg": spx_chg,
            "headline": f"USD {ccy_labels.get('USD')} (DXY {dxy_val} · US10Y {us10y_val}%) | GBP {ccy_labels.get('GBP')} | AUD {ccy_labels.get('AUD')}",
            "summary": f"LATICCE v10.2 · Radar Foco Principal + VISIÓN 5 Módulos + Giros 1S ({len(all_weekly_pivots)} niveles){focus_str}.",
            "narrative": brief_narrative,
        },
        "currency_strength": {
            "raw": raw_strength,
            "labels": ccy_labels,
        },
        "wall_street": wall_street,
        "focus_pick": focus_pick,
        "weekly_pivots": all_weekly_pivots,
        "correlated_baskets": baskets,
        "banks": banks,
        "news": news,
        "calendar": calendar_events,
        "assets": assets,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(assets)} activos actualizados (LATICCE v10.2).")


if __name__ == "__main__":
    main()
