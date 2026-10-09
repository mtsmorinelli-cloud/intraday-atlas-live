#!/usr/bin/env python3
"""Conservative public-data scanner. No broker execution or fabricated signals."""
import json, math, os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

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
    if not (v.iloc[-240:] > 0).all():return {"state":"n.v.","reason":"Volumen fehlt"}
    atr=(df["high"]-df["low"]).rolling(200).mean()
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
    if d=="LONG":
        hold=last["low"]<=p+w and last["close"]>p
        flip=prev["close"]<p and last["close"]>p+w
        state="HOLD" if hold else "FLIP" if flip else "ZONE"
    else:
        hold=last["high"]>=p-w and last["close"]<p
        flip=prev["close"]>p and last["close"]<p-w
        state="HOLD" if hold else "FLIP" if flip else "ZONE"
    return {"state":state,"direction":d,"pivot":round(p,5),"reason":"Pivot 12/12, RVOL und Wick bestätigt; vereinfachte Hold/Flip-Auswertung"}
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
def analyze(m,t):
    base={"market":m,"reference":t or "nicht zuordenbar","bias":"n.v.","m15":"n.v.","pbd":"n.v.","hvr":"n.v.","score":None,"news":"UNGEPRÜFT","status":"NO TRADE","reason":"Keine Daten","price":None}
    if not t:return {**base,"reason":"Broker-Symbol nicht eindeutig abbildbar"}
    m15=closed(fetch(t,"10d","15m"),15); h1=closed(fetch(t,"1mo","1h"),60)
    if m15 is None or h1 is None or len(m15)<45 or len(h1)<80:return {**base,"status":"WATCH","reason":"M15/H1 unvollständig"}
    # H4 via hourly completed four-hour UTC bars; partial periods discarded
    h4=h1.resample("4h",origin="epoch").agg({"open":"first","high":"max","low":"min","close":"last"})
    h4=h4.dropna()
    if len(h4)<25:return {**base,"status":"WATCH","reason":"H4 unvollständig"}
    bias1=swing(h1);bias4=swing(h4);s15=swing(m15)
    price=float(m15["close"].iloc[-1]);age=(NOW-m15.index[-1].to_pydatetime()).total_seconds()/60
    stale=age>75
    hv=hvr(m15);pb=pbd_proxy(m15)
    alignment=bias1==bias4 and bias1 in ("LONG","SHORT")
    aligned15=alignment and s15==bias1
    # M15 sweep/reclaim of previous candle; M5/M1 optional, not fabricated.
    prev=m15.iloc[-2];last=m15.iloc[-1]
    sweep=(last["low"]<prev["low"] and last["close"]>prev["low"]) if bias1=="LONG" else (last["high"]>prev["high"] and last["close"]<prev["high"]) if bias1=="SHORT" else False
    displacement=abs(float(last["close"]-last["open"]))>1.2*float((m15["close"]-m15["open"]).abs().tail(20).mean())
    hv_ok=hv.get("state") in ("HOLD","FLIP") and hv.get("direction")==bias1
    active=session(m,NOW.astimezone(TZ))
    # News calendar not connected: never issue actionable SETUP.
    score=sum((alignment,aligned15,sweep,hv_ok,active,displacement))
    return {**base,"price":round(price,6),"asof":m15.index[-1].isoformat(),"bias":bias1 if alignment else "UNKLAR","m15":s15 or "n.v.","pbd":pb,"hvr":hv["state"],"hvr_detail":hv,"score":score if not stale else None,"news":"UNGEPRÜFT","status":"WATCH" if not stale else "NO TRADE","reason":"News-Kalender nicht verifiziert; keine Handelsfreigabe"+("; Kerzen veraltet" if stale else ""),"session":active,"sweep_m15":bool(sweep),"displacement":bool(displacement),"score_components":{"HTF":bool(alignment),"M15":bool(aligned15),"Sweep":bool(sweep),"HVR":bool(hv_ok),"Session":bool(active),"Displacement":bool(displacement)}}
out={"generated_at":NOW.isoformat(),"engine":"Intraday Atlas experimentell v0.2","live_execution":False,"news_verified":False,"warning":"Keine Handelsfreigabe. PbD ist nur ein Preis-Proxy, HVR eine vereinfachte BOSWaves-inspirierte Umsetzung. News nicht angebunden. Yahoo-Daten verzögert/fehlend möglich.","markets":[]}
for m,t in MARKETS.items():
    try:out["markets"].append(analyze(m,t))
    except Exception as e:out["markets"].append({"market":m,"reference":t,"status":"NO TRADE","score":None,"reason":"Daten-/Berechnungsfehler: "+type(e).__name__})
os.makedirs("data",exist_ok=True)
with open("data/scanner.json","w",encoding="utf8") as f:json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False)
print("generated",len(out["markets"]),"markets")
