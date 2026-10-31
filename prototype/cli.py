import argparse
import json
from service import demo, review, scenarios
def main():
    parser=argparse.ArgumentParser(description="VEIL advisory prototype")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("list")
    d=sub.add_parser("demo");d.add_argument("case_id",nargs="?",default="P01")
    r=sub.add_parser("review");r.add_argument("--action",required=True);r.add_argument("--context",required=True)
    args=parser.parse_args()
    if args.command=="list":
        result=[{"id":c["id"],"action":c["request"]["action"]} for c in scenarios()]
    elif args.command=="demo":
        try: result=demo(args.case_id)
        except ValueError as exc: parser.error(str(exc))
    else: result=review(args.action,args.context)
    print(json.dumps(result,indent=2))
    return 2 if isinstance(result,dict) and result.get("status")=="error" else 0
if __name__=="__main__": raise SystemExit(main())
