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

def find_fresh_ob(c_4h, c_1h, direction, price, pip, dec):
    """
    Busca primero un Order Block fresco/anticipado en 4H o 1H donde el precio
    AÚN NO haya despegado más allá de TP1, evitando entradas viejas ya corridas.
    """
    if direction == "BUY":
        # 1. Buscar vela bajista en últimas 6 velas de 1H (bloque fresco de continuación)
        recent_bears = [x for x in c_1h[-7:-1] if x["c"] < x["o"] and x["l"] <= price]
        if recent_bears:
            ob = recent_bears[-1]
            ob_low = round(ob["l"], dec)
            ob_high = round(max(ob["h"], ob_low + 8 * pip), dec)
            return ob_low, ob_high, "COMPRA OB FRESCO"

        # 2. Buscar Order Block institucional en 4H (última vela roja antes de impulso verde) aún cerca del precio
        for i in range(len(c_4h) - 2, max(1, len(c_4h) - 14), -1):
            c_prev = c_4h[i]
            c_next = c_4h[i + 1]
            if c_prev["c"] < c_prev["o"] and c_next["c"] > c_prev["h"] and c_prev["l"] <= price:
                # Verificar que el precio no esté lejísimos (máximo 45 pips/pts arriba)
                if (price - c_prev["h"]) <= 45 * pip:
                    ob_low = round(c_prev["l"], dec)
                    ob_high = round(max(c_prev["h"], ob_low + 10 * pip), dec)
                    return ob_low, ob_high, "OB 4H ANTICIPADO"

        # 3. Retroceso dinámico a zona de descuento cercana al precio actual (nunca a 80+ pips abajo)
        ob_high = round(price - (6 * pip), dec)
        ob_low = round(ob_high - (10 * pip), dec)
        return ob_low, ob_high, "PULLBACK COMPRA"
    else:
        # 1. Buscar vela alcista en últimas 6 velas de 1H (bloque fresco de continuación)
        recent_bulls = [x for x in c_1h[-7:-1] if x["c"] > x["o"] and x["h"] >= price]
        if recent_bulls:
            ob = recent_bulls[-1]
            ob_high = round(ob["h"], dec)
            ob_low = round(min(ob["l"], ob_high - 8 * pip), dec)
            return ob_low, ob_high, "VENTA OB FRESCO"

        # 2. Buscar Order Block institucional en 4H (última vela verde antes de caída roja) aún cerca del precio
        for i in range(len(c_4h) - 2, max(1, len(c_4h) - 14), -1):
            c_prev = c_4h[i]
            c_next = c_4h[i + 1]
            if c_prev["c"] > c_prev["o"] and c_next["c"] < c_prev["l"] and c_prev["h"] >= price:
                if (c_prev["l"] - price) <= 45 * pip:
                    ob_high = round(c_prev["h"], dec)
                    ob_low = round(min(c_prev["l"], ob_high - 10 * pip), dec)
                    return ob_low, ob_high, "OB 4H ANTICIPADO"

        # 3. Retroceso dinámico cercano al precio actual
        ob_low = round(price + (6 * pip), dec)
        ob_high = round(ob_low + (10 * pip), dec)
        return ob_low, ob_high, "PULLBACK VENTA"

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

    raw = {"USD": usd_score, "GBP": gbp_score, "AUD": aud_score, "EUR": eur_score, "JPY": jpy_score, "NZD": nzd_score, "CAD": cad_score, "CHF": chf_score, "XAU": xau_score, "BTC": spx_chg * 0.8 - usd_score * 0.5}
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

