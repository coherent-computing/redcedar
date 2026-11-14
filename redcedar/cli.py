"""The redcedar command: train, evaluate, predict and explain from the command line.

    redcedar train my_data.csv --qubits 6 --seed 123
    redcedar train my_data.csv --settings my_settings.toml --set num_pca=8 --save results
    redcedar train my_data.csv --model random_forest --trees 500
    redcedar evaluate <train_id>
    redcedar predict <train_id> new_data.csv -o predictions.csv
    redcedar explain <train_id>
    redcedar models
    redcedar status

The server comes from --url / --api-key, or REDCEDAR_URL / REDCEDAR_API_KEY; --local runs the
Red Cedar code in this process instead (no server).

Settings for a training come, in this order, each over the one before: the server's defaults,
the --settings file, --set key=value, then the named flags (--qubits, --layers, ...). The data
file is always the train command's argument: a settings file holds settings only, so the same
file can be used for any data.
"""

import argparse
import json
import os
import sys

import requests

from .client import connect


def parse_value(text):
    """A --set value: JSON when it parses (numbers, true/false, null, lists, quoted strings),
    otherwise the text itself (e.g. --set backend=statevector)."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def apply_set(settings, assignment):
    """Apply one --set key=value to the settings dict. A dotted key sets a value inside a
    nested setting, e.g. forest_options.n_estimators=500 sets
    settings["forest_options"]["n_estimators"] and keeps the other forest options."""
    if "=" not in assignment:
        raise ValueError(f"--set needs key=value, got {assignment!r}")
    key, value = assignment.split("=", 1)
    parts = key.strip().split(".")
    target = settings
    for part in parts[:-1]:
        target = target.setdefault(part, {})
        if not isinstance(target, dict):
            raise ValueError(f"--set {key}: {part} is not a group of settings")
    target[parts[-1]] = parse_value(value.strip())


def training_settings(args):
    """The settings sent with a training: the --settings file, then --set, then the named
    flags (see the module docstring)."""
    from .settings import load_settings
    settings = dict(load_settings(args.settings))
    for assignment in args.set or []:
        apply_set(settings, assignment)
    if args.model is not None:
        settings["model"] = args.model
    if args.trees is not None:
        settings.setdefault("forest_options", {})["n_estimators"] = args.trees
    if args.qubits is not None:
        settings["num_qubits"] = args.qubits
    if args.layers is not None:
        settings["max_layers"] = args.layers
        settings.setdefault("min_layers", 1)
    if args.min_layers is not None:
        settings["min_layers"] = args.min_layers
    if args.nodes is not None:
        if args.nodes == "all":
            settings["all_nodes"] = True
        else:
            settings["all_nodes"] = False
            settings["num_iterations"] = int(args.nodes)
    if args.batch_size is not None:
        settings["batch_size"] = args.batch_size
    if args.parallelize:
        settings["parallelize"] = True
    if args.seed is not None:
        settings["seed"] = args.seed
    if args.backend:
        settings["backend"] = args.backend
    return settings


def print_training(result):
    """The test results of a training: per layer for the quantum model, overall for a forest."""
    if result.get("model") == "random_forest":
        if result.get("test_samples"):
            if result.get("task") == "regression":
                print(f"Random forest: mean absolute error {result['mean_absolute_error']:.4f}, "
                      f"R2 {result['r2']:.4f} on {result['test_samples']} test rows")
            else:
                print(f"Random forest: test accuracy {result['test_accuracy']:.1%} "
                      f"on {result['test_samples']} test rows")
        else:
            print("Random forest: trained on all rows (no test set)")
    for layer, v in result.get("validation", {}).items():
        if v.get("test_accuracy") is not None:
            print(f"Layer {layer}: test accuracy {v['test_accuracy']:.1%}")
        elif v.get("test_loss") is not None:
            print(f"Layer {layer}: test loss {v['test_loss']:.4f}")
        else:
            print(f"Layer {layer}: trained on all rows (no test set)")
    print(f"train_id: {result['train_id']}")


def save_training(folder, data, settings, result):
    """Write a training's result to <folder>/<train_id>.json: the data and the settings sent,
    and the whole result (summary, training curves and test results per layer). The model
    itself stays on the server, with its full settings."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{result['train_id']}.json")
    with open(path, "w") as f:
        json.dump({"data": data, "settings": settings, "result": result}, f, indent=2, default=str)
    return path


