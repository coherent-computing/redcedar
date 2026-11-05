# About

## Red Cedar

**Red Cedar** is a quantum machine learning framework developed by Cascade Quantum. It lets you train models on
quantum simulators and quantum computers without having to master the low-level details of quantum technology.

Models are defined as hierarchical operators rather than circuits, which allows them to be synthesized
efficiently for any hardware backend. Training uses three techniques developed for Red Cedar:

- **Sub-net initialization**, which lets model training scale without running into barren plateaus.
- **Bit-bit encoding**, which encodes classical data efficiently.
- **Exact coordinate update**, which trains the parameters without a classical optimizer.

## Packages

| Package | What it is |
|---------|------------|
| **redcedar** | The Python SDK: connect to a Red Cedar server, train, evaluate, predict, explain. Depends only on `requests`. |
| **redcedar-examples** | Example notebooks and scripts that use the SDK. |
| **Red Cedar server** | Prepares the data, builds and runs the circuits, and trains the models. The SDK talks to it over HTTPS. |

Circuits run on Qiskit simulators, on CUDA-Q (including multi-GPU execution), and on IonQ and IQM simulators and
quantum computers.

## Related Repositories

- **[redcedar](https://github.com/coherent-computing/redcedar)**: the SDK source.
- **[redcedar-examples](https://github.com/coherent-computing/redcedar-examples)**: the example notebooks.

## License

The redcedar SDK is open source. See the LICENSE file in the repository for details.

## Version

Current SDK version: **0.93.0**. Current server version: **0.93** (November 2026).

See [Release Notes](./release_notes.md) for version history.

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
