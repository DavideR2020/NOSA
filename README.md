# NOSA

Neuro-Optical Signal Analysis

NOSA is an analytical toolbox designed specifically for the analysis and interpretation of voltage imaging data. NOSA features baseline fitting and filtering algorithms to extract electrical patterns from high speed recordings with low signal-to-noise ratios. NOSA also includes features for spike- and burst detection, movement artefact compensation, and the ability to analyze simultaneously performed optical and electrical recordings. Moreover, NOSA provides analytical tools to identify temporal relations in multicellular electrical patterns via cross correlation analysis. NOSA is stand-alone software that requires no installation and comes with an intuitive user-interface that allows to precisely control and comprehend each analytical step. For more information, see the documentation. 

## Running NOSA from source code

To run NOSA from source code, the following prerequisites are needed:

```
python 3.7.1
numpy 1.16.2
scipy 1.2.1
pyqt5 5.11.3
pyqtgraph 0.10.0
matplotlib 3.0.3
pystackreg 0.2.1
dipy 0.15.0
qdarkstyle 2.5.4
pyabf 2.2.8
quantities 0.12.3
xlsxwriter 1.1.5
tifffile 2019.3.8
```

When the prerequisites are met, run NOSA with `python main.py`.

## Creating NOSA Executables

To create executable files, [PyInstaller](https://www.pyinstaller.org/) is used. A configuration file for PyInstaller is given. To create the executable, run `pyinstaller main.spec`.

## Running Unittests

There are some unittests for NOSA, located in `tests` directory. Run these with `python -m unittest tests.FeatureTests`.

## Documentation

The documentation is written in Markdown. The source file is `source/doc.md` in the documentation directory. The distributable file is `doc.html`. Please note that the `assets`, `images`, and `package_license` directories are necessary for `doc/doc.html`.

For converting the `.md` file to a `.html` file, the [markdown-styles](https://github.com/mixu/markdown-styles) package is used. To create the distributable `.html` file from the `.md` file, run `generate-md --layout github --input source --output .` in the documentation directory.