def print_explanation(result, top):
    """The features a model relies on, most important first."""
    if "feature_importances" in result:   # a random forest: one importance per column
        rows = [(f["feature_name"], f["importance"]) for f in result["feature_importances"][:top]]
        print("Random forest feature importances (share of the trees' error reduction):")
    else:                                 # the quantum model: one importance per data qubit
        qubits = sorted(result.get("qubit_map") or [], key=lambda q: -(q.get("importance") or 0))
        rows = [(f"q{q['qubit']}: {q['feature_name']}", q.get("importance") or 0) for q in qubits[:top]]
        print("Importance of each data qubit (the feature it holds):")
    for name, value in rows:
        print(f"  {name:<32} {value:.1%}")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="redcedar", description="Red Cedar quantum machine learning",
        epilog="Run 'redcedar <command> --help' for a command's options.")
    p.add_argument("--url", help="server URL (default: REDCEDAR_URL or http://127.0.0.1:8002)")
    p.add_argument("--api-key", help="API key (default: REDCEDAR_API_KEY)")
    p.add_argument("--local", action="store_true",
                   help="call the Red Cedar core directly in this process instead of a server "
                        "(redcedar_core, installed with pip install -e, or the red-cedar folder "
                        "in REDCEDAR_CORE_PATH)")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress output")
    p.add_argument("--log", action="store_true", help="also print the server's log for the job")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser(
        "train", help="train a model on a CSV file or catalog dataset",
        description="Train a model. Settings: the server's defaults, then --settings FILE, then "
                    "--set KEY=VALUE, then the named flags, each over the one before.",
        epilog="Examples:\n"
               "  redcedar train my_data.csv --qubits 6 --layers 2 --seed 123\n"
               "  redcedar train my_data.csv --settings my_settings.toml --set num_pca=8\n"
               "  redcedar train my_data.csv --model random_forest --trees 500 --set forest_options.min_samples_leaf=3\n"
               "  redcedar train my_data.csv --task regression --save results",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    t.add_argument("data", help="CSV file path or catalog dataset ID")
    t.add_argument("--settings", help="settings file (.json or .toml); settings only, not the data")
    t.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="any setting, repeatable; a dotted key sets a value in a group "
                        "(forest_options.n_estimators=500); values are read as JSON when they "
                        "can be (8, 0.5, true, null), otherwise as text")
    t.add_argument("--model", choices=["quantum", "random_forest"],
                   help="the learner (default: quantum)")
    t.add_argument("--trees", type=int, help="random forest: number of trees (forest_options.n_estimators)")
    t.add_argument("--qubits", type=int, help="num_qubits")
    t.add_argument("--layers", type=int, metavar="N", help="train up to N layers (max_layers; from layer 1 unless --min-layers)")
    t.add_argument("--min-layers", type=int, metavar="N", help="first layer to train (min_layers)")
    t.add_argument("--nodes", metavar="N|all",
                   help="nodes to optimize per layer (num_iterations), or 'all' (all_nodes)")
    t.add_argument("--batch-size", type=int, help="training rows per parameter update (default: all)")
    t.add_argument("--parallelize", action="store_true", help="evaluate circuits in parallel (joblib)")
    t.add_argument("--seed", type=int, help="seed, to make the run repeatable")
    t.add_argument("--backend", help="where the circuits run (default: statevector)")
    t.add_argument("--task", choices=["classification", "regression"],
                   help="default: detected from the target column")
    t.add_argument("--test-size", type=float,
                   help="held-out test rows, a fraction or a count (0 = train on all rows)")
    t.add_argument("--save", metavar="DIR",
                   help="also write the result (settings, training curves, test results) to "
                        "DIR/<train_id>.json")

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

    x = sub.add_parser("explain", help="the features a model relies on (explainable AI)")
    x.add_argument("train_id")
    x.add_argument("--top", type=int, default=10, help="how many features to show (default: 10)")
    x.add_argument("--backend")

    sub.add_parser("models", help="list recently trained models")
    sub.add_parser("status", help="check the server and show the server and SDK versions")

    args = p.parse_args(argv)
    if args.command == "train" and args.nodes is not None and args.nodes != "all" and not args.nodes.isdigit():
        p.error("--nodes takes a number or 'all'")
    client = connect(url=args.url, api_key=args.api_key, local=args.local or False)
    verbose = False if args.quiet else "log" if args.log else True
    run_settings = {"backend": args.backend} if getattr(args, "backend", None) else None

    try:
        if args.command == "train":
            settings = training_settings(args)
            test_size = args.test_size
            if test_size is not None and test_size >= 1:
                test_size = int(test_size)
            result = client.training.run(args.data, settings=settings, verbose=verbose,
                                         task=args.task, test_size=test_size)
            print_training(result)
            if args.save:
                print(f"Result saved to {save_training(args.save, args.data, settings, result)}")

        elif args.command == "evaluate":
            report = client.training.evaluate(args.train_id, layer=args.layer, verbose=verbose,
                                              settings=run_settings)
            if report.get("task") == "regression":
                loss = f", loss {report['overall_loss']:.4f}" if report.get("overall_loss") is not None else ""
                r2 = f", R2 {report['r2']:.4f}" if report.get("r2") is not None else ""
                print(f"Mean absolute error {report['mean_absolute_error']:.4f}{loss}{r2} "
                      f"on {report['test_samples']} test rows")
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

        elif args.command == "explain":
            result = client.explainable.run(args.train_id, verbose=verbose, settings=run_settings)
            print_explanation(result, args.top)

        elif args.command == "models":
            for m in client.inference.models()["models"]:
                kind = ("random forest" if m.get("model") == "random_forest"
                        else f"{m.get('num_qubits')} qubits, layers {m.get('layers')}")
                print(m["train_id"], m.get("dataset_display_name") or m.get("dataset", ""),
                      m.get("task", ""), kind)

        elif args.command == "status":
            s = client.status()
            print(f"Server: {client.url or 'none (local mode: the Red Cedar core in this process)'}")
            print(f"Server version: {s['server_version'] or 'unknown'}")
            print(f"SDK version: {s['sdk_version']}")
            if not s["ok"]:
                print(f"Error: {s['error']}", file=sys.stderr)
                return 1

    except (RuntimeError, ValueError, requests.HTTPError, requests.ConnectionError, FileNotFoundError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
