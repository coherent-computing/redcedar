# Quick Start

This guide walks you through installing the **Red Cedar** SDK, training a quantum machine learning model on your
own data, and using it to make predictions. It takes two calls.

## Prerequisites

- **Python 3.9 or later**
- **A Red Cedar server** to run the circuits: either one running on your own machine, or a hosted server with an
  API key (see [Connect](#connect))

Nothing quantum is installed on your machine by the SDK. The server builds and runs the circuits.

## Install

```bash
pip install redcedar
```

The only dependency is `requests`. Add `[plotting]` (`pip install "redcedar[plotting]"`) if you want matplotlib for
the plots in the examples.

## Connect

**A server on your own machine.** If you have the Red Cedar engine installed, start its server from the
`red-cedar` folder:

```bash
./run_server.sh          # Linux / Mac
run_server.bat           # Windows
```

It listens on port 8002, and the SDK looks for it at `http://127.0.0.1:8002` by default. The server only accepts
requests with the key that `run_server.sh` sets (the line `export BACKEND_API_KEY=...`), so give the SDK the same
key, or set it once in your shell as `REDCEDAR_API_KEY`:

```python
import redcedar

client = redcedar.connect(api_key="<the BACKEND_API_KEY value from run_server.sh>")
print(client.status())          # {'ok': True, 'server_version': '0.93', 'sdk_version': '0.93.0'}
```

Without the key, `status()` and the dataset list still work, but training, analysis and the other calls are
refused.

**A hosted server.** Pass its URL and your API key, or set them once in your shell as `REDCEDAR_URL` and
`REDCEDAR_API_KEY`:

```python
client = redcedar.connect(url="https://<hosted-server-url>", api_key="your-api-key")
```

A hosted server only accepts requests with a valid API key. Contact your Cascade Quantum representative to get
one, or to get access to the Red Cedar user interface. If you already have access to the user interface, you
can create your own key there, under **API Keys**.

## Your Data

A CSV file with one row per example. The input features come first; the **last column is the answer** you want
the model to learn: a class label (or a number, for regression). A header row is optional, but recommended:
with one, Red Cedar knows your columns by name.

```
radius,texture,perimeter,area,smoothness,diagnosis
17.99,10.38,122.8,1001.0,0.1184,M
13.54,14.36,87.46,566.3,0.09779,B
...
```

## Step 1: Train a Model

```python
model = client.training.run("my_data.csv", verbose=True)

print(model["train_id"])
```

`training.run()` uploads the file, trains a model on the server, and waits until it's done. With `verbose=True`
it shows the progress, and the test accuracy after each layer of the model.

By default, 80% of your rows train the model and the other 20% are held back to test it, so the accuracy you
see is measured on rows the model has never seen. Once you're happy with the result, you can train on all of
your rows with `test_size=0`.

The `train_id` names your trained model. You use it for everything that follows.

Every part of the model and its training can be set: the number of qubits and layers, the circuit structure,
how the data is prepared, the number of iterations, the seed, the backend. Pass them as `settings=`, a dict or a
`.json` / `.toml` file:

```python
model = client.training.run("my_data.csv", settings={"num_qubits": 6, "max_layers": 3, "seed": 123})
```

The [Settings](user_guide.md#settings) section of the User Guide lists every setting and how to set it.

## Step 2: Make Predictions

```python
predictions = client.inference.run(model["train_id"], "new_data.csv")

for row in predictions["predictions"][:5]:
    print(row["prediction"], row["probabilities"])
```

`inference.run()` gives the model new rows and returns one result per row: the predicted label and the
probability of each class. The new file has the same input columns as the training file; the answer column is
usually missing, since the answer is what you want (if it's there, you get the accuracy too). To save the
results next to your data, add `output="predictions.csv"`.

That's all it takes: a file, a trained model, and predictions.

## One Step Further: Which Features Matter?

Red Cedar can show which of your input features the model relies on to make its decisions:

```python
explanation = client.explainable.run(model["train_id"], verbose=True)

for q in explanation["qubit_map"]:
    print(f"{q['feature_name']}: {q['importance']:.1%}")
```

Each data qubit of the model encodes one input feature, and `importance` measures how much that qubit influences
the prediction. See [Explainable AI](user_guide.md#explainable-ai) in the User Guide.

## What Next

There is much more you can control. The [User Guide](user_guide.md) covers it all; some places to start:

- **[Regression](user_guide.md#classification-or-regression):** predict a number instead of a class, with
  `task="regression"`.
- **[Settings](user_guide.md#settings):** every training option (qubits, layers, the circuit structure, data
  preparation, training, execution) and how to set it.
- **[Evaluate a model](user_guide.md#evaluating-a-model):** the accuracy per class, for any layer, or on a
  different backend.
- **[Analyze a dataset](user_guide.md#dataset-analysis)** before training: how many dimensions carry signal, and
  how many qubits the model needs.
- **[Run on quantum hardware](user_guide.md#running-on-quantum-hardware):** train on a simulator, run on a
  quantum computer.
- **[The command line](user_guide.md#command-line):** `redcedar train my_data.csv`, without writing any Python.

The [Examples](examples.md) have complete notebooks for each of these.

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
