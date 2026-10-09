#!/usr/bin/env python3
"""Conservative public-data scanner. No broker execution or fabricated signals."""
import json, math, os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
from calendar_adapter import build_calendar
from hvr_boswaves import hvr_boswaves

MARKETS={
"EURUSD#":"EURUSD=X","USDJPY#":"JPY=X","GER40Cash#":"^GDAXI",
"US100Cash#":"NQ=F","XAUJPY#":None,"GBPJPY#":"GBPJPY=X",
"GAUUSD#":None,"AUDUSD#":"AUDUSD=X","USDCHF#":"CHF=X","US30Cash#":"YM=F"}
TZ=ZoneInfo("Europe/Berlin")
NOW=datetime.now(timezone.utc)
def clean(df):
    if df is None or df.empty:return None
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    df=df.rename(columns={x:x.lower() for x in df.columns})
    for x in ("open","high","low","close"):
        if x not in df:return None
    df=df.dropna(subset=["open","high","low","close"]).sort_index()
    if df.empty:return None
    if df.index.tz is None:df.index=df.index.tz_localize("UTC")
    return df
def fetch(ticker,period,interval):
    try:
        return clean(yf.Ticker(ticker).history(period=period,interval=interval,auto_adjust=False,prepost=False,raise_errors=True))
    except Exception:return None
def closed(df,mins):
    if df is None:return None
    # Yahoo bars are timestamped at their start. Drop unfinished bar.
    return df[df.index+pd.Timedelta(minutes=mins)<=pd.Timestamp(NOW)-pd.Timedelta(minutes=1)]
def swing(df,n=5):
    if df is None or len(df)<2*n+8:return None
    a=df.iloc[:-1]
    highs=[];lows=[]
    for i in range(n,len(a)-n):
        window=a.iloc[i-n:i+n+1]
        if a["high"].iloc[i]>=window["high"].max():highs.append(float(a["high"].iloc[i]))
        if a["low"].iloc[i]<=window["low"].min():lows.append(float(a["low"].iloc[i]))
    if not highs or not lows:return None
    close=float(df["close"].iloc[-1])
    return "LONG" if close>highs[-1] else "SHORT" if close<lows[-1] else "RANGE"
def hvr(df):
    # BOSWaves-inspired conservative confirmation, not an exact Pine port.
    if df is None or len(df)<245:return {"state":"n.v.","reason":"<245 abgeschlossene M15-Kerzen"}
    v=df["volume"] if "volume" in df else pd.Series(0,index=df.index)
    if (v.iloc[-240:] <= 0).any():return {"state":"n.v.","reason":"Volumen fehlt oder Nullwerte"}
    prior=df["close"].shift(1)
    true_range=pd.concat([df["high"]-df["low"],(df["high"]-prior).abs(),(df["low"]-prior).abs()],axis=1).max(axis=1)
    atr=true_range.rolling(200,min_periods=200).mean()
    vs=v.rolling(20).mean()
    zones=[]
    for i in range(max(212,len(df)-200),len(df)-12):
        w=df.iloc[i-12:i+13];c=df.iloc[i];rng=float(c["high"]-c["low"])
        if rng<=0 or not math.isfinite(float(atr.iloc[i])):continue
        if float(v.iloc[i])<1.15*float(vs.iloc[i]):continue
        bull=float(c["close"]-c["low"])/rng>=.5 and float(min(c["open"],c["close"])-c["low"])/rng>=.25 and c["low"]<=w["low"].min()
        bear=float(c["high"]-c["close"])/rng>=.5 and float(c["high"]-max(c["open"],c["close"]))/rng>=.25 and c["high"]>=w["high"].max()
        if bull or bear:
            pivot=float(c["low"] if bull else c["high"]);width=.3*float(atr.iloc[i])
            zones.append((i,"LONG" if bull else "SHORT",pivot,width))
    if not zones:return {"state":"NONE","reason":"Keine bestätigte Zone"}
    i,d,p,w=zones[-1]; last=df.iloc[-1];prev=df.iloc[-2]
    # Hold and flip are distinct: a flip requires a zone break and subsequent retest.
    earlier=df.iloc[i+13:-1]
    if d=="LONG":
        hold=last["low"]<=p+w and last["close"]>p
        flip=(earlier["close"]<p).any() and prev["close"]>p+w and last["low"]<=p+w and last["close"]>p+w
        state="HOLD" if hold else "FLIP" if flip else "ZONE"
    else:
        hold=last["high"]>=p-w and last["close"]<p
        flip=(earlier["close"]>p).any() and prev["close"]<p-w and last["high"]>=p-w and last["close"]<p-w
        state="HOLD" if hold else "FLIP" if flip else "ZONE"
    return {"state":state,"direction":d,"pivot":round(p,5),"confirmed_at":df.index[i+12].isoformat(),"reason":"Pivot 12/12, RVOL, ATR200 und Wick; vereinfachte BOSWaves-inspirierte Hold/Flip-Auswertung"}
