import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import yfinance as yf

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

def pct_change_4h(candles, lookback=6):
    if not candles or len(candles) < lookback:
        return 0.0
    first = candles[-lookback]["c"]
    last = candles[-1]["c"]
    return ((last - first) / first) * 100.0 if first else 0.0

def detect_reversal_and_structure(c_1h):
    """
    Detecta giros de cambio de tendencia reales:
    1. Barrido de liquidez (Sweep SSL / BSL) en extremos con mecha de rechazo.
    2. Cambio de Carácter (CHoCH) rompiendo el último swing estructural.
    """
    if len(c_1h) < 18:
        return {"choch": "NONE", "sweep": "NONE", "reversal_dir": "NONE"}

    window = c_1h[-20:-2]
    last_two = c_1h[-2:]
    curr = last_two[-1]
    swing_high = max(x["h"] for x in window)
    swing_low = min(x["l"] for x in window)

    choch = "NONE"
    if curr["c"] > swing_high:
        choch = "BULLISH_CHOCH"
    elif curr["c"] < swing_low:
        choch = "BEARISH_CHOCH"

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

    return {"choch": choch, "sweep": sweep, "reversal_dir": reversal_dir}

def fetch_high_impact_calendar(now_utc):
    """
    Descarga el calendario económico real de la semana (ForexFactory) y filtra
    las noticias de ALTO IMPACTO (High) del día de hoy por divisa.
    """
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

    # Respaldo de calendario si el feed externo no responde
    if not events_today:
        events_today = [
            {"date": today_iso, "time": "07:00 UTC", "currency": "EUR/GBP", "impact": "ALTO", "title": "Apertura Killzone Londres · Barrido de Liquidez Asiática"},
            {"date": today_iso, "time": "12:30 UTC", "currency": "USD", "impact": "ALTO", "title": "Apertura Killzone Nueva York · Flujo Institucional"},
            {"date": today_iso, "time": "23:50 UTC", "currency": "AUD/JPY", "impact": "MEDIO", "title": "Apertura Sesión Tokio & Sídney · Flujo Asia-Pacífico"}
        ]

    return events_today[:10], high_impact_by_ccy

