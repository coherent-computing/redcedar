# Red Cedar Python Client

Python client for the Red Cedar quantum machine learning server. Run dataset analysis, model training, inference, and explainable AI from notebooks or scripts — no quantum computing libraries required on your machine.

Documentation: [coherent-computing.github.io/redcedar](https://coherent-computing.github.io/redcedar/) (source in [`doc/`](doc/)).

## Install

From a clone of this repository:

```bash
pip install -e .
```

The only dependency is `requests`. The example notebooks also plot with matplotlib, which you can install with the client: `pip install -e ".[plotting]"`.

## Connecting to the Server

```python
import redcedar

client = redcedar.connect(url="http://localhost:8002", api_key="your-api-key")
print(client.status())   # {'ok': True, 'server_version': '0.93', 'sdk_version': '0.2.0'}
```

You can also set environment variables instead of passing arguments:

```bash
export REDCEDAR_URL="http://localhost:8002"
export REDCEDAR_API_KEY="your-api-key"
```

Then just call `redcedar.connect()` with no arguments.

If both are provided, explicit arguments take priority over environment variables. If neither is set, the client defaults to `http://localhost:8002` (the port `run_server` uses) with no API key.

**Hosted server.** Use the URL and API key you were given, for example `redcedar.connect(url="https://<hosted-server-url>", api_key="your-api-key")`. A hosted server accepts only requests with a valid API key. Contact your Cascade Quantum representative to get one, or to get access to the Red Cedar user interface. If you already have access to the user interface, you can create your own key there, under **API Keys** (one key at a time; a new key replaces the old one).

**Local mode (development).** With the Red Cedar source, `redcedar.connect(local="path/to/red-cedar")` starts the server inside your own Python process, on a free local port, and connects to it. Everything works as with a separate server, and a debugger stops at breakpoints in the Red Cedar code. It needs the Red Cedar dependencies in your environment; the folder can also come from the `REDCEDAR_CORE_PATH` environment variable (`connect(local=True)`). Don't run it next to another server started from the same folder: they share its job database.

---

## Datasets

### `client.datasets.list()`

Returns a list of all datasets available on the server.

```python
datasets = client.datasets.list()
for ds in datasets:
    print(ds['id'], ds['name'], ds.get('rows'), ds.get('classes'))
```

Each entry is a dict. The most useful fields: `id`, `name`, `description`, `category`, `source`, `rows`, `columns`, `classes`, `available`. Some datasets include additional fields like `recommended` or `dataset_name`.

The `id` is what you pass to analysis and training functions (e.g., `"wdbc"`, `"iris"`, `"diabetes"`, `"clinical_trial_v1"`).

### `client.datasets.upload(file_path)`

Uploads a CSV file and returns a dataset ID to pass to `training.run()` or `inference.run()`. The last column is the class label; a header row is optional. You can also pass the file path to those calls directly, which uploads it each time; upload once when you use the same file several times.

```python
dataset_id = client.datasets.upload("my_data.csv")
result = client.training.run(dataset_id, settings={"num_qubits": 4})
```

---

## Analysis

Three analysis functions help you understand a dataset before training. All three accept the same arguments:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `dataset_id` | str | required | Dataset ID from the catalog |
| `verbose` | bool | `False` | Print a progress bar to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each progress update |

### `client.analysis.pca(dataset_id)`

Principal Component Analysis. Shows how many independent dimensions carry real signal in the data.

```python
pca = client.analysis.pca("wdbc", verbose=True)
print(pca['features'])              # 30
print(pca['thresholds']['90'])      # 7  (components for 90% variance)
print(pca['thresholds']['95'])      # 10
```

Returns a dict with: `dataset_name`, `features`, `samples`, `n_components`, `variance_ratios` (list), `cumulative_variance` (list), `thresholds` (dict mapping percentage strings to component counts), `elapsed_seconds`.

### `client.analysis.mi(dataset_id)`

Mutual Information analysis. The data is first reduced with PCA, as training does, and each principal component (`PC1`, `PC2`, ...) is ranked by how strongly it predicts the class label.

```python
mi = client.analysis.mi("wdbc", verbose=True)
print(mi['total_mi'])               # 1.3392
print(mi['thresholds']['90'])       # 17 (components for 90% of total MI)
for f in mi['ranked_features'][:5]:
    print(f['feature_name'], f['mi_score'])
```

Returns a dict with: `dataset_name`, `samples`, `features`, `classes`, `total_mi`, `ranked_features` (list of dicts with `rank`, `feature_index`, `feature_name`, `mi_score`, `mi_percent`), `cumulative_mi` (list), `thresholds`, `elapsed_seconds`.

### `client.analysis.qre(dataset_id)`

Quantum Resource Estimation. Estimates how many qubits the model needs for this dataset: the data is encoded with more and more qubits until no two samples with different classes look the same (so 100% accuracy is possible in principle), plus the qubits needed for the class label. The result is averaged over 10 random train/test splits.

```python
qre = client.analysis.qre("wdbc", verbose=True)
print(qre['estimatedQubits'])       # 16
print(qre['standardDeviation'])     # 1.4
```

Returns a dict with: `dataset_name`, `estimatedQubits`, `standardDeviation`, `samples`, `features`, `classes`, `plotData`, `warning_message` (or `None`), `elapsed_seconds`. `plotData` has one entry per number of data qubits, with the highest possible accuracy on the training and test data (`Number of Qubits`, `Train`, `Train sem`, `Test`, `Test sem`, and the overlap measures).

The analysis functions accept catalog IDs and IDs from `datasets.upload()`.

---

## Training

### `client.training.run(dataset_id, settings=None, verbose=False, on_progress=None, train_size=None, test_size=None, class_range=None, task=None)`

Train a quantum ML model on a dataset.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `dataset_id` | str | required | A CSV file path (uploaded first), a dataset ID from the catalog, an ID from `datasets.upload()`, or an OpenML dataset name |
| `settings` | dict, str, or None | `None` | Override default training parameters (see below) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |
| `train_size` | float or int | dataset default | Training set size (fraction or number of samples) |
| `test_size` | float or int | dataset default | Test set size (fraction or number of samples); `0` trains on all rows, with no test set |
| `class_range` | list | all classes | Classes to train on, e.g. `["0", "1"]` (catalog datasets only) |
| `task` | str | detected | `"classification"` or `"regression"`. Detected from a CSV file's target column: text or whole numbers are classes, fractional numbers regression. Pass `task="regression"` for a whole-number target that is a quantity |

```python
result = client.training.run("wdbc", verbose=True, settings={
    "num_qubits": 4,
    "min_layers": 1,
    "max_layers": 1,
})

train_id = result['train_id']
print(result['elapsed_seconds'])
```

Returns a dict with: `train_id`, `total_layers`, `elapsed_seconds`, `data_loading_seconds`, plus:

- `history`: the training curves, by layer. Each layer has a list of `{iteration, train_loss, train_accuracy}`.
- `validation`: the test results at the end of each layer, by layer: `test_loss`, `test_accuracy`, `test_accuracy_per_class`, `test_loss_per_class`, `num_parameters` and timings.

```python
import matplotlib.pyplot as plt

for layer, points in result['history'].items():
    plt.plot([p['train_loss'] for p in points], label=f"layer {layer}")
plt.xlabel("Iteration"); plt.ylabel("Training loss"); plt.legend()

for layer, v in result['validation'].items():
    print(f"Layer {layer}: test accuracy {v['test_accuracy']:.1%}")
```

The `train_id` is used for evaluation, inference and explainable AI calls.

### `client.training.evaluate(train_id, layer=None, verbose=False, on_progress=None, settings=None)`

Scores a trained model on the test rows held back from its training run (by default 20% of the rows) and gives accuracy results. You pass no data: the server rebuilds the same split from the model's saved settings. For a prediction for each row of new data, use `inference.run()`.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | Training job ID from `training.run()` |
| `layer` | int | highest layer | Which layer of the trained model to test |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |
| `settings` | dict | `None` | Run-time overrides; only `backend` and `parallelize` are used, e.g. to test on a different backend |

```python
report = client.training.evaluate(train_id, verbose=True)

print(report['overall_accuracy'])    # 0.754
print(report['overall_loss'])        # 0.2822
print(report['test_samples'])        # 114

for cls in report['per_class']:
    print(f"Class {cls['class']}: {cls['accuracy']:.1%} ({cls['samples']} samples)")
```

Returns a dict with: `train_id`, `layer`, `task`, `overall_accuracy`, `overall_loss`, `test_samples`, `num_classes`, `per_class` (list of dicts with `class`, `accuracy`, `loss`, `samples`), `data_loading_seconds`, `inference_seconds`, `elapsed_seconds`. For a regression model, `overall_accuracy` is `None`, `per_class` is empty, and `mean_absolute_error` gives the average error in the target's units. At most 400 test rows are scored. A model trained with `test_size=0` has no test rows: the call stops with an error.

### `client.training.analyze(train_id, layer=None, verbose=False, on_progress=None)`

Replays the parameters saved during training on the test data, giving the test accuracy and loss over the course of training. `layer` defaults to the last layer.

```python
replay = client.training.analyze(train_id)
plt.plot(replay['accuracy_history'])
plt.xlabel("Checkpoint"); plt.ylabel("Test accuracy")
```

Returns a dict with: `train_id`, `layer`, `num_checkpoints`, `accuracy_history`, `loss_history`, `final_accuracy`, `final_loss`, `data_loading_seconds`, `replay_seconds`, `elapsed_seconds`.

### `client.training.status(train_id)` and `client.training.stop(train_id)`

`status()` returns `train_id`, `status` (`running`, `completed`, `failed` or `stopped`), `progress`, `summary` and `error_message`. A job still waiting in the queue has no status yet (404).

`stop()` asks the server to stop a running job; finished layers are kept. Since `training.run()` waits until the job ends, call `stop()` from another thread, notebook or process. The waiting `training.run()` then raises `RuntimeError("Training stopped")`.

### Settings overrides

Settings can be a Python dict, a path to a `.json` file, or a path to a `.toml` file. Only the keys you include are changed; everything else keeps the server default. Keys the server doesn't recognize are ignored without an error, so check the spelling against the table below.

```python
# Dict
client.training.run("wdbc", settings={"num_qubits": 8, "backend": "statevector"})

# JSON file
client.training.run("wdbc", settings="my_settings.json")

# TOML file (requires Python 3.11+ or the tomli package)
client.training.run("wdbc", settings="my_settings.toml")
```

Commonly used settings keys:

| Key | Default | Description |
|-----|---------|-------------|
| `num_qubits` | 4 | Number of qubits in the quantum circuit |
| `min_layers` | 1 | First layer in the layer sweep |
| `max_layers` | 2 | Last layer in the layer sweep |
| `chain_layers` | `True` | Start each layer from the parameters the previous layer found (`False` = each layer starts from scratch) |
| `backend` | `"statevector"` | Execution backend (`"statevector"`, `"ionq-simulator"`, etc.) |
| `num_iterations` | all nodes | Number of optimizer iterations per layer |
| `scale` | `True` | Whether to scale features before PCA |
| `dimension_reduction` | `"pca"` | Dimensionality reduction method (`"pca"` or `"none"`) |
| `copula` | `True` | Apply copula transform to training data |
| `normalize` | `True` | Normalize data to [0, 1] range |
| `circuit_structure` | `"bipartite"` | Circuit structure type |
| `ansatz_type` | `"euler_and_heisenberg"` | Gate ansatz for parameterized circuits |
| `activation_type` | `"discretize"` | Activation function type |
| `parallelize` | `False` | Parallelize circuit execution |
| `batch_size` | `None` | Training samples per batch (`None` = all training data) |
| `all_nodes` | `False` | Optimize all nodes (ignores `num_iterations`) |
| `node_order_type` | `"sequential"` | Order in which optimizer visits nodes |
| `op_direction` | `"backward"` | Order of the ansatz operators over the data qubits (`"backward"` or `"forward"`) |
| `seed` | `None` | Seed for the initial parameters, so runs can be repeated (`None` = random start) |
| `bits_type` | `"importance"` | How features are mapped to qubits |
| `num_pca` | auto | Number of PCA components (None = auto) |

---

## Inference

### `client.inference.run(train_id, data, layer=None, output=None, verbose=False, on_progress=None, settings=None)`

Runs a trained model on new rows and returns a prediction for each row.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | Training job ID from `training.run()` |
| `data` | str | required | A CSV file path (uploaded first), or an ID from `datasets.upload()` |
| `layer` | int | highest layer | Which layer of the trained model to use |
| `output` | str | `None` | Also write the input rows plus the predictions to this CSV file (needs `data` as a file path) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |
| `settings` | dict | `None` | Run-time overrides; only `backend` and `parallelize` are used |

```python
predictions = client.inference.run(train_id, "new_data.csv", output="predictions.csv")

for row in predictions['predictions'][:5]:
    print(row['prediction'], row['probabilities'])   # B {'B': 0.94, 'M': 0.06}
```

Returns a dict with: `train_id`, `layer`, `task`, `rows`, `predictions` (one dict per row, in file order), `data_loading_seconds`, `inference_seconds`, `elapsed_seconds`. Classification: each row has `prediction` (the label) and `probabilities` (class label to probability), and the result has `accuracy` when the rows include the target column. Regression: each row has `prediction` (a number), and the result has `mean_absolute_error` when the rows include the target column. The `output` file has the input columns plus `prediction` and, for classification, one `probability_<class>` column per class.

The new file's columns are matched to the model's inputs:

- **By name** when the new file and the training file both have a header row. Columns can be in any order, and columns the model doesn't use (an ID, say) are ignored. A missing feature column stops with an error naming it.
- **By position** otherwise: the training features in training order, optionally followed by the target column. Any other number of columns stops with an error.

A header row is a first row that is all text. The training data must still be on the server: the preprocessing is rebuilt from it.

### `client.inference.models()`

List the six most recently trained models on the server. Older models can still be used by `train_id` until the server deletes them (see Current Limitations).

```python
models = client.inference.models()
for m in models['models']:
    print(m['train_id'], m.get('dataset_display_name'), m.get('num_qubits'), m.get('layers'))
```

Returns a dict with a `models` list. Each model entry includes `train_id`, `dataset`, `dataset_display_name`, `dataset_name`, `num_qubits`, `layers` (list of completed layer numbers), `max_layer`, `node_count`, `node_order`, `timestamp`, `non_defaults`, `training_params`.

---

## Explainable AI

### `client.explainable.run(train_id, verbose=False, on_progress=None, settings=None)`

Analyze which input features drive the model's classification decisions. It uses the highest layer of the trained model. Each data qubit is mapped back to the input feature it encodes, and `importance` measures how much that qubit influences the prediction.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | Training job ID from `training.run()` |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |
| `settings` | dict | `None` | Run-time overrides; only `backend` and `parallelize` are used |

```python
explanation = client.explainable.run(train_id, verbose=True)

print(explanation['num_qubits'])
print(explanation['num_class_qubits'])

for q in explanation['qubit_map']:
    print(f"Qubit {q['qubit']}: {q['feature_name']} (importance {q['importance']*100:.1f}%)")

for qid, val in explanation['convergence'].items():
    print(f"Class qubit {qid}: convergence = {val:.4f}")
```

Returns a dict with: `train_id`, `layer`, `dataset_name`, `num_qubits`, `num_class_qubits`, `class_range`, `qubit_map` (list of dicts with `qubit`, `feature_index`, `feature_name`, `bits`, `bit`, `importance`), `convergence` (dict mapping class qubit IDs to convergence values), `distributions`, `feature_indices`, `data_loading_seconds`, `elapsed_seconds`.

---

## Progress Monitoring

All long-running operations accept `verbose` and `on_progress`:

- **`verbose=True`** prints a single updating line to stdout, `[  30%] Layer 1/2`, plus the server's log lines for the job (training output, per-layer results).
- **`on_progress`** receives `(percent, message)` on each update, for custom progress handling (GUI bars, logging, etc.)

These can be used together.

If the server is busy with another job, yours waits in the queue and starts when that job finishes. The call simply waits; with `verbose=True` it prints `Waiting in queue...` until the job starts.

```python
def my_callback(percent, message):
    log.info(f"{percent}% — {message}")

result = client.training.run("wdbc", verbose=True, on_progress=my_callback)
```

---

## Error Handling

The client raises standard Python exceptions:

- **`requests.ConnectionError`** — cannot reach the server. Use `client.status()` to check before starting work.
- **`requests.HTTPError`** — server returned an error (e.g., 404 if a training job doesn't exist, 401 for bad API key).
- **`RuntimeError`** — a job failed during execution (the error message from the server is included), or it was stopped with `training.stop()` (`"Training stopped"`).

```python
try:
    result = client.training.run("wdbc", verbose=True)
except RuntimeError as e:
    print(f"Training failed: {e}")
```

---

## Full Pipeline Example

```python
import redcedar

client = redcedar.connect()

# Explore the dataset
pca = client.analysis.pca("wdbc", verbose=True)
mi = client.analysis.mi("wdbc", verbose=True)
qre = client.analysis.qre("wdbc", verbose=True)

# Train
result = client.training.run("wdbc", verbose=True, settings={
    "num_qubits": 4,
    "min_layers": 1,
    "max_layers": 2,
})
train_id = result['train_id']

# Evaluate
report = client.training.evaluate(train_id, verbose=True)
print(f"Accuracy: {report['overall_accuracy']:.1%}")

# Predict
predictions = client.inference.run(train_id, "new_data.csv", output="predictions.csv")

# Explain
explanation = client.explainable.run(train_id, verbose=True)
for q in explanation['qubit_map']:
    print(f"  {q['feature_name']}: {q['importance']*100:.1f}%")
```

## Command Line

Installing the client also installs the `redcedar` command (`python -m redcedar` does the same, for when pip's scripts folder isn't on the PATH). It uses `REDCEDAR_URL` and `REDCEDAR_API_KEY`, or `--url` and `--api-key`.

```bash
redcedar train my_data.csv --qubits 6 --layers 2 --seed 123    # prints the train_id
redcedar evaluate <train_id>
redcedar predict <train_id> new_data.csv -o predictions.csv
redcedar models
redcedar status                                                # server and SDK versions
```

`train` also takes `--settings my_settings.toml` (any setting), `--backend`, `--task regression` and `--test-size 0` (train on all rows); `evaluate` and `predict` take `--layer` and `--backend`. Run `redcedar <command> --help` for the details.

## Example Notebooks

The [redcedar-examples](https://github.com/coherent-computing/redcedar-examples) repository has notebooks that use this client:

| Notebook | Shows |
|----------|-------|
| `01_quick_start.ipynb` | The basic workflow: train, plot the training curves, test, explain |
| `02_dataset_analysis.ipynb` | PCA, mutual information and qubit estimates, comparing datasets, analyzing your own CSV |
| `03_training_settings.ipynb` | Training settings, one section per setting |
| `04_training_in_depth.ipynb` | Layers and chaining, test accuracy during training, choosing the data, reusing models, stopping a job |

---

## Current Limitations

- **Explainable AI is for classification models.** Regression models train, evaluate (loss and mean absolute error) and predict (a number per row); explainable AI refuses them.

- **One job at a time.** The server processes jobs sequentially. If you submit a request while another job is running, yours is queued and starts when the current job finishes.

- **CSV uploads only.** You can train on catalog datasets and on CSV files you upload, but you can't yet plug in your own data loaders.

- **Only training can be stopped.** Inference, explainable AI and the training replay can't be stopped once they start.

- **Trained models are not kept forever.** When it starts, the server deletes trained models older than 24 hours, and all but the 30 most recent.

- **No test set with `test_size=0`.** The layer results' test values are `None`, and `training.evaluate()` and `training.analyze()` stop with an error; measure such a model with `inference.run()` on rows that include the target column.

## Planned Enhancements

- User-provided data loaders
- Access to additional server-side customization (preprocessing pipelines, circuit structure options)

## Requirements

- Python 3.9+
- `requests` (installed automatically)
- A running Red Cedar server to connect to
