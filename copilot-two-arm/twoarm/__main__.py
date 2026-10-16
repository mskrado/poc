"""CLI: python -m twoarm {prepare,start,finish,grade,readout}."""
import argparse, json, sys
from pathlib import Path
from . import arms, log, readout

RESULTS = Path("results/runs.csv")


def main(argv=None):
    p = argparse.ArgumentParser(prog="twoarm")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--arm", choices="AB", required=True)
    s.add_argument("--condition", choices=["ai", "no_ai"], required=True); s.add_argument("--workspace", required=True)
    s.add_argument("--who", required=True); s.add_argument("--tool", default="")
    s.add_argument("--forecast-pct", type=float, required=True, help="before: AI changes my time by X%% (-30 = faster)")
    f = sub.add_parser("finish"); f.add_argument("--workspace", required=True)
    f.add_argument("--felt-pct", type=float, required=True, help="after: AI changed my time by X%%")
    f.add_argument("--results", default=str(RESULTS)); f.add_argument("--notes", default="")
    g = sub.add_parser("grade"); g.add_argument("--arm", choices="AB", required=True); g.add_argument("--workspace", required=True)
    r = sub.add_parser("readout"); r.add_argument("--results", default=str(RESULTS)); r.add_argument("--out", default="results")
    a = p.parse_args(argv)
    if a.cmd == "start":
        st = log.start(a.arm, a.condition, Path(a.workspace), a.who, a.tool, a.forecast_pct)
        print(f"run {st['run_id']} started, workspace {a.workspace}. Read SPEC.md / ISSUE.md there.")
    elif a.cmd == "finish":
        print(json.dumps(log.finish(Path(a.workspace), a.felt_pct, Path(a.results), a.notes), indent=2))
    elif a.cmd == "grade":
        print("%d/%d" % arms.grade(a.arm, Path(a.workspace)))
    else:
        rows = readout.load(Path(a.results)); out = Path(a.out)
        (out / "readout.md").write_text(readout.markdown(rows))
        readout.chart(rows, out / "charts" / "readout.png")
        print(f"wrote {out/'readout.md'} and {out/'charts'/'readout.png'}")


if __name__ == "__main__":
    sys.exit(main())
