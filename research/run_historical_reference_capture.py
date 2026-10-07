"""Return success only for complete primary capture; preserve old capture evidence."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.capture_historical_reference_inventory import run
from research.recover_lowliq_history_request import digest


def completion_exit_code(result):
    target=result.get('target_windows')
    complete=(type(target) is int and target>0 and result.get('processed_windows')==target
        and result.get('unvisited_windows')==0 and result.get('failure') is None
        and result.get('status')=='ALL_WINDOWS_ATTEMPTED'
        and result.get('statuses')=={'complete':target}
        and len(result.get('results',[]))==target
        and len({r.get('window') for r in result['results']})==target
        and all(r.get('window') and r.get('status')=='complete' for r in result['results']))
    return 0 if complete else 2


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--root',type=Path);mode.add_argument('--receipt',type=Path)
    parser.add_argument('--receipt-sha256');parser.add_argument('--budget',type=float,default=1800)
    parser.add_argument('--max-new-windows',type=int,default=1000)
    args=parser.parse_args(argv)
    if args.receipt:
        if not args.receipt_sha256 or digest(args.receipt)!=args.receipt_sha256:
            parser.error('receipt mode requires its matching trusted SHA256')
        result=json.loads(args.receipt.read_text())
    else:
        if args.receipt_sha256:parser.error('receipt digest requires receipt mode')
        result=run(args.root,args.budget,args.max_new_windows)
    code=completion_exit_code(result)
    print(json.dumps({'completion_exit_code':code,'capture_complete':code==0,
        'status':result.get('status'),'target_windows':result.get('target_windows'),
        'processed_windows':result.get('processed_windows'),'statuses':result.get('statuses'),
        'source_certified':False,'publication_allowed':False}),flush=True)
    return code


if __name__=='__main__':sys.exit(main())
