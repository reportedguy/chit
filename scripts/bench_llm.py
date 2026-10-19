"""Smart-cleanup quality and latency per device, through the real Cleaner (light rules first).

Usage: python scripts/bench_llm.py <model-repo> CPU GPU NPU
"""

import sys
import time

from chit import models
from chit.cleanup import Cleaner, SmartCleaner

SAMPLES = [
    "Um, so I wanted to, uh, let you know that the meeting is on Tuesday. No wait, Wednesday at three. "
    "And, you know, please, like, bring the slides.",
    "what's the weather going to be like tomorrow",
    "hey can you uh can you review my PR when you get a chance it's the one about the login page",
    "acha toh matlab main kal office nahi aa paunga, uh, doctor ka appointment hai",
    "मतलब मैं कल ऑफिस नहीं आ पाऊंगा, डॉक्टर का अपॉइंटमेंट है",
    "So basically the plan is, um, we finish the design by Friday, then, uh, we start building next week, "
    "and I mean if everything goes well we can launch by the end of the month, but, you know, "
    "we should keep some buffer for testing and bug fixes because last time we, uh, we ran out of time.",
    "send the invoice to Rahul, sorry, to Priya by end of day",
]

repo = sys.argv[1]
for dev in sys.argv[2:]:
    t = time.perf_counter()
    try:
        cleaner = Cleaner(SmartCleaner(models.local_path(repo), dev))
    except Exception as e:
        print(f"{dev}: FAILED to load: {str(e)[:300]}", flush=True)
        continue
    print(f"\n=== {repo} on {dev}: loaded in {time.perf_counter() - t:.1f}s", flush=True)
    cleaner.clean("um so hello there how are you doing", "smart")  # warm-up
    total = 0
    for s in SAMPLES:
        t = time.perf_counter()
        out = cleaner.clean(s, "smart")
        dt = time.perf_counter() - t
        total += dt
        print(f"[{dt:5.2f}s] {out}", flush=True)
    print(f"{dev}: total {total:.1f}s", flush=True)
