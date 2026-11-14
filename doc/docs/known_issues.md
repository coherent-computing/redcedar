# PAL — Problems, Anomalies, and Limitations

As with most complex and evolving software, **Red Cedar** has several issues you may want to be aware of. This section describes known **P**roblems, **A**nomalies, and **L**imitations. Being aware of these in advance can help avoid frustration.

## Limitations

These are fundamental limitations in the current implementation. Some may be relaxed in future versions.

#### Tasks and Data

- **Explainable AI supports classification models only.** Regression models (`task="regression"`) train, evaluate and predict, but `explainable.run()` refuses them.

- **A model needs its training file on the server.** New rows are prepared the way the training data was (scaling, compression, encoding), and that preparation is rebuilt from the training data each time. So evaluation, predictions, training analysis and explainable AI all read the model's training file again, and fail once it is gone. An uploaded training file goes away when you delete it (`datasets.delete_upload()` or the web app), when you upload another file with the same name and choose to replace it, or when a super user deletes it. Before a delete or a replace, the web app says how many trained models need the file, and `datasets.uploads()` gives the same count as `models`. The limit of 20 uploaded files per user doesn't delete a file that a model needs. Catalog datasets are not affected. **Workaround**: keep a training file as long as you use the models trained on it; delete those models first (`inference.delete_model()`) when you no longer need them.

- **Regression predictions stay within the range of the training targets.** The model encodes the target on `num_qubits_target` qubits (default 2, so 4 levels) as a fraction of the range between the smallest and largest training target. A prediction is the average of that fraction over the measured outcomes, so it can't fall outside that range, and its resolution depends on the number of target qubits.

- **Only CSV files can be uploaded.** You can train on the catalog datasets and on CSV files you upload, but you can't yet plug in your own data loaders.

#### Server

- **The server runs one job at a time.** Jobs submitted while another job is running are queued and start in order.

- **Only training can be stopped.** Inference, explainable AI and the training replay run to completion once they start.

- **Each user keeps their 20 most recent models.** When a training takes a signed-in user past 20 trained models, their oldest models are deleted. Models trained with no user (a local server, or the backend key) are not limited, and a restart doesn't delete models. **Workaround**: to keep an older model, copy its folder from `server/training_results/`.

- **A restart drops jobs that were running.** When the server starts, it removes jobs that were running when it stopped. They are not restarted; submit them again. Queued jobs are kept.

- **Run one server per Red Cedar folder.** All servers started from the same `red-cedar` folder share its job database (`server/jobs.db`). This includes a Qiskit server on the host and a CUDA-Q server in a container that mounts the same folder. Two servers running at once take each other's queued jobs and can fail with `disk I/O error`. Stop one server before starting another.

#### CUDA-Q

- **CUDA-Q samples; the Qiskit simulator is exact.** CUDA-Q always estimates probabilities from shots. When no shot count is set, training, validation and inference on CUDA-Q use 100 shots, while the Qiskit statevector simulator computes exact probabilities. Results on the two APIs therefore differ somewhat for the same settings and seed. Explainable AI on CUDA-Q uses 10000 shots; this is a temporary value and will become a setting.

- **Seeds don't make MPI multi-GPU runs repeatable yet.** In the circuit-parallel (`RC_PARALLEL=1`) and hybrid (`RC_GPUS_PER_CIRCUIT`) modes, the execution library sets the CUDA-Q target again inside its multi-GPU code, which drops the seed. Results are valid, but two runs with the same seed can differ. Single-GPU runs, and runs that spread one circuit across several GPUs, are seeded normally.

#### Qiskit

- **On Qiskit, a seed fixes only the starting parameters when shots are used.** With a shot count set, or on a hardware or fake hardware backend, the sampling itself is not seeded, so results vary from run to run. Default runs on the statevector simulator are exact and repeat.

## Anomalies

These are not bugs per se, but behaviors worth knowing about.

#### Seeds

- **The same seed gives different results on Qiskit and CUDA-Q.** Both start from the same parameters, but CUDA-Q estimates probabilities from shots and the Qiskit simulator computes them exactly (see Limitations), so training takes a different path.

- **An unseeded run right after a seeded run can repeat.** On a running server, the random state carries over from one job to the next. Two unseeded runs that each follow the same seeded run start from the same state and give the same result. To get different random starts, give each run its own seed.

#### Data

- **With `test_size=0` the training log still prints test results.** The training workflows test the model before and after training; with no test set, they test on a few training rows. Those results appear in the log but are not reported: the layer results have no test values.

- **Regression targets that are whole numbers are treated as classes unless you say otherwise.** The task type is detected from the target column, and a column holding only whole numbers (including values like `12.0`) looks like class labels. **Workaround**: pass `task="regression"` to `training.run()` (or `--task regression` on the command line).

## Known Problems

These are specific bugs or issues that may be fixed in future releases.

#### Regression

- **Regression predictions are not useful yet.** On the Energy Efficiency example (`05_regression.ipynb` in the examples), the model predicts about the same value for every sample, near the top of the target range, and its mean absolute error is larger than that of always predicting the average training value. The training loss falls while the test loss does not improve. Classification is not affected.

#### Output

- **Training logs a `DEBUG:` line on every parameter update.** The line comes from `quantum_learning/optimizer.py` and makes the server's training log much longer. The SDK shows it only with `verbose="log"`. It does not affect results.

#### Tests

- **`tests/test_circuit_builders.py` fails to import.** It imports `cudaq_builders.ansatz`, which no longer exists (the module is now `quantum_ansatz.py`).

<br>
&nbsp;&copy;&nbsp;2026 Cascade Quantum. All Rights Reserved.
