"""The redcedar command: train, evaluate and predict from the command line.

    redcedar train my_data.csv --qubits 6 --seed 123
    redcedar evaluate <train_id>
    redcedar predict <train_id> new_data.csv -o predictions.csv
    redcedar models
    redcedar status

The server comes from --url / --api-key, or REDCEDAR_URL / REDCEDAR_API_KEY.
"""

import argparse
import sys

import requests

from .client import connect


def main(argv=None):
    p = argparse.ArgumentParser(prog="redcedar", description="Red Cedar quantum machine learning")
    p.add_argument("--url", help="server URL (default: REDCEDAR_URL or http://localhost:8002)")
    p.add_argument("--api-key", help="API key (default: REDCEDAR_API_KEY)")
    p.add_argument("--local", metavar="PATH",
                   help="run the server inside this process, from this red-cedar folder")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress output")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("train", help="train a model on a CSV file or catalog dataset")
    t.add_argument("data", help="CSV file path or catalog dataset ID")
    t.add_argument("--settings", help="settings file (.json or .toml)")
    t.add_argument("--qubits", type=int, help="num_qubits")
    t.add_argument("--layers", type=int, help="train layers 1 to N (min_layers=1, max_layers=N)")
    t.add_argument("--seed", type=int, help="seed for the initial parameters")
    t.add_argument("--backend", help="where the circuits run (default: statevector)")
    t.add_argument("--task", choices=["classification", "regression"],
                   help="default: detected from the target column")
    t.add_argument("--test-size", type=float,
                   help="held-out test rows, a fraction or a count (0 = train on all rows)")

    e = sub.add_parser("evaluate", help="score a model on its held-out test rows")
    e.add_argument("train_id")
    e.add_argument("--layer", type=int)
    e.add_argument("--backend")

    r = sub.add_parser("predict", help="predictions for new rows")
    r.add_argument("train_id")
    r.add_argument("data", help="CSV file with the new rows")
    r.add_argument("-o", "--output", help="write the rows and predictions to this CSV file")
    r.add_argument("--layer", type=int)
    r.add_argument("--backend")

    sub.add_parser("models", help="list recently trained models")
    sub.add_parser("status", help="check the server and show the server and SDK versions")

    args = p.parse_args(argv)
    client = connect(url=args.url, api_key=args.api_key, local=args.local or False)
    verbose = not args.quiet
    run_settings = {"backend": args.backend} if getattr(args, "backend", None) else None

    try:
        if args.command == "train":
            from .settings import load_settings
            settings = load_settings(args.settings)
            if args.qubits is not None:
                settings["num_qubits"] = args.qubits
            if args.layers is not None:
                settings["min_layers"], settings["max_layers"] = 1, args.layers
            if args.seed is not None:
                settings["seed"] = args.seed
            if args.backend:
                settings["backend"] = args.backend
            test_size = args.test_size
            if test_size is not None and test_size >= 1:
                test_size = int(test_size)
            result = client.training.run(args.data, settings=settings, verbose=verbose,
                                         task=args.task, test_size=test_size)
            for layer, v in result.get("validation", {}).items():
                if v.get("test_accuracy") is not None:
                    print(f"Layer {layer}: test accuracy {v['test_accuracy']:.1%}")
                elif v.get("test_loss") is not None:
                    print(f"Layer {layer}: test loss {v['test_loss']:.4f}")
                else:
                    print(f"Layer {layer}: trained on all rows (no test set)")
            print(f"train_id: {result['train_id']}")

        elif args.command == "evaluate":
            report = client.training.evaluate(args.train_id, layer=args.layer, verbose=verbose,
                                              settings=run_settings)
            if report.get("task") == "regression":
                print(f"Mean absolute error {report['mean_absolute_error']:.4f}, "
                      f"loss {report['overall_loss']:.4f} on {report['test_samples']} test rows")
            else:
                print(f"Accuracy {report['overall_accuracy']:.1%} on {report['test_samples']} test rows")
            for c in report["per_class"]:
                print(f"  class {c['class']}: {c['accuracy']:.1%} ({c['samples']} rows)")

        elif args.command == "predict":
            result = client.inference.run(args.train_id, args.data, layer=args.layer,
                                          output=args.output, verbose=verbose,
                                          settings=run_settings)
            if args.output:
                print(f"{result['rows']} predictions written to {args.output}")
            else:
                for p_row in result["predictions"]:
                    print(p_row["prediction"])
            if "accuracy" in result:
                print(f"Accuracy on these rows: {result['accuracy']:.1%}")
            if "mean_absolute_error" in result:
                print(f"Mean absolute error on these rows: {result['mean_absolute_error']:.4f}")

        elif args.command == "models":
            for m in client.inference.models()["models"]:
                print(m["train_id"], m.get("dataset_display_name") or m.get("dataset", ""),
                      m.get("task", ""), f"{m.get('num_qubits')} qubits", f"layers {m.get('layers')}")

        elif args.command == "status":
            s = client.status()
            print(f"Server: {client.url}")
            print(f"Server version: {s['server_version'] or 'unknown'}")
            print(f"SDK version: {s['sdk_version']}")
            if not s["ok"]:
                print(f"Error: {s['error']}", file=sys.stderr)
                return 1

    except (RuntimeError, requests.HTTPError, requests.ConnectionError, FileNotFoundError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
