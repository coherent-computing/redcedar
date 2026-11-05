# Red Cedar Documentation

This directory contains the documentation source files and build tools for the Red Cedar SDK, laid out like
the QED-C benchmarks documentation.

The documentation is built using [mkdocs](https://www.mkdocs.org/), which converts markdown files into a themed
HTML site. Source files are in the `docs/` folder.

These docs are for SDK users and don't introduce the UI (only the API key section mentions it, for people who
already have access). The release notes and PAL here are the only copies; UI documentation is kept with the UI.

## Publishing

The site is published at https://coherent-computing.github.io/redcedar/. A push to `main` that changes
anything under `doc/` runs `.github/workflows/deploy_docs.yml`, which builds the site and pushes it to the
`gh-pages` branch; GitHub Pages serves that branch. The built `site/` folder is not committed.

To publish by hand instead (needs push access), from this `doc/` directory:
```
python -m mkdocs gh-deploy
```

## Building the Documentation

mkdocs is already installed in the Qiskit environment. From this `doc/` directory:
```
python -m mkdocs build
```

This produces a `site/` folder containing the complete HTML documentation. Open `site/index.html` to view.

## Live Preview

For development with automatic reload:
```
python -m mkdocs serve
```

Then open [http://localhost:8000/](http://localhost:8000/) in your browser. Changes to files in `docs/` are
reflected immediately.

## Convenience Script

On Windows, run:
```
make_docs
```

## Documentation Files

| File | Content |
|------|---------|
| `docs/index.md` | Documentation overview and navigation |
| `docs/quick_start.md` | First-time user walkthrough: train, predict, one step further |
| `docs/user_guide.md` | Complete reference for the SDK and the command line |
| `docs/examples.md` | The example notebooks and scripts |
| `docs/release_notes.md` | Version history |
| `docs/known_issues.md` | Problems, anomalies, and limitations |
| `docs/about.md` | Project background, packages, license |
