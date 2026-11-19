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
                    out.append({
                        "t": int(idx.timestamp()),
                        "o": o_val,
                        "h": h_val,
                        "l": l_val,
                        "c": c_val,
                    })
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"Aviso {ticker_str} ({interval}): {e}")
        return []

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
        news_items = [
            {"source": "Radar Institucional", "title": "Flujos de liquidez concentrados en apertura de Londres y Nueva York; atención a rendimientos del Tesoro a 10 años.", "link": "#", "time": "En línea"},
            {"source": "Mesa Divisas", "title": "Inversores evalúan diferenciales de tasas entre la Reserva Federal, el Banco Central Europeo y el Banco de Japón.", "link": "#", "time": "En línea"}
        ]
    return news_items[:8]

def get_central_banks(dxy_val, us10y_val):
    usd_hawk = dxy_val >= 103.5 or us10y_val >= 4.1
    return [
        {
            "bank": "FED (EE.UU.)",
            "currency": "USD",
            "stance": "RESTRICTIVA (HAWKISH)" if usd_hawk else "NEUTRAL / CAUTA",
            "bias": "BULLISH" if usd_hawk else "NEUTRAL",
            "detail": f"DXY en {dxy_val} y bonos US10Y en {us10y_val}%. Prioridad en control de inflación y datos de empleo."
        },
        {
            "bank": "BCE (Eurozona)",
            "currency": "EUR",
            "stance": "FLEXIBILIZACIÓN GRADUAL",
            "bias": "BEARISH",
            "detail": "Enfoque dependiente de datos ante desaceleración industrial europea; presión bajista frente a un USD firme."
        },
        {
            "bank": "BoE (Reino Unido)",
            "currency": "GBP",
            "stance": "CAUTELA EN RECORTES",
            "bias": "NEUTRAL",
            "detail": "Inflación persistente en servicios mantiene diferencial atractivo para la libra en cruces de rendimiento."
        },
        {
            "bank": "BoJ (Japón)",
            "currency": "JPY",
            "stance": "NORMALIZACIÓN LENTA",
            "bias": "BEARISH",
            "detail": "Diferencial de tasas frente a EE.UU. y Europa sigue condicionando movimientos bruscos en USDJPY, GBPJPY y AUDJPY."
        },
        {
            "bank": "RBA (Australia)",
            "currency": "AUD",
            "stance": "VIGILANCIA DE INFLACIÓN",
            "bias": "NEUTRAL",
            "detail": "Sensible a materias primas, crecimiento asiático y diferencial de rendimiento frente al dólar estadounidense y el yen."
        }
    ]

def calc_bias(candles):
    if len(candles) < 6:
        return "NEUTRAL"
    first = candles[-6]["c"]
    last = candles[-1]["c"]
    if last > first * 1.0005:
        return "SUBE"
    if last < first * 0.9995:
        return "BAJA"
    return "NEUTRAL"

def build_asset(cfg, usd_bias):
    try:
        sym = cfg["symbol"]
        dec = cfg["decimals"]
        pip = cfg["pip"]

        c_1d = get_candles(cfg["yf"], "3mo", "1d", dec, 45)
        c_4h_raw = get_candles(cfg["yf"], "1mo", "1h", dec, 180)
        c_4h = []
        if c_4h_raw:
            for i in range(0, len(c_4h_raw), 4):
                chunk = c_4h_raw[i:i+4]
                c_4h.append({
                    "t": chunk[0]["t"],
                    "o": chunk[0]["o"],
                    "h": max(x["h"] for x in chunk),
                    "l": min(x["l"] for x in chunk),
                    "c": chunk[-1]["c"],
                })
            c_4h = c_4h[-45:]
        c_1h = get_candles(cfg["yf"], "10d", "1h", dec, 45)

        if not c_1h and c_1d:
            c_1h = c_1d[-30:]
        if not c_4h and c_1d:
            c_4h = c_1d[-30:]
        if not c_1h:
            print(f"Omitido {sym}: sin velas disponibles.")
            return None

        price = c_1h[-1]["c"]
        prev_close = c_1d[-2]["c"] if len(c_1d) >= 2 else c_1h[0]["o"]
        chg_day = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0

        b_d = calc_bias(c_1d)
        b_4h = calc_bias(c_4h)
        b_1h = calc_bias(c_1h)

        score_up = (1 if b_d == "SUBE" else 0) + (1 if b_4h == "SUBE" else 0) + (1 if b_1h == "SUBE" else 0)
        score_dn = (1 if b_d == "BAJA" else 0) + (1 if b_4h == "BAJA" else 0) + (1 if b_1h == "BAJA" else 0)
        chart_bias = "SUBE" if score_up >= score_dn else "BAJA"

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
            signal_tag = "VENTA OB" if price < eq_50 * 1.002 else "RE-ENTRADA OB"

        macro_dir = "NEUTRAL"
        if cfg["quote"] == "USD":
            macro_dir = "BAJA" if usd_bias == "SUBE" else ("SUBE" if usd_bias == "BAJA" else "NEUTRAL")
        elif cfg["base"] == "USD":
            macro_dir = usd_bias

        if macro_dir == "NEUTRAL" or macro_dir == chart_bias:
            alignment = "ALIGNED"
            conf_score = 84 if macro_dir == chart_bias else 72
            verdict_title = "VAN JUNTOS · CONFLUENCIA"
            verdict_sub = f"Macro y gráfico apuntan a {chart_bias}"
        else:
            alignment = "OPPOSED"
            conf_score = 38
            verdict_title = "CONTRADICCIÓN · TESIS ROTA"
            verdict_sub = f"Macro sugiere {macro_dir}, gráfico {chart_bias}"

        macro_reason = (
            f"DXY con sesgo {usd_bias}. "
            + ("Flujo institucional respalda la dirección técnica." if alignment == "ALIGNED" else "Divergencia entre rendimiento del dólar y estructura intradía.")
        )

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
    dxy_candles = get_candles("DX-Y.NYB", "10d", "1h", 2, 24)
    us10y_candles = get_candles("^TNX", "10d", "1h", 2, 24)

    dxy_val = dxy_candles[-1]["c"] if dxy_candles else 104.20
    us10y_val = us10y_candles[-1]["c"] if us10y_candles else 4.25
    usd_bias = calc_bias(dxy_candles) if dxy_candles else "NEUTRAL"

    assets = []
    for cfg in ASSETS_CONFIG:
        item = build_asset(cfg, usd_bias)
        if item:
            assets.append(item)

    banks = get_central_banks(dxy_val, us10y_val)
    news = fetch_live_news()

    payload = {
        "last_updated": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "brief": {
            "dxy": dxy_val,
            "us10y": us10y_val,
            "headline": f"DXY en {dxy_val} ({usd_bias}) · Rendimiento Bonos US10Y en {us10y_val}%",
            "summary": f"Telemetría macro actualizada sobre {len(assets)} activos (incluyendo pares AUD y GBP). El índice del dólar presenta sesgo {usd_bias}."
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

    print(f"OK: {len(assets)} activos, {len(banks)} bancos y {len(news)} noticias guardados en data.json.")

if __name__ == "__main__":
    main()
