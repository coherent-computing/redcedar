# User Guide

This guide is the complete reference for the **redcedar** Python SDK: every call, its arguments and what it
returns, the settings, and the command line. For a first walkthrough, start with the
[Quick Start](quick_start.md).

## How Red Cedar Works

A Red Cedar model is a parameterized quantum circuit that learns to map your input features to an answer. The
SDK sends your data and settings to a Red Cedar server; the server prepares the data, builds the circuits, runs
them on a simulator or a quantum computer, and trains the parameters. Results come back to the SDK as plain
Python values (dicts and lists).

The work has three steps, and the SDK groups its calls the same way:

| Step | Call | What it does |
|------|------|--------------|
| Train | `training.run()` | Trains a model on your data. |
| Evaluate (optional) | `training.evaluate()` | Scores the model on the rows held back from its own training run: how good is it? |
| Use | `inference.run()` | Makes predictions on new rows you supply. |

`training` holds everything about building a model and judging it; `inference` holds using it. Alongside these
are `datasets`, `analysis` (understanding a dataset before training) and `explainable` (what the model relies
on).

Long-running calls wait until the server has finished and then return the result. The server runs one job at a
time; if it is busy, your job waits in a queue and starts when the job before it finishes.

## Installation

```bash
pip install redcedar
```

The only dependency is `requests`. The example notebooks also plot with matplotlib:
`pip install "redcedar[plotting]"`.

Until the package is published on PyPI, install it from a clone of the repository (also the way to get the
notebooks, or to read the source):

```bash
git clone https://github.com/coherent-computing/redcedar.git
cd redcedar
pip install -e .
```

## Connecting to a Server

### A Server on Your Own Machine

If you have the Red Cedar engine installed, start its server from the `red-cedar` folder with `./run_server.sh`
(Linux, Mac) or `run_server.bat` (Windows). It listens on port 8002, and the SDK connects to
`http://127.0.0.1:8002` by default. The server only accepts requests with the key that the script sets (the line
`export BACKEND_API_KEY=...` in `run_server.sh`, `set BACKEND_API_KEY=...` in `run_server.bat`). Pass the same
key to `connect()`, or set it once as `REDCEDAR_API_KEY`:

```python
import redcedar

client = redcedar.connect(api_key="<the BACKEND_API_KEY value from run_server.sh>")
print(client.status())   # {'ok': True, 'server_version': '0.93', 'sdk_version': '0.93.0'}
```

Without the key, `status()` and `datasets.list()` still work, but training, analysis, inference and explainable
AI are refused (`422`, no key; `403`, a wrong key). This key belongs to the server itself. A hosted server uses
your personal API key instead (next section).

`status()` also tells you which versions you are using: the server's version (`client.server_version` gives it
on its own) and the SDK's. The SDK's version follows the server's (SDK 0.93.x goes with server 0.93).

In `REDCEDAR_URL`, use `127.0.0.1` rather than `localhost` for a server on your own machine. On Windows,
`localhost` is tried first as IPv6 (`::1`), which the server doesn't listen on, and every request then waits
about 2 seconds.

### A Hosted Server

Pass the URL of the hosted server and your API key:

```python
client = redcedar.connect(url="https://<hosted-server-url>", api_key="your-api-key")
```

Or set environment variables once, and call `redcedar.connect()` with no arguments:

```bash
export REDCEDAR_URL="https://<hosted-server-url>"
export REDCEDAR_API_KEY="your-api-key"
```

Explicit arguments take priority over environment variables. A hosted server only accepts requests with a valid
API key; without one, every call fails with `401` (no key or an unknown key) or `403` (a key without access).

**Getting a key.** Contact your Cascade Quantum representative to get an API key, or to get access to the Red
Cedar user interface. If you already have access to the user interface, you can create your own key there,
under **API Keys**. Keep the key private: it acts as you. You have one key at a time; a new key replaces the
old one, which then stops working.

### Local Mode, for Development

With the Red Cedar source and its dependencies in your Python environment, the SDK can call the Red Cedar code
directly, with no server. Install the source once, from the `red-cedar` folder:

```bash
pip install -e .
```

Then connect in local mode:

```python
client = redcedar.connect(local=True)
```

