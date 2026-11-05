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
| `01_quick_start.ipynb` | The basic workflow: train a model, plot the training curves, test it on held-out data, and see which features it relies on (explainable AI) |
| `02_dataset_analysis.ipynb` | Understanding a dataset before training: PCA, mutual information and quantum resource estimation with plots, comparing two datasets, and analyzing your own CSV file |
| `03_training_settings.ipynb` | Training settings, one section per setting: `seed` (repeatable runs) and `op_direction` (order of the operators) |
| `04_training_in_depth.ipynb` | Layers and layer chaining, test accuracy over the course of training, per-class results, choosing the train and test data, reusing trained models, and checking on or stopping a running job |

## Scripts

Each notebook will also come as a plain Python script, for running from the command line or a scheduler, and
the same steps can be run with the [`redcedar` command](user_guide.md#command-line).

<br>
&copy; 2026 Cascade Quantum. All Rights Reserved.
