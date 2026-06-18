"""Advance the tournament state for the round-by-round live loop.

The model reads data/state.json each run. This CLI edits it, then you rerun the
model to refresh the published rankings.

    python update_round.py eliminate "South Africa" "Czechia"   # group-stage exits
    python update_round.py knockout R32 bracket.json            # lock a knockout round
    python update_round.py reset                                # back to pre-tournament

`bracket.json` is a list of pairs, e.g. [["Argentina","Uzbekistan"], ...], with
16 pairs for R32, 8 for R16, 4 for QF, 2 for SF, 1 for F.

Typical loop: group stage -> eliminate the teams that go out -> when the bracket
is set, switch to knockout R32 -> after each round, post the next bracket. Rerun
`python model.py` after every change.
"""
import json
import os
import sys

HERE = os.path.dirname(__file__)
STATE = os.path.join(HERE, "..", "data", "state.json")
VALID = {"R32": 16, "R16": 8, "QF": 4, "SF": 2, "F": 1}


def _read():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"stage": "group", "eliminated": []}


def _write(state):
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    print(f"state.json -> stage={state['stage']}, "
          f"{len(state.get('eliminated', []))} eliminated, "
          f"{len(state.get('bracket', []))} pairs. Now rerun: python model.py")


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd = argv[0]
    state = _read()
    if cmd == "reset":
        _write({"stage": "group", "eliminated": []})
    elif cmd == "eliminate":
        state.setdefault("stage", "group")
        state.setdefault("eliminated", [])
        for name in argv[1:]:
            if name not in state["eliminated"]:
                state["eliminated"].append(name)
        _write(state)
    elif cmd == "knockout":
        stage = argv[1].upper()
        if stage not in VALID:
            sys.exit(f"stage must be one of {list(VALID)}")
        with open(argv[2], encoding="utf-8") as fh:
            bracket = json.load(fh)
        if len(bracket) != VALID[stage]:
            sys.exit(f"{stage} needs {VALID[stage]} pairs, got {len(bracket)}")
        _write({"stage": stage, "bracket": bracket})
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
