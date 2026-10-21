"""Extract what the video draws from the explorer snapshot (data/explorer) into video/study.json.

  python3 video/prepare_data.py

- episodes: every scored episode of every split run, in the landing's order (runs.json order), as
  {cover, mode, scores}; the same set the landing's lanes draw.
- showcase: one episode's per-request scores from the monitor's two prompts.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "explorer")
SHOWCASE = ("sweep-c6-attack", 2)  # C6, attack: the prompts split mid-episode and meet above 60 at the end


def load(*parts):
    with open(os.path.join(DATA, *parts)) as f:
        return json.load(f)


episodes = []
for run in load("runs.json"):
    if not run["split"] or run["error"]:
        continue
    for ep in load("runs", f"{run['id']}.json")["episodes"]:
        episodes.append({"cover": ep["condition"], "mode": ep["mode"], "scores": [s or 0 for s in ep["scores"]]})

run_id, n = SHOWCASE
ep = load("runs", run_id, "episodes", f"{n}.json")
showcase = {
    "run": run_id, "n": n, "cover": ep["condition"], "mode": ep["mode"],
    "holistic": [a["scores"]["holistic"] for a in ep["actions"]],
    "narrow": [a["scores"]["narrow"] for a in ep["actions"]],
    "outcomes": [a["outcome"] for a in ep["actions"]],
}

with open(os.path.join(HERE, "study.json"), "w") as f:
    json.dump({"episodes": episodes, "showcase": showcase}, f)
covers = sorted({e["cover"] for e in episodes})
print(f"{len(episodes)} episodes over {len(covers)} covers; showcase {run_id}/{n}: {len(showcase['holistic'])} requests")
