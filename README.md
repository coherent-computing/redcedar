# redcedar

Python client for the Red Cedar quantum machine learning server. Train quantum models on your own data, test them, make predictions and see which features drive them, from a notebook, a script or the command line. The circuits run on the server, so no quantum computing libraries are needed on your machine.

## Install

```bash
pip install redcedar
```

The only dependency is `requests`. The example notebooks also plot with matplotlib: `pip install "redcedar[plotting]"`.

## Quick Example

```python
import redcedar

client = redcedar.connect(url="https://<server-url>", api_key="your-api-key")
print(client.status())   # {'ok': True, 'server_version': '0.93', 'sdk_version': '0.93.0'}

# Train on a CSV file (last column = class label) or a catalog dataset
result = client.training.run("my_data.csv", verbose=True, settings={"num_qubits": 4, "max_layers": 2})
train_id = result['train_id']

# Test on the rows held back from training
report = client.training.evaluate(train_id)
print(f"Accuracy: {report['overall_accuracy']:.1%}")

# Predict new rows, and save them with the predictions
predictions = client.inference.run(train_id, "new_data.csv", output="predictions.csv")

# Which input features drive the model
explanation = client.explainable.run(train_id)
for q in explanation['qubit_map']:
    print(f"{q['feature_name']}: {q['importance']*100:.1f}%")
```

`REDCEDAR_URL` and `REDCEDAR_API_KEY` can be set in the environment instead, and then `redcedar.connect()` needs no arguments.

## Features

- **Training** on your own CSV files or on datasets in the server's catalog, for classification and regression, with settings passed as a dict or a JSON or TOML file
- **Evaluation** on held-out test rows, with accuracy and loss overall and per class
- **Predictions** for each row of a new file, with class probabilities, written to a CSV file if you like
- **Explainable AI**: which input features the model relies on
- **Dataset analysis** before training: PCA, mutual information, and an estimate of the qubits a dataset needs
- **Simulators and quantum hardware**: the server runs the circuits on Qiskit and CUDA-Q simulators (including multi-GPU) and on IonQ and IQM simulators and quantum computers
- **Progress reporting** for long jobs, which wait in the server's queue when it's busy
- **Command line**: `redcedar train`, `evaluate`, `predict`, `models` and `status`, without writing any Python

## Getting Access

The client connects to a Red Cedar server. A hosted server accepts only requests with a valid API key: contact your Cascade Quantum representative to get one. If you have access to the Red Cedar user interface, you can create your own key there, under **API Keys**.

## Documentation

- **[Quick Start](https://coherent-computing.github.io/redcedar/quick_start/)**: install, connect, train a model and make predictions
- **[User Guide](https://coherent-computing.github.io/redcedar/user_guide/)**: every call and setting, the command line, and the current limitations
- **[Full Documentation](https://coherent-computing.github.io/redcedar/)**: also examples, release notes and known issues

## Source

[github.com/coherent-computing/redcedar](https://github.com/coherent-computing/redcedar). To install from a clone:

```bash
git clone https://github.com/coherent-computing/redcedar.git
cd redcedar
pip install -e .
```

## License

See [LICENSE](https://github.com/coherent-computing/redcedar/blob/main/LICENSE).
