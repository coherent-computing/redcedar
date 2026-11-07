# Examples

The [redcedar-examples](https://github.com/coherent-computing/redcedar-examples) repository has Jupyter notebooks
that use the SDK. Each one runs against a Red Cedar server: set `REDCEDAR_URL` and `REDCEDAR_API_KEY` before
starting Jupyter (see [Connecting to a Server](user_guide.md#connecting-to-a-server)).

```bash
git clone https://github.com/coherent-computing/redcedar-examples.git
cd redcedar-examples
pip install "redcedar[plotting]"
jupyter notebook 01_quick_start.ipynb
```

## Notebooks

Start with `01_quick_start.ipynb`; the others go deeper into one topic each and can be read in any order.

| Notebook | Shows |
|----------|-------|
| `01_quick_start.ipynb` | The basic workflow: train a model on classified samples, classify samples using the trained model, check the predicted classes, and see which features the model relies on (explainable AI) |
| `02_dataset_analysis.ipynb` | Understanding a dataset before training: PCA, mutual information and quantum resource estimation with plots, comparing two datasets, and analyzing your own CSV file |
| `03_training_settings.ipynb` | Training settings, one section per setting: `seed` (repeatable runs) and `op_direction` (order of the operators) |
| `04_training_in_depth.ipynb` | Training loss and accuracy during training, layers and layer chaining, test accuracy over the course of training, per-class results, choosing the train and test data, reusing trained models, and checking on or stopping a running job |

## Scripts

`quick_start.py` has the same steps as `01_quick_start.ipynb`, as a plain Python script for running from the
command line (`python quick_start.py`) or a scheduler. More scripts will follow, and the same steps can also be
run with the [`redcedar` command](user_guide.md#command-line).

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