def compute_currency_strength_matrix(c4_map, dxy_4h, us10y_4h, spx_4h):
    dxy_chg = pct_change_4h(dxy_4h, 6)
    us10y_chg = pct_change_4h(us10y_4h, 6)
    spx_chg = pct_change_4h(spx_4h, 6)

    usd_score = (dxy_chg * 1.4) + (us10y_chg * 0.35)
    gbp_score = (pct_change_4h(c4_map.get("GBPUSD"), 6) + pct_change_4h(c4_map.get("GBPJPY"), 6) + pct_change_4h(c4_map.get("GBPAUD"), 6)) / 3.0
    aud_score = ((pct_change_4h(c4_map.get("AUDUSD"), 6) + pct_change_4h(c4_map.get("AUDJPY"), 6) + pct_change_4h(c4_map.get("AUDNZD"), 6)) / 3.0) + (spx_chg * 0.25)
    eur_score = (pct_change_4h(c4_map.get("EURUSD"), 6) + pct_change_4h(c4_map.get("EURJPY"), 6) + pct_change_4h(c4_map.get("EURAUD"), 6)) / 3.0
    jpy_score = -((pct_change_4h(c4_map.get("USDJPY"), 6) + pct_change_4h(c4_map.get("GBPJPY"), 6) + pct_change_4h(c4_map.get("EURJPY"), 6) + pct_change_4h(c4_map.get("AUDJPY"), 6)) / 4.0)
    nzd_score = (pct_change_4h(c4_map.get("NZDUSD"), 6) - pct_change_4h(c4_map.get("AUDNZD"), 6)) / 2.0
    cad_score = (-pct_change_4h(c4_map.get("USDCAD"), 6) - pct_change_4h(c4_map.get("AUDCAD"), 6)) / 2.0
    chf_score = (-pct_change_4h(c4_map.get("USDCHF"), 6) - pct_change_4h(c4_map.get("AUDCHF"), 6)) / 2.0
    xau_score = -usd_score * 0.9

    raw = {
        "USD": usd_score, "GBP": gbp_score, "AUD": aud_score,
        "EUR": eur_score, "JPY": jpy_score, "NZD": nzd_score,
        "CAD": cad_score, "CHF": chf_score, "XAU": xau_score,
        "BTC": spx_chg * 0.8 - usd_score * 0.5,
    }
    labels = {k: ("FUERTE" if v > 0.12 else ("DÉBIL" if v < -0.12 else "NEUTRAL")) for k, v in raw.items()}
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
        {"bank": "FED (EE.UU.)", "currency": "USD", "stance": f"USD {ccy_labels.get('USD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("USD") == "FUERTE" else ("BEARISH" if ccy_labels.get("USD") == "DÉBIL" else "NEUTRAL"), "detail": f"DXY ({dxy_val}) + Bonos US10Y ({us10y_val}%) en 4H."},
        {"bank": "BoE (Reino Unido)", "currency": "GBP", "stance": f"GBP {ccy_labels.get('GBP', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("GBP") == "FUERTE" else ("BEARISH" if ccy_labels.get("GBP") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta ponderada GBPUSD + GBPJPY + GBPAUD en 4H."},
        {"bank": "RBA (Australia)", "currency": "AUD", "stance": f"AUD {ccy_labels.get('AUD', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("AUD") == "FUERTE" else ("BEARISH" if ccy_labels.get("AUD") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta AUDUSD + AUDJPY + AUDNZD + riesgo US500 en 4H."},
        {"bank": "BCE (Eurozona)", "currency": "EUR", "stance": f"EUR {ccy_labels.get('EUR', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("EUR") == "FUERTE" else ("BEARISH" if ccy_labels.get("EUR") == "DÉBIL" else "NEUTRAL"), "detail": "Cesta EURUSD + EURJPY + EURAUD en 4H."},
        {"bank": "BoJ (Japón)", "currency": "JPY", "stance": f"JPY {ccy_labels.get('JPY', 'NEUTRAL')}", "bias": "BULLISH" if ccy_labels.get("JPY") == "FUERTE" else ("BEARISH" if ccy_labels.get("JPY") == "DÉBIL" else "NEUTRAL"), "detail": "Flujo inverso en cruces JPY en 4H."}
    ]

def build_asset(cfg, candles_bundle, raw_strength, ccy_labels, high_impact_by_ccy):
    try:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        pip = cfg["pip"]

        c_1d = candles_bundle.get("1d", [])
        c_4h = candles_bundle.get("4h", [])
        c_1h = candles_bundle.get("1h", [])

        if not c_1h and c_1d:
            c_1h = c_1d[-30:]
        if not c_4h and c_1d:
            c_4h = c_1d[-30:]
        if not c_1h:
            return None

        price = c_1h[-1]["c"]
        prev_close = c_1d[-2]["c"] if len(c_1d) >= 2 else c_1h[0]["o"]
        chg_day = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0

        # 1. JERARQUÍA TÉCNICA CLÁSICA (1D=3, 4H=2, 1H=1)
        b_d = calc_bias(c_1d, 6, 0.0010)
        b_4h = calc_bias(c_4h, 6, 0.0008)
        b_1h = calc_bias(c_1h, 6, 0.0006)

        w_up = (3 if b_d == "SUBE" else 0) + (2 if b_4h == "SUBE" else 0) + (1 if b_1h == "SUBE" else 0)
        w_dn = (3 if b_d == "BAJA" else 0) + (2 if b_4h == "BAJA" else 0) + (1 if b_1h == "BAJA" else 0)

        # 2. FUERZA MACRO MULTIDIVISA EN 4H
        base_ccy = cfg["base"]
        quote_ccy = cfg["quote"]
        if cfg["type"] == "index":
            macro_diff = raw_strength.get("BTC", 0.0)
            macro_dir = "SUBE" if macro_diff > 0.10 else ("BAJA" if macro_diff < -0.10 else "NEUTRAL")
            macro_detail = f"Apetito al riesgo US500 y rendimiento USD ({ccy_labels.get('USD', 'NEUTRAL')})."
        else:
            b_str = raw_strength.get(base_ccy, 0.0)
            q_str = raw_strength.get(quote_ccy, 0.0)
            macro_diff = b_str - q_str
            macro_dir = "SUBE" if macro_diff > 0.12 else ("BAJA" if macro_diff < -0.12 else "NEUTRAL")
            macro_detail = f"{base_ccy} ({ccy_labels.get(base_ccy, 'NEUTRAL')}) vs {quote_ccy} ({ccy_labels.get(quote_ccy, 'NEUTRAL')}) en cesta 4H."

        # 3. GIROS DE CAMBIO DE TENDENCIA CON RESPALDO MACRO
        rev = detect_reversal_and_structure(c_1h)
        macro_backed_reversal = (rev["reversal_dir"] != "NONE" and rev["reversal_dir"] == macro_dir)

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

        # 4. BLOQUES CLÁSICOS ORIGINALES (SIN ORDER BLOCKS FRESCOS ARTIFICIALES)
        recent = c_1h[-24:]
        intraday_high = max(x["h"] for x in recent)
        intraday_low = min(x["l"] for x in recent)
        eq_50 = (intraday_high + intraday_low) / 2.0

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

            if macro_backed_reversal and rev["sweep"] == "SSL_SWEEP_BUY":
                signal_tag = "GIRO MACRO · BARRIDO SSL"
            elif macro_backed_reversal and rev["choch"] == "BULLISH_CHOCH":
                signal_tag = "GIRO MACRO · CHoCH ALCISTA"
            elif rev["choch"] == "BULLISH_CHOCH":
                signal_tag = "CHoCH ALCISTA · OB"
            else:
                signal_tag = "COMPRA OB" if price > eq_50 * 0.998 else "RE-ENTRADA OB"
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

            if macro_backed_reversal and rev["sweep"] == "BSL_SWEEP_SELL":
                signal_tag = "GIRO MACRO · BARRIDO BSL"
            elif macro_backed_reversal and rev["choch"] == "BEARISH_CHOCH":
                signal_tag = "GIRO MACRO · CHoCH BAJISTA"
            elif rev["choch"] == "BEARISH_CHOCH":
                signal_tag = "CHoCH BAJISTA · OB"
            else:
                signal_tag = "VENTA OB" if price < eq_50 * 1.002 else "RE-ENTRADA OB"

        # 5. CONFLUENCIA MACRO + TÉCNICA
        dominant_w = max(w_up, w_dn)
        if macro_dir == chart_bias:
            alignment = "ALIGNED"
            conf_score = min(94, 68 + (dominant_w * 3) + (4 if macro_backed_reversal else 0))
            verdict_title = "GIRO CONFIRMADO · MACRO + TÉCNICO" if macro_backed_reversal else "VAN JUNTOS · CONFLUENCIA"
            verdict_sub = f"Flujo macro ({macro_dir}) respalda estructura ({chart_bias})"
        elif macro_dir == "NEUTRAL":
            alignment = "ALIGNED"
            conf_score = min(78, 56 + (dominant_w * 3))
            verdict_title = "ESTRUCTURA MANDA · MACRO PLANA"
            verdict_sub = f"Jerarquía 1D/4H apunta a {chart_bias} · Macro en rango"
        else:
            alignment = "OPPOSED"
            conf_score = max(32, 46 - (dominant_w * 2))
            verdict_title = "CONTRADICCIÓN · TESIS ROTA"
            verdict_sub = f"Macro en {macro_dir} rechaza movimiento {chart_bias}"

        # 6. DETECCIÓN DE NOTICIA DE ALTO IMPACTO HOY PARA ESTE PAR
        ccys_to_check = {"USD"} if cfg["type"] in ("index", "crypto") else ({base_ccy, quote_ccy} - {"XAU"})
        if base_ccy == "XAU":
            ccys_to_check.add("USD")

        pair_news_titles = []
        affected_ccys = []
        for c in sorted(ccys_to_check):
            if c in high_impact_by_ccy:
                affected_ccys.append(c)
                pair_news_titles.extend(high_impact_by_ccy[c])

        has_high_news = len(pair_news_titles) > 0
        news_warning = None
        if has_high_news:
            news_warning = {
                "active": True,
                "currencies": "/".join(affected_ccys),
                "label": f"⚠️ NOTICIA FUERTE {'/'.join(affected_ccys)} HOY · OPERAR CON CUIDADO",
                "events": pair_news_titles[:3]
            }

        rev_note = f" Giro detectado ({rev['sweep'] if rev['sweep'] != 'NONE' else rev['choch']}) con respaldo macro." if macro_backed_reversal else ""
        macro_reason = f"{macro_detail} Jerarquía (1D:{b_d}, 4H:{b_4h}, 1H:{b_1h}).{rev_note}"

        return {
            "symbol": sym,
            "type": cfg["type"],
            "pip": pip,
            "decimals": dec,
            "price": price,
            "chg_day": chg_day,
            "chart_bias": chart_bias,
            "tf_bias": {"daily": b_d, "h4": b_4h, "h1": b_1h},
            "intraday_high": round(intraday_high, dec),
            "intraday_low": round(intraday_low, dec),
            "ob_high": ob_high,
            "ob_low": ob_low,
            "macro_reason": macro_reason,
            "news_warning": news_warning,
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

def main():
    now_utc = datetime.now(timezone.utc)
    dxy_4h = group_4h(get_candles("DX-Y.NYB", "1mo", "1h", 2, 180))
    us10y_4h = group_4h(get_candles("^TNX", "1mo", "1h", 2, 180))
    dxy_val = dxy_4h[-1]["c"] if dxy_4h else 104.20
    us10y_val = us10y_4h[-1]["c"] if us10y_4h else 4.25

    calendar_events, high_impact_by_ccy = fetch_high_impact_calendar(now_utc)

    bundles = {}
    c4_map = {}
    for cfg in ASSETS_CONFIG:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        c_1d = get_candles(cfg["yf"], "3mo", "1d", dec, 45)
        c_1h_long = get_candles(cfg["yf"], "1mo", "1h", dec, 180)
        c_4h = group_4h(c_1h_long)
        c_1h = c_1h_long[-45:] if c_1h_long else []
        bundles[sym] = {"1d": c_1d, "4h": c_4h, "1h": c_1h}
        c4_map[sym] = c_4h

    raw_strength, ccy_labels, spx_chg = compute_currency_strength_matrix(c4_map, dxy_4h, us10y_4h, c4_map.get("US500", []))
    assets = [item for cfg in ASSETS_CONFIG if (item := build_asset(cfg, bundles.get(cfg["symbol"], {}), raw_strength, ccy_labels, high_impact_by_ccy))]
    banks = get_central_banks(dxy_val, us10y_val, ccy_labels)
    news = fetch_live_news()

    alert_ccys = sorted(high_impact_by_ccy.keys())
    news_alert_str = f" · ⚠️ Noticias fuertes hoy en: {', '.join(alert_ccys)}" if alert_ccys else ""

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"USD {ccy_labels.get('USD')} (DXY {dxy_val} · US10Y {us10y_val}%) | GBP {ccy_labels.get('GBP')} | AUD {ccy_labels.get('AUD')}{news_alert_str}",
            "summary": f"Matriz multidivisa 4H y giros con respaldo macro sobre {len(assets)} activos (bloques clásicos sin pullbacks artificiales)."
        },
        "banks": banks,
        "news": news,
        "calendar": calendar_events,
        "assets": assets
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(assets)} activos guardados. Divisas con noticia fuerte hoy: {alert_ccys}")

if __name__ == "__main__":
    main()
