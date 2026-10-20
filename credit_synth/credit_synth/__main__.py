from __future__ import annotations

import argparse
from pathlib import Path
import sys
from .schema import DEFAULT_MIX
from .simulator import bootstrap
from .train import train
from .generate import generate
from .evaluate import evaluate
from .validate import validate_dataset


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic SME credit data: CVAE + conditional VGAE")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("bootstrap", help="Create an explicitly fictional training source")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rows", type=int, default=4000)
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("train", help="Train on profiles.csv and optional company_links.csv")
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--graph-epochs", type=int, default=80)
    p.add_argument("--skip-graph", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("generate", help="Generate new companies and linked credit tables")
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--companies", type=int, default=1000)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--as-of", default="2026-10-19", help="Fixed ISO date, used for all demo timelines")
    p.add_argument("--mix", type=float, nargs=3, default=DEFAULT_MIX,
                   metavar=("HEALTHY", "BORDERLINE", "DISTRESSED"))
    p.add_argument("--no-fixtures", action="store_true", help="Omit the five deterministic integration examples")
    for name in ["validate", "evaluate"]:
        p = sub.add_parser(name)
        p.add_argument("--data", type=Path, required=True)
        if name == "evaluate":
            p.add_argument("--model", type=Path, required=True)
            p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("demo", help="Bootstrap, train, generate, validate and evaluate")
    p.add_argument("--out", type=Path, default=Path("demo"))
    p.add_argument("--train-rows", type=int, default=2400)
    p.add_argument("--companies", type=int, default=500)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--graph-epochs", type=int, default=80)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--as-of", default="2026-10-19")
    args = parser.parse_args(argv)
    if hasattr(args, "seed") and args.seed < 0:
        parser.error("seed must be nonnegative")
    try:
        if args.command == "bootstrap":
            bootstrap(args.out, args.rows, args.seed)
            print(f"Created fictional source: {args.out}")
        elif args.command == "train":
            train(args.data, args.out, args.epochs, args.graph_epochs, args.seed, args.skip_graph)
            print(f"Saved model checkpoints: {args.out}")
        elif args.command == "generate":
            report = generate(args.model, args.out, args.companies, args.seed, args.as_of,
                              args.mix, not args.no_fixtures)
            print(f"Generated {report['rows']['companies']} companies; {report['checks_passed']} checks passed: {args.out}")
        elif args.command == "validate":
            report = validate_dataset(args.data)
            print(f"VALID: {report['checks_passed']} checks passed")
        elif args.command == "evaluate":
            evaluate(args.model, args.data, args.seed)
            print(f"Quality diagnostics: {args.data / 'quality.json'}")
        elif args.command == "demo":
            bootstrap(args.out / "reference", args.train_rows, args.seed)
            train(args.out / "reference", args.out / "model", args.epochs, args.graph_epochs, args.seed)
            report = generate(args.out / "model", args.out / "generated", args.companies,
                              args.seed + 1000, args.as_of)
            evaluate(args.out / "model", args.out / "generated", args.seed)
            print(f"Demo complete: {report['rows']['companies']} companies, {report['checks_passed']} checks passed")
            print(f"Data: {args.out / 'generated'}")
        return 0
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
