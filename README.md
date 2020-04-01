# NOSA

Neuro-Optical Signal Analysis

NOSA is a tool specially designed for processing and analysing voltage imaging. However, it can handle calcium imaging and patch clamp data, too. The features include Movement Correction, ROI Selection, Event Detection, Power Spectrum Analysis, and Cross Correlation. For more information, see the documentation. 

## Running NOSA from source code

To run NOSA from source code, the following prerequisites are needed:

```
python>=3.7.1
numpy>=1.16.2
scipy>=1.2.1
pyqt5==5.11.3
pyqtgraph>=0.10.0
matplotlib>=3.0.3
pystackreg>=0.2.1
dipy>=0.15.0
qdarkstyle==2.5.4
neo>=0.7.1
quantities>=0.12.3
xlsxwriter>=1.1.5
tifffile>=2019.3.8
```

Please note the exact version of `PyQt5` and `qdarkstyle`. If a newer version of these packages is used, NOSA may be displayed messy. However, all functionalities should work.

When the prerequisites are met, run NOSA with `python main.py`.

## Creating NOSA Executables

To create executable files, [PyInstaller](https://www.pyinstaller.org/) is used. A configuration file for PyInstaller is given. To create the executable, run `pyinstaller main.spec`.

## Running Unittests

There are some unittests for NOSA, located in `tests` directory. Run these with `python -m unittest tests.FeatureTests`.

## Documentation

The documentation is written in Markdown. The source file is `source/doc.md` in the documentation directory. The distributable file is `doc.html`. Please note that the `assets`, `images`, and `package_license` directories are necessary for `doc/doc.html`.

For converting the `.md` file to a `.html` file, the [markdown-styles](https://github.com/mixu/markdown-styles) package is used. To create the distributable `.html` file from the `.md` file, run `generate-md --layout github --input source --output .` in the documentation directory.
