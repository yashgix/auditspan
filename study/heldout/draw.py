"""Draw the blind hold-out after tag v2-rules-frozen. Writes ids and texts only (no form values, no extraction).

Usage: python -I draw.py REPO_DIR DEV_IDS_JSONL OUT_JSONL
"""

import json
import random
import sys

sys.path.insert(0, sys.argv[1])
from findingtrace.data import load  # noqa: E402

SEED = 20261115
SIZE = 150

findings = load(sys.argv[1] + "/data").findings
seen = {(row["report_id"], row["ref"]) for row in map(json.loads, open(sys.argv[2]))}
pool = sorted(f.key for f in findings if f.key not in seen)
drawn = random.Random(SEED).sample(pool, SIZE)
texts = {f.key: f.text for f in findings}
with open(sys.argv[3], "w", encoding="utf-8") as out:
    for report_id, ref in drawn:
        out.write(json.dumps({"id": f"{report_id} {ref}", "text": texts[report_id, ref]}, ensure_ascii=False) + "\n")
print(len(pool), "in pool,", len(drawn), "drawn with seed", SEED)
