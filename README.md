# COVID-19 NPIs sampling

[![Documentation Status](https://readthedocs.org/projects/covid19-npis-europe/badge/?version=latest)](https://covid19-npis-europe.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Logo](docs/source/doc/logo.png)

## Installation 

We recommend installing it using anaconda or miniconda: 

```
git clone --recurse-submodules git@github.com:jdehning/covid19_npis_sampling.git
cd covid19_npis_sampling
conda create -n pymc4-env python=3.8
conda activate pymc4-env
pip install -r requirements.txt jupyter
```
## Getting started

For the sampling investigation project, we started a new branch `investigate_sampling`
please use this one. You will find there inside `scripts/notebooks` the relevant 
scripts to run the model, and also to build a likelihood function of the model, which 
can be evaluated from Julia if wanted.  

- [**Documentation**](https://covid19-npis-europe.readthedocs.io/en/latest)
