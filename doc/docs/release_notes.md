# Release Notes

**Red Cedar** is continually evolving, with issues fixed and enhancements made to add features.
This section presents a brief record of relevant changes made to each version that has been released. Latest version is at the top.

## Version 0.9 Release Notes

Version 0.9 is the first tagged version of Red Cedar. Each release below lists the changes since the one before it.

### Release 0.94 - in preparation

- **Delete uploaded files and models from the SDK** -- `client.datasets.uploads()` lists your uploaded files and `client.datasets.delete_upload(dataset_id)` deletes one. `client.inference.delete_model(train_id)` deletes one of your trained models. A model needs the file it was trained on, so delete the models trained on a file before the file (see [Your Uploaded Files](user_guide.md#your-uploaded-files)).
- **Your own models only** -- `client.inference.models()`, `redcedar models` and the web app's Recent Models list the models you trained. They listed every user's models before.
- **Sample datasets** -- The web app has two kinds of uploaded files: training datasets, with the classes or target values the model learns from, and sample datasets, the rows a trained model classifies or predicts. Inference > Classification and Regression run the active model on a sample dataset whose columns fit it, show the predictions, and download them as a CSV file. Scoring a model on its held-out test rows moved to Model Training > Evaluate.
- **How a dataset will train** -- After a training dataset is uploaded, the web app shows how it will be trained (for example "Trains as classification of the last column, diagnosis"), in the upload list, and on Run Training. A file whose target is whole numbers is detected as classification, one class per value; a link offers to train it as regression instead.
- **Delete models in the web app** -- Recent Models has a delete button on each model, with a two-step confirmation.
- **Public datasets** -- In the web app, a file you upload can be made public: other users then see it under Public Files, with your name, and can train on it. Only you (or a super user) can delete it.
- **Uploaded files are private** -- A user can use an uploaded file only when it is theirs or public, in every request that takes its ID.
- **Models are private** -- Evaluation, predictions, training analysis and explainable AI refuse a model that another user trained, as if it didn't exist.
- **The 20-file limit keeps files that models need** -- When an upload takes a user past 20 files, the oldest is deleted as before, unless a trained model still needs it: a model reads its training file again, so deleting it would break the model.
- **Admin pages** -- An Admin section in the web app's menu holds Jobs, Users, Uploads and Models. Admins can use Jobs (and now manage the job queue, which needed the super role) and Models, a list of every user's trained models; super users can also manage users, see and delete every user's uploaded files, and delete any model. Job Management shows each job's owner by name, and its tables sort by any column. The sort on the admin pages is remembered.
- **User Management** -- A Last Active column (who is using the app right now), an invite dialog, and a way to sign out and manage your account on a phone.
- **Training Settings page** -- Regrouped: the dataset first, the seed among the primary settings, and an Execution section with the backend and parallelization.
- **WDBC with its original labels** -- The catalog's WDBC dataset now has the diagnosis as `M` and `B`, from the original UCI release, instead of OpenML's `1` and `2`. The rows are the same. **Models trained on WDBC with an earlier version predict `1`/`2`: retrain them to get `M`/`B`.**
- **Bug fix: the queue status shared the running job's owner** -- Every signed-in user's queue status included the running job's ID and its owner's user ID. Only the job's owner gets them now.

### Release 0.93 - 8 November 2026

- **Predictions on new data** -- `client.inference.run(train_id, "new_data.csv")` returns a prediction for each row: the class label and the probability of each class, or a number for a regression model. When the file also has the target column, the result includes the accuracy (classification) or the mean absolute error (regression). Columns are matched by header name, or by position in a file without a header row. `output="predictions.csv"` writes the rows with their predictions.
- **Evaluation renamed** -- Scoring a model on the test rows held back from its training run is now `client.training.evaluate(train_id)`, and `client.inference.run()` makes predictions on new data. Code that called `inference.run(train_id)` for the test accuracy must change to `training.evaluate(train_id)`. The example notebooks are updated.
- **Regression** -- `training.run(..., task="regression")` trains a regression model. Without `task=`, the task is detected from the target column; whole numbers are read as classes, so pass `task="regression"` for a target of whole numbers. Evaluation, predictions and the training replay support regression models (loss and mean absolute error); explainable AI supports classification models only. Settings: `num_qubits_target` (default 2) and `loss_type` (default `weighted_hamming`). **Regression predictions are not useful yet in this release:** on the Energy Efficiency example the model predicts about the same value for every sample, and its error is larger than that of predicting the average (see [Known Issues](known_issues.md)).
- **Train on all rows** -- `test_size=0` trains the model on every row. The model then has no test set: the layer results have no test values, and `training.evaluate()` and `training.analyze()` report that there are no test rows.
- **CSV files directly** -- `training.run()` and `inference.run()` take a CSV file path and upload it.
- **Command line** -- The `redcedar` command: `redcedar train`, `evaluate`, `predict` and `models` (also `python -m redcedar`).
- **Connecting** -- `connect()` defaults to `http://127.0.0.1:8002`. A hosted server requires an API key (see [Connecting to a Server](user_guide.md#connecting-to-a-server)). `connect(local=True)` calls the Red Cedar code directly in your Python process, with no server, for development with the Red Cedar source (`pip install -e .` in the `red-cedar` folder); see [Local Mode](user_guide.md#local-mode-for-development).
- **Quieter progress** -- `verbose=True` now prints the progress line, a dot every few seconds while the job is working, and the test result after each training layer. The server's full log for the job, which `verbose=True` used to print, now needs `verbose="log"` (`--log` on the command line).
- **Explainable AI names principal components** -- With dimension reduction (`dimension_reduction: "pca"`, the default), a data qubit holds a principal component, a mix of all the dataset's columns. Explainable AI now names it `PC1`, `PC2`, ... and lists in `made_of` the columns with the largest shares of it, largest first; the web UI shows them in a table under the qubit mapping. With `dimension_reduction: "none"`, each data qubit holds one column and is named after it (see [Explainable AI](user_guide.md#explainable-ai)).
- **Examples** -- The example notebooks are reworked and saved with the output of a run, so they can be read on GitHub. The Quick Start trains on classified samples, classifies the samples in a second file, and checks the predicted classes against their actual classes; `quick_start.py` does the same from the command line. `05_regression.ipynb` shows the same steps for regression. The other notebooks follow the same structure, and `01_full_pipeline.ipynb` is removed (see [Examples](examples.md)).
- **Documentation** -- The Quick Start's second step is "Classify Samples Using the Trained Model". The User Guide explains the training loss and accuracy, and what explainable AI's feature names mean with and without dimension reduction.
- **Versions** -- `client.status()` and `redcedar status` show the server's version and the SDK's. The SDK now follows the server's version number: this release is SDK 0.93.0 (it was 0.1.0), and SDK-only fixes get a new patch number (0.93.1, 0.93.2, ...).
- **Bug fix: CUDA-Q server crash** -- A server running on CUDA-Q could crash after several training jobs. Fixed.
- **Bug fix: seeded CUDA-Q runs** -- Two CUDA-Q runs with the same seed could give different results. Seeded runs now repeat.
- **CUDA-Q explainable AI** -- Explainable AI on CUDA-Q is seeded and uses 10000 shots, so repeated runs on the same model give the same result. The shot count is temporary and will become a setting.
- **Bug fix: fractional targets in CSV files with a header row** -- The target column of such a file was read as text, so a fractional regression target was detected as class labels. Targets that are numbers are now read as numbers.
- **Bug fix: CSV files without a header row and with text class labels** -- The class label in the last column (for example `M`) made the first row look like a header, so the first sample was used as column names and not loaded. The header check now looks at the feature columns, and counts a text value at the top of the target column only when it doesn't occur again in that column (a column name, not a class label).
- **Bug fix: split sizes for uploaded files** -- `train_size` and `test_size` were ignored for uploaded CSV files, which always used the 80/20 split.
- **Bug fix: explainable AI feature names** -- With dimension reduction (the default), the numbers of the selected components were looked up in the dataset's column names, so a data qubit was labelled with a column it did not stand for (for example `mean_radius` for principal component 1). Components are now named as above.
- **Bug fix: explainable AI importance for features with more than one qubit** -- The importance values were shifted by one qubit for each extra qubit of a feature, and the last data qubit always showed 0%. Each qubit now gets its own value.
- **Bug fix: web UI Job Management times and job types** -- Times are shown in your local time zone (they were UTC without saying so), and each job is labelled with its type (training, inference, explainable AI, training analysis, PCA, mutual information, resource estimation).

### Release 0.92 - 2 November 2026

- **CUDA-Q results corrected** -- On the CUDA-Q backend, the predicted class was read from the wrong qubit: a data qubit instead of the prediction qubit. Training on CUDA-Q was therefore scored against the wrong bit. Results are now read by qubit index, the same way as on Qiskit. On a 6-qubit WDBC test, CUDA-Q test accuracy went from 0.535 to 0.781 (Qiskit: 0.746). **Models trained on CUDA-Q with an earlier version should be retrained.** Models trained on Qiskit are not affected.
- **Same bit order on Qiskit and CUDA-Q** -- CUDA-Q circuits are now built so that their results come back in the same bit order as Qiskit, and results are no longer reversed after execution. Qiskit and CUDA-Q now give the same results for the same circuit, within shot noise.
- **Seed and operator direction** -- Two new training settings: `seed`, which sets the initial parameters, and `op_direction` (`backward`, the default, or `forward`). Both are saved with the model. With a seed set, repeated runs give the same result on Qiskit and on CUDA-Q. On CUDA-Q, the first seeded run after the server starts can differ slightly from later runs with the same seed.
- **Shared optimizer for classification and regression** -- Classification and regression now use the same optimizer and loss function code. Classification results are unchanged. The regression loss options are `hamming`, `weighted_hamming` and `huber`.
- **Bug fix: regression workflow** -- The command-line regression workflow (`workflow_regression/`) failed with a `TypeError` at the final test step, after training had finished, so no results were saved. It now reports the test loss and saves results.
- **Bug fix: queued jobs** -- A queued job started only when another request reached the server, so with only Python client SDK jobs, a queued job could wait indefinitely. The next queued job now starts as soon as the running job finishes.
- **Bug fix: job progress streams** -- Progress events that arrived while the server was sending earlier events were dropped. Training curves could miss points, and a lost completion event left the client waiting. All events are now delivered, for both training and analysis jobs.
- **Bug fix: CSV files without a header row** -- Class labels from a CSV file with no header row were read as numbers, and saving the per-class results failed. Class labels are now strings for both kinds of file. Regression targets are unchanged.
- Circuits that contain a mid-circuit measurement now raise a clear error instead of returning shifted bits on hardware. Red Cedar circuits do not contain any today.
- New checks in `tests/` for CUDA-Q bit order and class reading (`test_cudaq_bit_order.py`, `check_cudaq_class_read.py`), CUDA-Q results against an exact statevector (`test_cudaq_cct_exact.py`), Qiskit and CUDA-Q equivalence (`test_api_equivalence.py`), and explainable AI from start to finish on both APIs (`check_eai.py`).

### Release 0.91 - 28 September 2026

- **IQM hardware support** -- Training and inference can run on IQM quantum computers (Garnet, Sirius, Emerald) through `qiskit-iqm`, using backend IDs such as `iqm-garnet`. Circuits are sent in batches of 100. The access token is read from `IQM_API_TOKEN`. **Requires an additional package**: `pip install qiskit-iqm`.
- **Stop a running job** -- A new endpoint, `POST /jobs/{job_id}/stop`, stops any running or queued job: training, inference or explainable AI.
- **Data loading and preprocessing (preview)** -- A new module, `quantum_learning/data_loading/`, adds `ClassicalData.load_data()`, train/test splitting, preprocessing (including PCA that chooses the number of components automatically), bit-bit encoding transforms, settings with type checking, and saving and loading of preprocessing objects. The notebook `advanced_data_loading.ipynb` in the same folder shows how to use it. The training workflows and the server do not use it yet.
- Fixed server startup on Windows: `run_server.bat` now starts the server with `python -m uvicorn`.

### Release 0.90 - 23 September 2026

Version 0.9 is the base version from which versioning began. It provides a server for dataset analysis, training, inference and explainable AI, along with command-line workflows for classification and regression and a Python client SDK for notebooks and scripts. Models are defined as hierarchical operators rather than circuits and are synthesized for the selected backend; training uses sub-net initialization, bit-bit encoding of classical data, and exact coordinate update, with no classical optimizer. Circuits run on Qiskit simulators, on CUDA-Q (including multi-GPU execution), and on IonQ simulators and hardware.

<br>
&nbsp;&copy;&nbsp;2026 Cascade Quantum. All Rights Reserved.
