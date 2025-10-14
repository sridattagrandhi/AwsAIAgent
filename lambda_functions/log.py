# lambda_functions/log.py
import json, sys, time

def jlog(**kwargs):
    # Print to stderr so it shows up clearly in CloudWatch later too
    payload = {"ts": int(time.time()), **kwargs}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