def session(m,dt):
    h=dt.hour+dt.minute/60
    if m in ("US100Cash#","US30Cash#"):return 15.5<=h<17
    if m=="GER40Cash#":return 8<=h<11
    return 8<=h<11 or 13<=h<17
def pbd_proxy(df):
    # Price-based balance/impulse approximation, NOT Tom Vorwald's PbD.
    if df is None or len(df)<35:return "n.v."
    c=df["close"]; rng=(df["high"]-df["low"]).tail(20).mean()
    if not math.isfinite(rng) or rng<=0:return "n.v."
    move=float(c.iloc[-1]-c.iloc[-9])
    if move>2*rng and c.iloc[-1]>c.iloc[-20:-1].median():return "P (Proxy)"
    if move< -2*rng and c.iloc[-1]<c.iloc[-20:-1].median():return "B (Proxy)"
    return "D (Proxy)"
CALENDAR = build_calendar(NOW)

def news_guard(m):
    """Fail-closed calendar safety gate. No claim of verified complete news coverage."""
    try:
        cfg=CALENDAR
        checked=datetime.fromisoformat(cfg["verified_at"].replace("Z","+00:00"))
        if checked.tzinfo is None:raise ValueError("Timezone missing")
        if abs((NOW-checked).total_seconds())>12*3600:
            return "UNGEPRÜFT","Kalenderprüfung älter als 12 Stunden"
        for event in cfg.get("events",[]):
            if event.get("impact")!="high":continue
            affected=event.get("markets",[])
            if m not in affected and "ALL" not in affected:continue
            at=datetime.fromisoformat(event["time_utc"].replace("Z","+00:00"))
            if at.tzinfo is None:continue
            if abs((NOW-at).total_seconds())<=1800:
                return "NEWS BLOCK",event.get("name","High-Impact-News")
        return "TEILWEISE GEPRÜFT","Trading Economics: bekannte Termine geprüft; unerwartete News bleiben möglich"
    except Exception:return "UNGEPRÜFT","Kein aktueller verifizierter News-Kalender"

