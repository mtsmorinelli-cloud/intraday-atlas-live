"""Optional Trading Economics calendar adapter. No API key in public output."""
import os, json, urllib.request
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

COUNTRIES=["united states","euro area","germany","japan","united kingdom","switzerland","australia"]
MAP={"united states":["EURUSD#","USDJPY#","GER40Cash#","US100Cash#","XAUJPY#","GBPJPY#","AUDUSD#","USDCHF#","US30Cash#"],
"euro area":["EURUSD#","GER40Cash#"],"germany":["EURUSD#","GER40Cash#"],
"japan":["USDJPY#","XAUJPY#","GBPJPY#"],"united kingdom":["GBPJPY#"],
"switzerland":["USDCHF#"],"australia":["AUDUSD#"]}
def build_calendar(now=None):
    now=now or datetime.now(timezone.utc)
    key=os.getenv("TRADING_ECONOMICS_API_KEY","").strip()
    if not key:return {"verified_at":None,"events":[],"provider":"not configured","coverage":"UNGEPRÜFT"}
    # TE REST Date values are timezone-naive in many responses. Do not silently
    # interpret them as UTC. Only accept timestamps with an explicit offset.
    url="https://api.tradingeconomics.com/calendar/country/"+quote(",".join(COUNTRIES))+"?c="+quote(key,safe="")+"&f=json"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"IntradayAtlas/0.4"})
        with urllib.request.urlopen(req,timeout=25) as response:
            rows=json.load(response)
        if not isinstance(rows,list) or not rows:raise ValueError("empty calendar")
        events=[];unresolved=0
        for row in rows:
            if not isinstance(row,dict) or int(row.get("Importance") or 0)!=3:continue
            country=str(row.get("Country","")).strip().lower()
            markets=MAP.get(country)
            if not markets:continue
            raw=str(row.get("Date",""))
            try:
                stamp=datetime.fromisoformat(raw.replace("Z","+00:00"))
                if stamp.tzinfo is None:
                    unresolved+=1
                    continue
            except ValueError:
                unresolved+=1
                continue
            if not (now-timedelta(hours=2)<=stamp<=now+timedelta(days=8)):continue
            events.append({"name":str(row.get("Event","High Impact"))[:140],"time_utc":stamp.astimezone(timezone.utc).isoformat(),"markets":markets,"impact":"high","country":country})
        # Incomplete timezones => no claim that the calendar is verified.
        complete=unresolved==0
        return {"verified_at":now.isoformat() if complete else None,"events":events,"provider":"Trading Economics","coverage":"TEILWEISE GEPRÜFT" if complete else "UNGEPRÜFT","unresolved_timestamps":unresolved}
    except Exception as e:
        return {"verified_at":None,"events":[],"provider":"Trading Economics","coverage":"UNGEPRÜFT","error":type(e).__name__}
