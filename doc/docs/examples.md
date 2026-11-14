# Examples

The [redcedar-examples](https://github.com/coherent-computing/redcedar-examples) repository has Jupyter notebooks
and a script that use the SDK. Each one runs against a Red Cedar server: set `REDCEDAR_URL` and `REDCEDAR_API_KEY` before
starting Jupyter (see [Connecting to a Server](user_guide.md#connecting-to-a-server)).

```bash
git clone https://github.com/coherent-computing/redcedar-examples.git
cd redcedar-examples
pip install "redcedar[plotting]"
jupyter notebook 01_quick_start.ipynb
```

## Notebooks

Start with `01_quick_start.ipynb`; the others go deeper into one topic each and can be read in any order. Each
notebook is saved with the output of a run, so you can read the results and plots on GitHub without running it.

| Notebook | Shows |
|----------|-------|
| `01_quick_start.ipynb` | The basic workflow, as in the [Quick Start](quick_start.md): train a quantum model on a CSV file of classified samples, classify the samples in a second file using the trained model, check the predicted classes, and see which features the model relies on (explainable AI) |
| `02_dataset_analysis.ipynb` | How to understand a dataset before training: PCA, mutual information and quantum resource estimation, comparing two datasets, and analyzing your own CSV file |
| `03_training_settings.ipynb` | How training settings change a model, one section per setting: `seed` (repeatable runs) and `op_direction` (order of the operators), and the settings saved with each model |
| `04_training_in_depth.ipynb` | A closer look at training: loss and accuracy during training, layers and layer chaining, test accuracy over the course of training, results per class and per layer, choosing the train and test data, reusing trained models, and checking on or stopping a running job |
| `05_regression.ipynb` | The Quick Start's steps for regression, where the model predicts a number: train, measure the model on its test rows (mean absolute error), predict values for samples in a second file, and check the predicted values. Regression does not work well yet in this release: the predictions are currently further off than guessing the average |
| `06_random_forest.ipynb` | The Quick Start's steps with a random forest, the classical model Red Cedar trains as a baseline: train it on the same file, classify the samples, check the predicted classes, and see which columns it relies on (see [Random Forest](user_guide.md#random-forest)) |
| `07_quantum_and_forest.ipynb` | The quantum model and the random forest side by side, trained and tested on the same rows: test accuracy, the same samples classified by both, the samples where they disagree, and the features each relies on |

## Scripts

`quick_start.py` has the same steps as `01_quick_start.ipynb`, as a plain Python script for running from the
command line or a scheduler. Run it from the redcedar-examples folder (`python quick_start.py`); it saves its plots
as PNG files there. `quantum_and_forest.py` has the comparison of `07_quantum_and_forest.ipynb`. More scripts will follow, and the same steps can also be
run with the [`redcedar` command](user_guide.md#command-line).

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
