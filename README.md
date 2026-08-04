# Red Cedar Python Client

Python client for the Red Cedar quantum machine learning server. Run dataset analysis, model training, inference, and explainable AI from notebooks or scripts — no quantum computing libraries required on your machine.

## Install

```bash
pip install -e .
```

The only dependency is `requests`.

## Connecting to the Server

```python
import redcedar

client = redcedar.connect(url="http://localhost:8002", api_key="your-api-key")
print(client.status())   # {'ok': True}
```

You can also set environment variables instead of passing arguments:

```bash
export REDCEDAR_URL="http://localhost:8002"
export REDCEDAR_API_KEY="your-api-key"
```

Then just call `redcedar.connect()` with no arguments.

If both are provided, explicit arguments take priority over environment variables. If neither is set, the client defaults to `http://localhost:8000` with no API key.

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

The `id` is what you pass to analysis and training functions (e.g., `"wdbc"`, `"iris"`, `"diabetes"`).

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

Mutual Information analysis. Ranks features by how strongly they predict the class label.

```python
mi = client.analysis.mi("wdbc", verbose=True)
print(mi['total_mi'])               # 1.3392
print(mi['thresholds']['90'])       # 17 (features for 90% of total MI)
for f in mi['ranked_features'][:5]:
    print(f['feature_name'], f['mi_score'])
```

Returns a dict with: `dataset_name`, `samples`, `features`, `classes`, `total_mi`, `ranked_features` (list of dicts with `rank`, `feature_index`, `feature_name`, `mi_score`, `mi_percent`), `cumulative_mi` (list), `thresholds`, `elapsed_seconds`.

### `client.analysis.qre(dataset_id)`

Quantum Resource Estimation. Estimates how many qubits the model needs for this dataset.

```python
qre = client.analysis.qre("wdbc", verbose=True)
print(qre['estimatedQubits'])       # 16
print(qre['standardDeviation'])     # 1.4
```

Returns a dict with: `dataset_name`, `estimatedQubits`, `standardDeviation`, `samples`, `features`, `classes`, `plotData`, `elapsed_seconds`.

---

## Training

### `client.training.run(dataset_id, settings=None, verbose=False, on_progress=None)`

Train a quantum ML model on a dataset.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `dataset_id` | str | required | Dataset ID from the catalog |
| `settings` | dict, str, or None | `None` | Override default training parameters (see below) |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

```python
result = client.training.run("wdbc", verbose=True, settings={
    "num_qubits": 4,
    "min_layers": 1,
    "max_layers": 1,
})

train_id = result['train_id']
print(result['elapsed_seconds'])
```

Returns a dict with: `train_id`, `total_layers`, `elapsed_seconds`, `data_loading_seconds`.

The `train_id` is used for inference and explainable AI calls.

### Settings overrides

Settings can be a Python dict, a path to a `.json` file, or a path to a `.toml` file. Only the keys you include are changed; everything else keeps the server default.

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
| `all_nodes` | `False` | Optimize all nodes (ignores `num_iterations`) |
| `node_order_type` | `"sequential"` | Order in which optimizer visits nodes |
| `bits_type` | `"importance"` | How features are mapped to qubits |
| `num_pca` | auto | Number of PCA components (None = auto) |

---

## Inference

### `client.inference.run(train_id, verbose=False, on_progress=None)`

Run the trained model on held-out test data and get accuracy results.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | Training job ID from `training.run()` |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

```python
inference = client.inference.run(train_id, verbose=True)

print(inference['overall_accuracy'])    # 0.754
print(inference['overall_loss'])        # 0.2822
print(inference['test_samples'])        # 114

for cls in inference['per_class']:
    print(f"Class {cls['class']}: {cls['accuracy']:.1%} ({cls['samples']} samples)")
```

Returns a dict with: `train_id`, `layer`, `overall_accuracy`, `overall_loss`, `test_samples`, `num_classes`, `per_class` (list of dicts with `class`, `accuracy`, `loss`, `samples`), `data_loading_seconds`, `inference_seconds`, `elapsed_seconds`.

### `client.inference.models()`

List all trained models currently on the server.

```python
models = client.inference.models()
for m in models['models']:
    print(m['train_id'], m.get('dataset_display_name'), m.get('num_qubits'), m.get('layers'))
```

Returns a dict with a `models` list. Each model entry includes `train_id`, `dataset`, `dataset_display_name`, `dataset_name`, `num_qubits`, `layers` (list of completed layer numbers), `max_layer`, `node_count`, `node_order`, `timestamp`, `non_defaults`, `training_params`.

---

## Explainable AI

### `client.explainable.run(train_id, verbose=False, on_progress=None)`

Analyze which input features drive the model's classification decisions.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `train_id` | str | required | Training job ID from `training.run()` |
| `verbose` | bool | `False` | Print progress to stdout |
| `on_progress` | callable | `None` | Called with `(percent, message)` on each update |

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

- **`verbose=True`** prints a single updating line to stdout: `[  30%] Training layer 1...`
- **`on_progress`** receives `(percent, message)` on each update, for custom progress handling (GUI bars, logging, etc.)

These can be used together.

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
- **`RuntimeError`** — a job failed during execution. The error message from the server is included.

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
inference = client.inference.run(train_id, verbose=True)
print(f"Accuracy: {inference['overall_accuracy']:.1%}")

# Explain
explanation = client.explainable.run(train_id, verbose=True)
for q in explanation['qubit_map']:
    print(f"  {q['feature_name']}: {q['importance']*100:.1f}%")
```

See `redcedar-examples/01_full_pipeline.ipynb` for a complete walkthrough with output.

---

## Current Limitations

- **Classification only.** The server currently supports classification tasks. Regression support is planned.

- **One job at a time.** The server processes jobs sequentially. If you submit a request while another job is running, yours is queued and starts when the current job finishes.

- **Datasets are server-managed.** You can select from the server's dataset catalog but cannot yet upload custom datasets or plug in your own data loaders through the SDK. The web UI supports CSV uploads; SDK support for this is planned.

- **OpenML datasets only.** The SDK currently requests all datasets via OpenML. Datasets in the server catalog that are stored as local files (not sourced from OpenML) may not load correctly through the SDK. The standard catalog datasets (wdbc, iris, diabetes, wine, mnist) all work.

- **No job cancellation from the SDK.** Training jobs can be stopped from the web UI, but the SDK does not currently expose a stop function.

## Planned Enhancements

- Regression as a task type (in addition to classification)
- Custom dataset uploads and user-provided data loaders
- Job cancellation from the SDK
- Access to additional server-side customization (preprocessing pipelines, circuit structure options)

## Requirements

- Python 3.9+
- `requests` (installed automatically)
- A running Red Cedar server to connect to
