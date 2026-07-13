# Cascade Quantum SDK

Python client for the Cascade Quantum ML server. Run dataset analysis, model training, inference, and explainable AI from notebooks or scripts without installing the quantum engine locally.

## Install

```bash
pip install -e .
```

## Quick Start

```python
import cascade_quantum as cq

# Connect (reads CQ_URL and CQ_API_KEY from environment)
client = cq.connect()

# List datasets
datasets = client.datasets.list()

# Run PCA
pca = client.analysis.pca("wdbc", verbose=True)

# Train a model
result = client.training.run("wdbc", verbose=True)

# Run inference
inference = client.inference.run(result['train_id'], verbose=True)

# Explain
explanation = client.explainable.run(result['train_id'], verbose=True)
```

## Configuration

Set environment variables or pass to `connect()`:

```bash
export CQ_URL="http://localhost:8000"       # server URL
export CQ_API_KEY="your-api-key"            # API key
```

## Settings Overrides

Pass training settings as a dict, JSON file, or TOML file:

```python
# Dict
client.training.run("wdbc", settings={"num_qubits": 6, "copula": False})

# JSON file
client.training.run("wdbc", settings="my_settings.json")

# TOML file
client.training.run("wdbc", settings="my_settings.toml")
```

Only specified keys override server defaults.
