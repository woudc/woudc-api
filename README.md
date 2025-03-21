# woudc-api

REST and OGC API for WOUDC data services

## Overview

WOUDC API provides a RESTful API for that provides discovery and access to
ozone and ultraviolet radiation data in support of the [World Ozone and
Ultraviolet Radiation Data Centre (WOUDC)](https://woudc.org), one of six
World Data Centres as part of the [Global Atmosphere Watch](https://community.wmo.int/activity-areas/gaw)
programme of the [WMO](https://wmo.int).

## Installation

### Requirements
- [Python](https://python.org) 3.10 and above
- [virtualenv](https://virtualenv.pypa.io/)
- [Elasticsearch](https://www.elastic.co/products/elasticsearch) (8 and above)
- [pygeoapi](https://pygeoapi.io) (0.19.0 and above)
- [woudc-extcsv](https://github.com/woudc/woudc-extcsv) (0.6.0 and above)

### Dependencies
Dependencies are listed in [requirements.txt](requirements.txt). Dependencies
are automatically installed during installation.

### Installing woudc-api

```bash
# setup virtualenv
python3 -m venv --system-site-packages woudc-api_env
cd woudc-api_env
source bin/activate

# setup local OGC schemas (i.e. WOUDC_API_OGC_SCHEMAS_LOCATION in default.env)
mkdir schemas.opengis.net
curl -O http://schemas.opengis.net/SCHEMAS_OPENGIS_NET.zip && unzip ./SCHEMAS_OPENGIS_NET.zip "ogcapi/*" -d schemas.opengis.net && rm -f ./SCHEMAS_OPENGIS_NET.zip

# clone pygeoapi codebase and install
git clone https://github.com/geopython/pygeoapi.git
cd pygeoapi
pip install -r requirements.txt
pip install .
cd ..

# clone woudc-extcsv and install
git clone https://github.com/woudc/woudc-extcsv.git
cd woudc-extcsv
pip install .
cd ..

# clone woudc-api codebase and install
git clone https://github.com/woudc/woudc-api.git
cd woudc-api
pip install .

# set system environment variables
cp default.env local.env
vi local.env  # edit accordingly
. local.env

# generate openapi document
pygeoapi openapi generate ${PYGEOAPI_CONFIG} -f json --output-file ${PYGEOAPI_OPENAPI}

# optional: validate openapi document
pygeoapi openapi validate ${PYGEOAPI_OPENAPI}

# run the server
woudc-api serve  # server runs on http://localhost:5000

curl http://localhost:5000  # redirect to WOUDC data services pages

curl http://localhost:5000/oapi  # OGC API endpoint
```

#### Docker

Docker commands:
```bash
# set system environment variables
cp default.env local.env
vi local.env  # edit accordingly
. local.env

# build
docker build -t woudc-api .

# run container
docker run -d --name woudc-api -p ${WOUDC_API_BIND_PORT}:${WOUDC_API_BIND_PORT} woudc-api
```

Docker compose commands **(recommended)**:
```bash
# set system environment variables
cp default.env docker.env
vi docker.env  # edit accordingly
. docker.env

# build image
docker compose -f docker-compose.yml build

# container down
docker compose -f docker-compose.yml down

# container up (detached)
docker compose -f docker-compose.yml up -d
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
