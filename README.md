# woudc-api

REST and OGC API for WOUDC data services

## Overview

WOUDC API provides a RESTful API for that provides discovery and access to
ozone and ultraviolet radiation data in support of the [World Ozone and 
Ultraviolet Radiation Data Centre (WOUDC)](https://woudc.org), one of six
World Data Centres as part of the [Global Atmosphere Watch](https://public.wmo.int/en/programmes/global-atmosphere-watch-programme)
programme of the [WMO](https://public.wmo.int).

## Installation

### Requirements
- [Python](https://python.org) 3 and above
- [virtualenv](https://virtualenv.pypa.io/)
- [Elasticsearch](https://www.elastic.co/products/elasticsearch) (5.5.0 and above)
- [pygeoapi](https://pygeoapi.io)

### Dependencies
Dependencies are listed in [requirements.txt](requirements.txt). Dependencies
are automatically installed during installation.

### Installing woudc-api

```bash
# setup virtualenv
python3 -m venv --system-site-packages woudc-api
cd woudc-api
source bin/activate

# clone pygeoapi codebase and install
git clone https://github.com/geopython/pygeoapi.git
cd pygeoapi
python setup.py install
cd ..

# clone woudc-api codebase and install
git clone https://github.com/woudc/woudc-api.git
cd woudc-api
python setup.py install

# set system environment variables
cp default.env local.env
vi local.env  # edit accordingly
. local.env

# generate openapi document
pygeoapi generate-openapi-document -c $PYGEOAPI_CONFIG > $PYGEOAPI_OPENAPI

# run the server
woudc-api serve  # server runs on http://localhost:5000

curl http://localhost:5000  # redirect to WOUDC data services pages

curl http://localhost:5000/oapi  # OGC API endpoint
```

### Development

```bash
# install dev requirements
pip install -r requirements-dev.txt
```

#### Code Conventions

* [PEP8](https://www.python.org/dev/peps/pep-0008)

### Bugs and Issues

All bugs, enhancements and issues are managed on [GitHub](https://github.com/woudc/woudc-api/issues).

## Contact

* [Tom Kralidis](https://github.com/tomkralidis)
* [Kevin Ngai](https://github.com/kngai)