Every SDK call then runs the same function the server runs for it, in your own Python process and thread: no
server, no port, no HTTP. Results are the same as through a server, and a debugger steps from the SDK call
straight into the Red Cedar code. Without the install, pass the folder instead (`connect(local="path/to/red-cedar")`,
or set `REDCEDAR_CORE_PATH`).

Local mode uses the datasets, trained models and job records of that `red-cedar` folder, the same ones a server
started from it uses: a model trained through the server can be evaluated locally, and the other way round.
Ctrl+C stops a local training run, as `training.stop()` does; the layers that finished are kept.

## Data

### Your Own Data

Red Cedar trains on tables: one row per example, input features first, and the **last column is the target**,
the answer the model learns. A CSV file is the usual way to provide one.

- **Header row:** optional. A first row counts as a header when any of its cells is text. With a header, Red
  Cedar knows your columns by name, which `inference.run()` uses to match new files and explainable AI uses to
  name features. Without one, columns are known by position only.
- **One caveat:** a file without a header whose last column holds text labels (such as `M`/`B`) has text in its
  first row and would be read as having a header. Give such files a header row.
- **Features** are numbers. Red Cedar scales, normalizes and compresses them as part of training (see
  [Data preparation](#data-preparation) under Settings).

Pass the path of a CSV file wherever a dataset is expected:

```python
model = client.training.run("my_data.csv")
```

The file is uploaded each time. To upload once and reuse it, use `datasets.upload()`, which returns a dataset
ID:

```python
dataset_id = client.datasets.upload("my_data.csv")
model = client.training.run(dataset_id, settings={"num_qubits": 6})
```

### The Dataset Catalog

The server also has a catalog of ready-to-use datasets, such as `"wdbc"`, `"iris"` and `"diabetes"`.

```python
for ds in client.datasets.list():
    print(ds["id"], ds["name"], ds.get("rows"), ds.get("classes"))
```

Each entry is a dict. The most useful fields: `id`, `name`, `description`, `category`, `source`, `rows`,
`columns`, `classes`, `available`. The `id` is what you pass to the analysis and training calls.

## Training

### `client.training.run(data, settings=None, verbose=False, on_progress=None, train_size=None, test_size=None, class_range=None, task=None)`

Trains a model and waits until training ends.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `data` | str | required | A CSV file path, a dataset ID from `datasets.upload()`, or a catalog ID |
| `settings` | dict or str | `None` | Settings to change, as a dict or a `.json` / `.toml` file path (see [Settings](#settings)) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |
| `train_size` | float or int | `0.8` | Training set size, as a fraction or a number of rows |
| `test_size` | float or int | `0.2` | Test set size, as a fraction or a number of rows; `0` trains on all rows |
| `class_range` | list | all classes | Classes to train on, e.g. `["0", "1"]` (catalog datasets only) |
| `task` | str | detected | `"classification"` or `"regression"` (see [Classification or Regression](#classification-or-regression)) |

```python
model = client.training.run("my_data.csv", verbose=True, settings={
    "num_qubits": 6,
    "min_layers": 1,
    "max_layers": 2,
})

train_id = model["train_id"]
```

Returns a dict with `train_id`, `task`, `train_samples`, `test_samples`, `total_layers`, `elapsed_seconds`,
`data_loading_seconds`, plus:

- `history`: the training curves, by layer. Each layer has a list of `{iteration, train_loss, train_accuracy}`
  (no `train_accuracy` for regression).
- `validation`: the test results at the end of each layer, by layer: `test_loss`, `test_accuracy`,
  `test_accuracy_per_class`, `test_loss_per_class`, `num_parameters` and timings. Regression has `test_loss`
  only. With `test_size=0` the test values are `None`.

```python
import matplotlib.pyplot as plt

for layer, points in model["history"].items():
    plt.plot([p["train_loss"] for p in points], label=f"layer {layer}")
plt.xlabel("Iteration"); plt.ylabel("Training loss"); plt.legend()

for layer, v in model["validation"].items():
    print(f"Layer {layer}: test accuracy {v['test_accuracy']:.1%}")
```

### Train and Test Rows

Every training run splits the data: by default 80% of the rows train the model and 20% are held back for
testing. The split is stratified by class (each class keeps its share in both parts) and is the same every
time for the same data. The held-out rows are what training tests at the end of each layer, and what
`training.evaluate()` scores.

Holding rows back is what makes the test accuracy honest: accuracy measured on the training rows overstates
how the model does on new data. The usual pattern when you want the final model to learn from everything:

1. Train with the default split and check the test results.
2. If they're good, train again with the same settings and `test_size=0`, and use that model for predictions.

With `test_size=0` there is no held-out score: the test values in the layer results are `None`, and
`training.evaluate()` and `training.analyze()` stop with an error saying the model has no test rows. To measure
such a model, make predictions on rows that include the target column.

### Layers

A model is trained one layer at a time, from `min_layers` to `max_layers`. Each layer adds a set of parameters
to the circuit; by default (`chain_layers=True`) a layer starts from the parameters the layer before it found.
Every finished layer is saved, and later calls take `layer=` to pick one (the highest by default).

### Classification or Regression

The task is decided when the model is trained, and saved with it. Without `task=`, Red Cedar detects it from a
CSV file's target column: text labels or whole numbers mean **classification**, numbers with fractions mean
**regression** (catalog datasets are classification). A target of whole numbers that is really a quantity
(a count, a score, a price in whole units) needs `task="regression"`:

```python
model = client.training.run("prices.csv", task="regression", settings={"num_qubits": 6})
```

`task="classification"` on a target with fractional numbers stops with an error, as does `task="regression"` on
text labels.

A regression model predicts a number. The circuit encodes the target as a binary number on
`num_qubits_target` qubits (default 2, taken from `num_qubits`); the prediction is the average of that number
over the measured outcomes, scaled to the range of the training targets, so predictions stay between the
smallest and largest target seen in training. Its test result is a loss (`loss_type`, default
`"weighted_hamming"`); `training.evaluate()` and `inference.run()` also give the mean absolute error, in the
target's units. Explainable AI works with classification models only.

### `client.training.status(train_id)` and `client.training.stop(train_id)`

`status()` returns `train_id`, `status` (`running`, `completed`, `failed` or `stopped`), `progress`, `summary`
and `error_message`. A job still waiting in the queue has no status yet (404).

`stop()` asks the server to stop a running training job; finished layers are kept. Since `training.run()` waits
until the job ends, call `stop()` from another thread, notebook or process. The waiting `training.run()` then
raises `RuntimeError("Training stopped")`.

## Evaluating a Model

Training already reports the test accuracy after each layer. The calls in this section look at a trained model
again, later, in more detail.

### `client.training.evaluate(train_id, layer=None, settings=None, verbose=False, on_progress=None)`

Scores a trained model on the rows held back from its training run. You pass no data: the server rebuilds the
same split from the model's saved settings.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | The model, from `training.run()` |
| `layer` | int | highest layer | Which layer of the model to score |
| `settings` | dict | `None` | Execution settings only (`backend`, `parallelize`), e.g. to score on a different backend |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

```python
report = client.training.evaluate(train_id, verbose=True)

print(report["overall_accuracy"])
print(report["test_samples"])

for cls in report["per_class"]:
    print(f"Class {cls['class']}: {cls['accuracy']:.1%} ({cls['samples']} samples)")
```

Returns a dict with `train_id`, `layer`, `task`, `overall_accuracy`, `overall_loss`, `test_samples`,
`num_classes`, `per_class` (a list of dicts with `class`, `accuracy`, `loss`, `samples`), and timings. For a
regression model, `overall_accuracy` is `None`, `per_class` is empty, and `mean_absolute_error` gives the
average error in the target's units. It reports on the held-out rows as a whole; for a result per row, use
`inference.run()`. At most 400 held-out rows are scored.

### `client.training.analyze(train_id, layer=None, verbose=False, on_progress=None)`

Replays the parameters saved during training on the held-out rows, giving the test accuracy and loss over the
course of training. `layer` defaults to the highest layer.

```python
replay = client.training.analyze(train_id)
plt.plot(replay["accuracy_history"])
plt.xlabel("Checkpoint"); plt.ylabel("Test accuracy")
```

Returns a dict with `train_id`, `layer`, `num_checkpoints`, `accuracy_history`, `loss_history`,
`final_accuracy`, `final_loss`, and timings. Regression models have a loss history only.

## Predictions

### `client.inference.run(train_id, data, layer=None, output=None, settings=None, verbose=False, on_progress=None)`

Runs a trained model on new rows and returns one result per row.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | The model, from `training.run()` |
| `data` | str | required | A CSV file path, or a dataset ID from `datasets.upload()` |
| `layer` | int | highest layer | Which layer of the model to use |
| `output` | str | `None` | Also write the results to this CSV file |
| `settings` | dict | `None` | Execution settings only (`backend`, `parallelize`) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

```python
predictions = client.inference.run(train_id, "new_data.csv", output="predictions.csv")

for row in predictions["predictions"][:5]:
    print(row["prediction"], row["probabilities"])
```

Returns a dict with `train_id`, `layer`, `task`, `rows`, timings, and `predictions`, a list with one entry
per row, in the order of the file:

- **Classification:** `{"prediction": "M", "probabilities": {"M": 0.81, "B": 0.19}}`. The labels are the ones
  in the training data.
- **Regression:** `{"prediction": 152.3}`.

If the new rows also contain the target column, the result has an `accuracy` as well (regression: a
`mean_absolute_error`). The `output` file holds the input columns plus a `prediction` column and, for
classification, one `probability_<class>` column per class.

The new rows are prepared exactly as the training data was (scaling, compression, encoding), using the
training data, which must therefore still be on the server.

### Matching the Columns of a New File

The model has to pair each column of the new file with one of its inputs:

- **The file has a header row (a first row that is all text): columns are matched by name.** They can be in
  any order. Columns the model
  doesn't use (an ID, say) are ignored. A missing feature column stops with an error naming it. If the target
  column is present (under its training name), the accuracy is reported too.
- **No header row: columns are matched by position.** The columns must be the training features in training
  order, optionally followed by the target column. Any other number of columns stops with an error saying how
  many were expected.

A model trained on a file without a header knows its columns by position only, so its new files are matched by
position too.

### `client.inference.models()`

Lists the six most recently trained models on the server.

```python
for m in client.inference.models()["models"]:
    print(m["train_id"], m.get("dataset_display_name"), m.get("num_qubits"), m.get("layers"))
```

Each entry includes `train_id`, `dataset`, `dataset_display_name`, `num_qubits`, `layers` (the completed layer
numbers), `max_layer`, `node_order`, `timestamp`, `non_defaults` (the settings that differ from the defaults)
and `training_params`.

Trained models are not kept forever: see [Known Issues](known_issues.md) for how long a server keeps them.

## Explainable AI

### `client.explainable.run(train_id, settings=None, verbose=False, on_progress=None)`

Shows which input features drive the model's decisions. It uses the highest layer of the model. Each data qubit
is mapped back to the input feature it encodes, and `importance` measures how much that qubit influences the
prediction.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | The model, from `training.run()` |
| `settings` | dict | `None` | Execution settings only (`backend`, `parallelize`) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

```python
explanation = client.explainable.run(train_id, verbose=True)

for q in explanation["qubit_map"]:
    print(f"Qubit {q['qubit']}: {q['feature_name']} (importance {q['importance']:.1%})")

for qid, val in explanation["convergence"].items():
    print(f"Class qubit {qid}: convergence = {val:.4f}")
```

Returns a dict with `train_id`, `layer`, `dataset_name`, `num_qubits`, `num_class_qubits`, `class_range`,
`qubit_map` (a list of dicts with `qubit`, `feature_index`, `feature_name`, `bits`, `bit`, `importance`),
`convergence` (class qubit ID to convergence value), `distributions`, `feature_indices`, and timings.

## Dataset Analysis

Three calls help you understand a dataset before training. All three take a catalog ID or a dataset ID from
`datasets.upload()`, plus `verbose` and `on_progress`.

### `client.analysis.pca(dataset_id)`

Principal Component Analysis: how many independent dimensions carry real signal in the data.

```python
pca = client.analysis.pca("wdbc", verbose=True)
print(pca["features"])              # 30
print(pca["thresholds"]["90"])      # 7  (components for 90% of the variance)
```

Returns `dataset_name`, `features`, `samples`, `n_components`, `variance_ratios`, `cumulative_variance`,
`thresholds` (percentage to number of components), and timings.

### `client.analysis.mi(dataset_id)`

Mutual information. The data is first reduced with PCA, as training does, and each principal component (`PC1`,
`PC2`, ...) is ranked by how strongly it predicts the target.

```python
mi = client.analysis.mi("wdbc", verbose=True)
for f in mi["ranked_features"][:5]:
    print(f["feature_name"], f["mi_score"])
```

Returns `dataset_name`, `samples`, `features`, `classes`, `total_mi`, `ranked_features` (with `rank`,
`feature_index`, `feature_name`, `mi_score`, `mi_percent`), `cumulative_mi`, `thresholds`, and timings.

### `client.analysis.qre(dataset_id)`

Quantum resource estimation: how many qubits the model needs for this dataset. The data is encoded with more and
more qubits until no two rows with different classes look the same (so 100% accuracy is possible in principle),
plus the qubits needed for the class. The result is averaged over 10 random train/test splits.

```python
qre = client.analysis.qre("wdbc", verbose=True)
print(qre["estimatedQubits"], "+/-", qre["standardDeviation"])
```

Returns `dataset_name`, `estimatedQubits`, `standardDeviation`, `samples`, `features`, `classes`, `plotData`
(the highest possible train and test accuracy for each number of data qubits), `warning_message`, and timings.

## Settings

The calls above work with no settings at all. Every part of a model can also be set: the circuit and its
architecture, how the data is prepared, how training runs, and where the circuits execute.

### Passing Settings

Settings are a Python dict, or the path of a `.json` or `.toml` file. Only the keys you give change; everything
else keeps its default. Keys the server doesn't recognize are ignored without an error, so check the spelling
against the tables below.

```python
# Dict
client.training.run("my_data.csv", settings={"num_qubits": 8, "seed": 123})

# JSON file
client.training.run("my_data.csv", settings="my_settings.json")

# TOML file (Python 3.11+, or the tomli package)
client.training.run("my_data.csv", settings="my_settings.toml")
```

Every trained model saves its full settings, so any run can be repeated, or used as the starting point for the
next one.

`training.run()` takes all settings. `training.evaluate()`, `inference.run()` and `explainable.run()` use the
model's own settings, fixed when it was trained; their `settings=` changes only how the circuits are run
(`backend`, `parallelize`).

### Circuit and Architecture

| Key | Default | Description |
|-----|---------|-------------|
| `num_qubits` | 4 | Number of qubits in the circuit |
| `min_layers` | 1 | First layer in the layer sweep |
| `max_layers` | 2 | Last layer in the layer sweep |
| `chain_layers` | `True` | Start each layer from the parameters the layer before it found (`False`: each layer starts from scratch) |
| `circuit_structure` | `"bipartite"` | How the circuit's nodes are arranged |
| `ansatz_type` | `"euler_and_heisenberg"` | Gate ansatz of the parameterized circuit |
| `activation_type` | `"discretize"` | Activation function |
| `node_order_type` | `"sequential"` | Order in which the optimizer visits the nodes |
| `op_direction` | `"backward"` | Order of the ansatz operators over the data qubits (`"backward"` or `"forward"`) |

### Data Preparation

| Key | Default | Description |
|-----|---------|-------------|
| `normalize` | `True` | Normalize features to the [0, 1] range |
| `scale` | `True` | Scale features before dimension reduction |
| `copula` | `True` | Apply a copula transform to the training data |
| `dimension_reduction` | `"pca"` | Dimension reduction method (`"pca"` or `"none"`) |
| `num_pca` | auto | Number of PCA components |
| `bits_type` | `"importance"` | How features are mapped to qubits |

The split into training and test rows is set with the `train_size`, `test_size` and `class_range` arguments of
`training.run()`.

### Training

| Key | Default | Description |
|-----|---------|-------------|
| `num_iterations` | all nodes | Optimizer iterations per layer |
| `all_nodes` | `False` | Optimize all nodes (ignores `num_iterations`) |
| `batch_size` | `None` | Training rows per batch (`None`: all training rows) |
| `seed` | `None` | Seed for the initial parameters, so runs can be repeated (`None`: random start) |

### Regression

| Key | Default | Description |
|-----|---------|-------------|
| `num_qubits_target` | 2 | Qubits that encode the target, out of `num_qubits` |
| `loss_type` | `"weighted_hamming"` | Regression loss: `"weighted_hamming"`, `"hamming"` or `"huber"` |

### Execution

| Key | Default | Description |
|-----|---------|-------------|
| `backend` | `"statevector"` | Where the circuits run (see below) |
| `parallelize` | `False` | Run circuits in parallel |

## Running on Quantum Hardware

The `backend` setting chooses where circuits run. `"statevector"`, the default, is an exact simulator.
Other backends include `"ionq-simulator"`, IonQ quantum computers, and IQM quantum computers (`"iqm-garnet"`,
`"iqm-sirius"`, `"iqm-emerald"`). Which backends a server offers depends on how it is set up and which provider
accounts it has.

Hardware time is expensive, and training runs many circuits. A common pattern is to train on a simulator, then
evaluate the trained model, or make predictions, on hardware:

```python
model = client.training.run("my_data.csv", settings={"num_qubits": 6})

report = client.training.evaluate(model["train_id"], settings={"backend": "iqm-garnet"})
print(report["overall_accuracy"])
```

On hardware, results are estimated from shots and carry noise, so they differ somewhat from the exact
simulator.

## Command Line

Installing the SDK also installs the `redcedar` command, for training and predictions without writing Python.
It uses the same server connection (`REDCEDAR_URL`, `REDCEDAR_API_KEY`).

```bash
redcedar train my_data.csv --qubits 6 --layers 2 --seed 123
redcedar evaluate <train_id>
redcedar predict <train_id> new_data.csv -o predictions.csv
redcedar models
redcedar status
```

| Command | Same as | Flags |
|---------|---------|-------|
| `redcedar train` | `training.run()`; prints the test result per layer and the `train_id` | `--qubits`, `--layers N` (layers 1 to N), `--seed`, `--backend`, `--task`, `--test-size`, `--settings` |
| `redcedar evaluate` | `training.evaluate()` | `--layer`, `--backend` |
| `redcedar predict` | `inference.run()`; prints the predictions, or writes them with `-o` | `--layer`, `--backend`, `-o` |
| `redcedar models` | `inference.models()` | |
| `redcedar status` | `status()`; prints the server's URL and version and the SDK version | |

Any setting can come from a file: `--settings my_settings.toml`. Before the command, `--url` and `--api-key`
choose the server, `--local` uses [local mode](#local-mode-for-development), and `-q` turns
off the progress output. Run `redcedar <command> --help` for the details.

If the `redcedar` command isn't found (pip's scripts folder isn't on your PATH, which is common on Windows and
with conda), use `python -m redcedar` instead: `python -m redcedar train my_data.csv`.

## Progress and Errors

### Progress

All long-running calls take `verbose` and `on_progress`, which can be used together:

- **`verbose=True`** prints a single updating line, such as `[  30%] Layer 1/2`, plus the server's log lines for
  the job (training output, results per layer). While the job waits in the queue it prints `Waiting in
  queue...`.
- **`on_progress`** is called with `(percent, message)` on each update, for your own progress bars or logging.

```python
def my_callback(percent, message):
    log.info(f"{percent}% - {message}")

model = client.training.run("my_data.csv", verbose=True, on_progress=my_callback)
```

### Errors

The SDK raises standard Python exceptions:

- **`requests.ConnectionError`**: the server can't be reached. Use `client.status()` to check before starting
  work.
- **`requests.HTTPError`**: the server returned an error, such as 404 for a training job that doesn't exist or
  401 for a wrong API key.
- **`RuntimeError`**: a job failed (the server's error message is included), or it was stopped with
  `training.stop()` (`"Training stopped"`).

```python
try:
    model = client.training.run("my_data.csv", verbose=True)
except RuntimeError as e:
    print(f"Training failed: {e}")
```

## Limitations

Some things are not possible yet: explainable AI for regression models, your own data loaders and
custom circuit components (only CSV files and the catalog, and the built-in components chosen by settings),
stopping jobs other than training, and keeping models on a server indefinitely. The [Known Issues](known_issues.md) page lists these and other known problems.

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
