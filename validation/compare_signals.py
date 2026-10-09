"""Compare independently annotated reference events with scanner output.
Input CSV columns: timestamp_utc,market,indicator,expected
Supported indicators: HVR, PbD. Events must come from the original indicators,
not from this scanner; no reference events means NOT VALIDATED.
"""
import argparse,csv,json,collections
from datetime import datetime,timezone
from pathlib import Path
def load_rows(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def compare(reference,observed):
    allowed={"HVR","PbD"}
    actual={}
    for r in observed:
        if r.get("indicator") in allowed:
            actual[(r["timestamp_utc"],r["market"],r["indicator"])]=r.get("observed","n.v.")
    summary={}
    for indicator in sorted(allowed):
        refs=[r for r in reference if r.get("indicator")==indicator]
        matched=0;disagreements=[];missing=0
        for r in refs:
            key=(r["timestamp_utc"],r["market"],indicator)
            if key not in actual:
                missing+=1
            elif actual[key]==r["expected"]:
                matched+=1
            else:
                disagreements.append({"timestamp_utc":key[0],"market":key[1],"expected":r["expected"],"observed":actual[key]})
        n=len(refs)
        summary[indicator]={"reference_count":n,"matched":matched,"missing_observations":missing,"disagreements":disagreements,
                            "agreement_rate":round(matched/n,4) if n else None,
                            "validated":bool(n>=10 and missing==0 and not disagreements)}
    return summary
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",required=True)
    ap.add_argument("--observed",required=True)
    ap.add_argument("--output",default="data/validation.json")
    args=ap.parse_args()
    reference=load_rows(args.reference)
    observed=load_rows(args.observed)
    result={"generated_at":datetime.now(timezone.utc).isoformat(),
            "note":"Reference events must be independently labeled from the original indicators. Agreement alone does not prove profitability.",
            "results":compare(reference,observed)}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result["results"],ensure_ascii=False))
if __name__=="__main__":main()
