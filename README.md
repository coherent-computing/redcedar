# Red Cedar

Python client for the Red Cedar quantum machine learning server. Run dataset analysis, model training, inference, and explainable AI from notebooks or scripts without installing the quantum engine locally.

## Install

```bash
pip install -e .
```

## Quick Start

```python
import redcedar

# Connect (reads REDCEDAR_URL and REDCEDAR_API_KEY from environment)
client = redcedar.connect()

# List datasets
datasets = client.datasets.list()

# Run PCA analysis
pca = client.analysis.pca("wdbc", verbose=True)

# Run Mutual Information analysis
mi = client.analysis.mi("wdbc", verbose=True)

# Run Quantum Resource Estimation
qre = client.analysis.qre("wdbc", verbose=True)

# Train a model
result = client.training.run("wdbc", verbose=True)

# Run inference
inference = client.inference.run(result['train_id'], verbose=True)

# Explainable AI
explanation = client.explainable.run(result['train_id'], verbose=True)
```

## Configuration

Set environment variables or pass to `connect()`:

```bash
export REDCEDAR_URL="http://localhost:8000"       # server URL
export REDCEDAR_API_KEY="your-api-key"            # API key
```

Or connect directly:

```python
client = redcedar.connect(url="http://localhost:8002", api_key="your-key")
```

## Settings Overrides

Override any training parameter using a dict, JSON file, or TOML file:

```python
# Dict — only specified keys override server defaults
client.training.run("wdbc", settings={"num_qubits": 6, "copula": False})

# JSON file
client.training.run("wdbc", settings="my_settings.json")

# TOML file
client.training.run("wdbc", settings="my_settings.toml")
```

## What You Can Do

| Function | Description |
|----------|-------------|
| `client.datasets.list()` | Browse available datasets |
| `client.analysis.pca(id)` | Principal Component Analysis |
| `client.analysis.mi(id)` | Mutual Information feature ranking |
| `client.analysis.qre(id)` | Quantum Resource Estimation |
| `client.training.run(id)` | Train a quantum ML model |
| `client.inference.run(train_id)` | Classify test data |
| `client.inference.models()` | List trained models |
| `client.explainable.run(train_id)` | Feature importance analysis |

All long-running operations stream progress via SSE. Use `verbose=True` for inline progress or `on_progress=callback` for custom handling.

## Requirements

- Python 3.9+
- `requests` (installed automatically)
- No quantum computing dependencies required
