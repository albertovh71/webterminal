#!/usr/bin/env python3
import subprocess, json, datetime, os

CCUSAGE = "/home/ubuntu/.npm/_npx/b8bc0fb451ae8722/node_modules/@ccusage/ccusage-linux-x64/bin/ccusage"
OUT = "/opt/webterminal/claude-usage-cache.json"
TMPFILE = "/opt/webterminal/claude-usage-cache.json.tmp"
WEEKLY_LIMIT = float(os.environ.get("CLAUDE_WEEKLY_LIMIT_USD", "100"))

result = {}

try:
    p = subprocess.run([CCUSAGE, "blocks", "--active", "--json"], capture_output=True, timeout=15)
    blocks_data = json.loads(p.stdout) if p.stdout else {}
    blocks = blocks_data.get("blocks", [])
    if blocks:
        blk = blocks[0]
        proj = blk.get("projection", {})
        rem = proj.get("remainingMinutes")
        if rem is not None:
            result["window_pct"] = round(max(0.0, min(100.0, (300 - rem) / 300 * 100)), 1)
            result["window_reset_min"] = rem
        tc = blk.get("tokenCounts", {})
        result["session_tokens"] = {
            "input": tc.get("inputTokens", 0),
            "output": tc.get("outputTokens", 0),
            "cache_read": tc.get("cacheReadInputTokens", 0),
            "cache_create": tc.get("cacheCreationInputTokens", 0),
        }
except Exception as e:
    result["blocks_error"] = str(e)

try:
    p2 = subprocess.run([CCUSAGE, "weekly", "--json"], capture_output=True, timeout=15)
    weekly_data = json.loads(p2.stdout) if p2.stdout else {}
    weekly = weekly_data.get("weekly", [])
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    week_str = week_start.strftime("%Y-%m-%d")
    current_week = next((w for w in weekly if w["period"] == week_str), None)
    if current_week:
        cost = current_week.get("totalCost", 0)
        result["weekly_pct"] = round(min(100.0, cost / WEEKLY_LIMIT * 100), 1)
        result["weekly_cost"] = round(cost, 2)
        result["weekly_limit"] = WEEKLY_LIMIT
    days_to_monday = (7 - today.weekday()) % 7 or 7
    result["weekly_reset_days"] = days_to_monday
except Exception as e:
    result["weekly_error"] = str(e)

result["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

with open(TMPFILE, "w") as f:
    json.dump(result, f)
os.chmod(TMPFILE, 0o644)
os.replace(TMPFILE, OUT)