def build_asset(cfg, candles_bundle, raw_strength, ccy_labels):
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

        b_d = calc_bias(c_1d, 6, 0.0010)
        b_4h = calc_bias(c_4h, 6, 0.0008)
        b_1h = calc_bias(c_1h, 6, 0.0006)

        w_up = (3 if b_d == "SUBE" else 0) + (2 if b_4h == "SUBE" else 0) + (1 if b_1h == "SUBE" else 0)
        w_dn = (3 if b_d == "BAJA" else 0) + (2 if b_4h == "BAJA" else 0) + (1 if b_1h == "BAJA" else 0)
        chart_bias = "SUBE" if w_up >= w_dn else "BAJA"

        base_ccy = cfg["base"]
        quote_ccy = cfg["quote"]
        if cfg["type"] == "index":
            macro_diff = raw_strength.get("BTC", 0.0)
            macro_dir = "SUBE" if macro_diff > 0.10 else ("BAJA" if macro_diff < -0.10 else "NEUTRAL")
            macro_detail = f"Apetito al riesgo US500 y USD ({ccy_labels.get('USD', 'NEUTRAL')})."
        else:
            macro_diff = raw_strength.get(base_ccy, 0.0) - raw_strength.get(quote_ccy, 0.0)
            macro_dir = "SUBE" if macro_diff > 0.12 else ("BAJA" if macro_diff < -0.12 else "NEUTRAL")
            macro_detail = f"{base_ccy} ({ccy_labels.get(base_ccy, 'NEUTRAL')}) vs {quote_ccy} ({ccy_labels.get(quote_ccy, 'NEUTRAL')}) en cesta 4H."

        recent = c_1h[-24:]
        intraday_high = max(x["h"] for x in recent)
        intraday_low = min(x["l"] for x in recent)
        eq_50 = (intraday_high + intraday_low) / 2.0

        direction = "BUY" if chart_bias == "SUBE" else "SELL"
        ob_low, ob_high, signal_tag = find_fresh_ob(c_4h, c_1h, direction, price, pip, dec)
        entry = round((ob_low + ob_high) / 2.0, dec)

        risk = max(14 * pip, round((intraday_high - intraday_low) * 0.22, dec))
        if direction == "BUY":
            sl = round(ob_low - (4 * pip), dec)
            if (entry - sl) < 12 * pip:
                sl = round(entry - risk, dec)
            actual_risk = abs(entry - sl)
            tp1 = round(entry + (actual_risk * 2.0), dec)
            tp2 = round(entry + (actual_risk * 3.0), dec)
            in_good_zone = price <= eq_50 * 1.002
        else:
            sl = round(ob_high + (4 * pip), dec)
            if (sl - entry) < 12 * pip:
                sl = round(entry + risk, dec)
            actual_risk = abs(sl - entry)
            tp1 = round(entry - (actual_risk * 2.0), dec)
            tp2 = round(entry - (actual_risk * 3.0), dec)
            in_good_zone = price >= eq_50 * 0.998

        dominant_w = max(w_up, w_dn)
        if macro_dir == chart_bias:
            alignment = "ALIGNED"
            conf_score = min(94, 68 + (dominant_w * 3) + (4 if in_good_zone else 0))
            verdict_title = "VAN JUNTOS · CONFLUENCIA"
            verdict_sub = f"Cesta macro ({macro_dir}) y estructura ({chart_bias}) alineadas"
        elif macro_dir == "NEUTRAL":
            alignment = "ALIGNED"
            conf_score = min(79, 56 + (dominant_w * 3) + (3 if in_good_zone else 0))
            verdict_title = "ESTRUCTURA MANDA · MACRO PLANA"
            verdict_sub = f"Jerarquía 1D/4H apunta a {chart_bias} · Macro en rango"
        else:
            alignment = "OPPOSED"
            conf_score = max(32, 48 - (dominant_w * 2))
            verdict_title = "CONTRADICCIÓN · TESIS ROTA"
            verdict_sub = f"Flujo macro sugiere {macro_dir}, gráfico {chart_bias}"

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
            "macro_reason": f"{macro_detail} Jerarquía técnica (1D:{b_d}, 4H:{b_4h}, 1H:{b_1h}).",
            "confluence": {"score": conf_score, "alignment": alignment, "verdict_title": verdict_title, "verdict_sub": verdict_sub},
            "setup": {"direction": direction, "signal_tag": signal_tag, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2},
            "candles": {"1d": c_1d, "4h": c_4h, "1h": c_1h}
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
    assets = [item for cfg in ASSETS_CONFIG if (item := build_asset(cfg, bundles.get(cfg["symbol"], {}), raw_strength, ccy_labels))]
    banks = get_central_banks(dxy_val, us10y_val, ccy_labels)
    news = fetch_live_news()

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"USD {ccy_labels.get('USD')} (DXY {dxy_val} · US10Y {us10y_val}%) | GBP {ccy_labels.get('GBP')} | AUD {ccy_labels.get('AUD')}",
            "summary": f"Matriz multidivisa 4H activa sobre {len(assets)} activos con Order Blocks anticipados."
        },
        "banks": banks,
        "news": news,
        "calendar": [
            {"date": now_utc.strftime("%Y-%m-%d"), "time": "07:00 UTC", "currency": "EUR/GBP", "impact": "ALTO", "title": "Apertura Killzone Londres · Barrido de Liquidez Asiática"},
            {"date": now_utc.strftime("%Y-%m-%d"), "time": "12:30 UTC", "currency": "USD", "impact": "ALTO", "title": "Apertura Killzone Nueva York · Flujo Institucional"},
            {"date": now_utc.strftime("%Y-%m-%d"), "time": "14:00 UTC", "currency": "USD", "impact": "MEDIO", "title": "PMI Manufacturero / Servicios & Subasta Bonos Tesoro"},
            {"date": now_utc.strftime("%Y-%m-%d"), "time": "23:50 UTC", "currency": "AUD/JPY", "impact": "MEDIO", "title": "Apertura Sesión Tokio & Sídney · Flujo Asia-Pacífico"}
        ],
        "assets": assets
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(assets)} activos con Order Blocks anticipados guardados en data.json.")

if __name__ == "__main__":
    main()