def analyze(m,t):
    base={"market":m,"reference":t or "nicht zuordenbar","bias":"n.v.","m15":"n.v.","pbd":"n.v.","hvr":"n.v.","score":None,"news":"UNGEPRÜFT","status":"NO TRADE","reason":"Keine Daten","price":None}
    if not t:return {**base,"reason":"Broker-Symbol nicht eindeutig abbildbar"}
    m15=closed(fetch(t,"10d","15m"),15); h1=closed(fetch(t,"1mo","1h"),60)
    if m15 is None or h1 is None or len(m15)<45 or len(h1)<80:return {**base,"status":"WATCH","reason":"M15/H1 unvollständig"}
    # H4 via hourly completed four-hour UTC bars; partial periods discarded
    # Keep only complete 4h buckets; incomplete H4 candles create false signals.
    h4_ohlc=h1.resample("4h",origin="epoch").agg({"open":"first","high":"max","low":"min","close":"last"})
    h4_count=h1["close"].resample("4h",origin="epoch").count()
    h4=h4_ohlc.loc[h4_count.eq(4)].dropna()
    if len(h4)<25:return {**base,"status":"WATCH","reason":"H4 unvollständig"}
    bias1=swing(h1);bias4=swing(h4);s15=swing(m15)
    price=float(m15["close"].iloc[-1]);age=(NOW-m15.index[-1].to_pydatetime()).total_seconds()/60
    stale=age>75
    hv=hvr_boswaves(m15);pb=pbd_proxy(m15)
    news_state,news_reason=news_guard(m)
    alignment=bias1==bias4 and bias1 in ("LONG","SHORT")
    aligned15=alignment and s15==bias1
    # M15 sweep/reclaim of previous candle; M5/M1 optional, not fabricated.
    prev=m15.iloc[-2];last=m15.iloc[-1]
    sweep=(last["low"]<prev["low"] and last["close"]>prev["low"]) if bias1=="LONG" else (last["high"]>prev["high"] and last["close"]<prev["high"]) if bias1=="SHORT" else False
    displacement=abs(float(last["close"]-last["open"]))>1.2*float((m15["close"]-m15["open"]).abs().tail(20).mean())
    hv_ok=hv.get("state") in ("BULL_HOLD","BEAR_HOLD","BULL_FLIP","BEAR_FLIP") and hv.get("direction")==bias1
    active=session(m,NOW.astimezone(TZ))
    score=int(sum((alignment,aligned15,sweep,hv_ok,active,displacement)))
    # Experimental observations are now shown even before Pine parity validation.
    # Never convert an unverified news window or missing structural risk into a trade order.
    qualified=bool(score>=4 and alignment and aligned15 and active and not stale and news_state!="NEWS BLOCK")
    if news_state=="NEWS BLOCK":
        status="NEWS BLOCK"
    elif stale or not active:
        status="NO TRADE"
    elif qualified:
        status="KANDIDAT"
    else:
        status="WATCH"
    reason=("Experimenteller Kandidat: News-Kalender unvollständig, kein verifizierter Entry/SL/TP"
            if qualified else "Regelkonfluenz nicht ausreichend oder Daten/Session ungeeignet")
    return {**base,"price":round(price,6),"asof":m15.index[-1].isoformat(),
            "bias":bias1 if alignment else "UNKLAR","m15":s15 or "n.v.","pbd":pb,
            "hvr":hv["state"],"hvr_detail":{k:v for k,v in hv.items() if k!="zones"},
            "score":score if not stale else None,"news":news_state,"news_reason":news_reason,
            "status":status,"reason":reason,"session":active,"sweep_m15":bool(sweep),
            "displacement":bool(displacement),"experimental_candidate":qualified,
            "score_components":{"HTF":bool(alignment),"M15":bool(aligned15),
            "Sweep":bool(sweep),"HVR":bool(hv_ok),"Session":bool(active),
            "Displacement":bool(displacement)}}

out={"generated_at":NOW.isoformat(),"engine":"Intraday Atlas experimentell v0.6","live_execution":False,"experimental_signals_enabled":True,"pbd_hvr_validated":False,"validation_status":"REFERENZVERGLEICH AUSSTEHEND","news_verified":bool(CALENDAR.get("verified_at")),"calendar_provider":CALENDAR.get("provider"),"calendar_coverage":CALENDAR.get("coverage"),"calendar_event_count":len(CALENDAR.get("events",[])),"warning":"Experimentelle Kandidatenanzeige AKTIV, ohne Validierungswartezeit. KEINE Orderfreigabe: News unvollständig, Entry/SL/TP nicht verifiziert. PbD ist Proxy; HVR-Python-Port noch nicht abgeglichen.","markets":[]}
for m,t in MARKETS.items():
    try:out["markets"].append(analyze(m,t))
    except Exception as e:out["markets"].append({"market":m,"reference":t,"status":"NO TRADE","score":None,"reason":"Daten-/Berechnungsfehler: "+type(e).__name__})
os.makedirs("data",exist_ok=True)
def json_safe(value):
    """Convert pandas/NumPy scalar values to native JSON types."""
    import numpy as np
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
with open("data/scanner.json","w",encoding="utf8") as f:
    json.dump(json_safe(out),f,ensure_ascii=False,indent=2,allow_nan=False)
print("generated",len(out["markets"]),"markets")
