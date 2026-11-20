def compute_currency_strength_matrix(c4_map, c1d_map, dxy_4h, dxy_1d, us10y_4h, us10y_1d, spx_4h, spx_1d):
    """
    Mide la fuerza macroeconómica combinando flujo intradía (60% en 4H)
    y estructura institucional de fondo (40% en 1D).
    """
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
    labels = {k: ("FUERTE" if v > 0.14 else ("DÉBIL" if v < -0.14 else "NEUTRAL")) for k, v in raw.items()}
    return raw, labels, round(spx_chg, 2)
