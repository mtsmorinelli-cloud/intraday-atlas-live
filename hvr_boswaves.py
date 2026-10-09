"""BOSWaves HVR signal-state port, based on user-supplied MPL-2.0 Pine v6.
Copyright (c) BOSWaves; source indicator High Volume Rejection Zones.
Core calculation and event state only; visual drawing omitted.
"""
import math
import pandas as pd

def _true_atr(df, n=200):
    prior=df["close"].shift(1)
    tr=pd.concat([df["high"]-df["low"],(df["high"]-prior).abs(),(df["low"]-prior).abs()],axis=1).max(axis=1)
    # Pine ta.atr uses RMA, not SMA; seed with SMA of first n true ranges.
    values=tr.to_numpy(dtype=float)
    result=[float("nan")]*len(values)
    if len(values)<n:return result
    prev=float(sum(values[:n])/n)
    result[n-1]=prev
    for j in range(n,len(values)):
        prev=(prev*(n-1)+float(values[j]))/n
        result[j]=prev
    return result

def hvr_boswaves(df):
    """Confirmed bars only. Return latest-bar event, zone states and diagnostics.
    Price/volume units must match the source TradingView series for signal parity.
    """
    unavailable={"state":"n.v.","direction":None,"reason":"OHLCV oder Historie nicht ausreichend","zones":[]}
    if df is None or len(df)<225:return unavailable
    a=df.reset_index(drop=True)
    needed=("open","high","low","close","volume")
    if any(k not in a for k in needed):return unavailable
    if a[list(needed)].isna().any().any():return unavailable
    if (a["volume"]<=0).any():return {**unavailable,"reason":"Fehlendes oder null Volumen"}
    atr=_true_atr(a)
    volavg=a["volume"].rolling(20,min_periods=20).mean()
    support=None;resistance=None
    events=[]
    def valid_pivot(i,kind):
        # Pine ta.pivotlow/high with 12 left and 12 right.
        v=float(a[kind].iloc[i])
        left=a[kind].iloc[i-12:i];right=a[kind].iloc[i+1:i+13]
        # Strict tie resolution: later equal extremes invalidate older pivot.
        return (v<=left.min() and v<right.min()) if kind=="low" else (v>=left.max() and v>right.max())
    for j in range(len(a)):
        # Creation occurs on confirmation bar j, using pivot j-12.
        i=j-12
        if i>=max(12,199):
            candle=a.iloc[i]
            rng=float(candle["high"]-candle["low"])
            if rng>0 and math.isfinite(atr[i]) and volavg.iloc[i]>0:
                rvol=float(candle["volume"]/volavg.iloc[i])
                up=float(candle["high"]-max(candle["open"],candle["close"]))/rng
                down=float(min(candle["open"],candle["close"])-candle["low"])/rng
                awayhi=float(candle["high"]-candle["close"])/rng
                awaylo=float(candle["close"]-candle["low"])/rng
                if rvol>=1.15 and up>=.25 and awayhi>=.5 and valid_pivot(i,"high"):
                    p=float(candle["high"])
                    resistance={"kind":"RESISTANCE","pivot":p,"edge":p+atr[i]*.3,"pivot_bar":i,"created":j,"broken":False,"break_bar":None,"hold_done":False,"flip_done":False,"rvol":round(rvol,3)}
                if rvol>=1.15 and down>=.25 and awaylo>=.5 and valid_pivot(i,"low"):
                    p=float(candle["low"])
                    support={"kind":"SUPPORT","pivot":p,"edge":p-atr[i]*.3,"pivot_bar":i,"created":j,"broken":False,"break_bar":None,"hold_done":False,"flip_done":False,"rvol":round(rvol,3)}
        candle=a.iloc[j]
        # Match original order: resistance processed before support.
        for zone in (resistance,support):
            if zone is None or j-zone["pivot_bar"]>200:continue
            if not zone["broken"]:
                if j>zone["created"] and not zone["hold_done"]:
                    if zone["kind"]=="RESISTANCE" and candle["high"]>=zone["pivot"] and candle["close"]<zone["pivot"]:
                        zone["hold_done"]=True;events.append((j,"BEAR_HOLD",zone.copy()))
                    elif zone["kind"]=="SUPPORT" and candle["low"]<=zone["pivot"] and candle["close"]>zone["pivot"]:
                        zone["hold_done"]=True;events.append((j,"BULL_HOLD",zone.copy()))
                if zone["kind"]=="RESISTANCE" and candle["close"]>zone["edge"]:
                    zone["broken"]=True;zone["break_bar"]=j
                elif zone["kind"]=="SUPPORT" and candle["close"]<zone["edge"]:
                    zone["broken"]=True;zone["break_bar"]=j
            elif j>zone["break_bar"] and not zone["flip_done"]:
                if zone["kind"]=="RESISTANCE" and candle["low"]<=zone["edge"] and candle["close"]>zone["edge"]:
                    zone["flip_done"]=True;events.append((j,"BULL_FLIP",zone.copy()))
                elif zone["kind"]=="SUPPORT" and candle["high"]>=zone["edge"] and candle["close"]<zone["edge"]:
                    zone["flip_done"]=True;events.append((j,"BEAR_FLIP",zone.copy()))
        if resistance and j-resistance["pivot_bar"]>200:resistance=None
        if support and j-support["pivot_bar"]>200:support=None
    last_events=[(name,z) for idx,name,z in events if idx==len(a)-1]
    latest=last_events[-1] if last_events else None
    zones=[z for z in (support,resistance) if z is not None]
    if latest:
        name,z=latest
        return {"state":name,"direction":"LONG" if name.startswith("BULL") else "SHORT","pivot":z["pivot"],"edge":z["edge"],"rvol":z["rvol"],"reason":"BOSWaves Hold/Flip auf abgeschlossener Kerze","zones":zones}
    return {"state":"ZONE" if zones else "NONE","direction":None,"reason":"Kein neues Hold/Flip-Ereignis auf letzter Kerze","zones":zones}
