#!/bin/bash

# =================================================================
#
# Author: Kevin Ngai <kevin.ngai@ec.gc.ca>
#
# Copyright (c) 2024 Kevin Ngai
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

BASEDIR=/data/web/woudc-api-nightly
PYGEOAPI_GITREPO=https://github.com/geopython/pygeoapi.git
WOUDC_API_GITREPO=https://github.com/woudc/woudc-api.git
WOUDC_EXTCSV_GITREPO=https://github.com/woudc/woudc-extcsv.git
DAYSTOKEEP=7

export WOUDC_API_URL=https://gods-geo.woudc-dev.cmc.ec.gc.ca/woudc-api/nightly/latest/oapi/
export WOUDC_API_BIND_HOST=0.0.0.0/
export WOUDC_API_BIND_PORT=5000
# WOUDC_API_ES_USERNAME and WOUDC_API_ES_PASSWORD loaded from ~/.profile
export WOUDC_API_ES_URL=https://${WOUDC_API_ES_USERNAME}:${WOUDC_API_ES_PASSWORD}@localhost:9200
export WOUDC_API_OGC_SCHEMAS_LOCATION=/data/web/woudc-api-nightly/latest/schemas.opengis.net

DATETIME=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d.%H%M)
NIGHTLYDIR="woudc-api-$TIMESTAMP"

log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $*"
}

cleanup_old_builds() {
    log "Deleting nightly builds > $DAYSTOKEEP days old"
    find . -type d -name "woudc-api-20*" | while read -r dir; do
        DATETIME2=$(echo "$dir" | awk -F- '{print $3}' | awk -F. '{print $1}')
        DIFF=$(( ( $(date +%s -d "$DATETIME") - $(date +%s -d "$DATETIME2") ) / 86400 ))
        if [ "$DIFF" -gt "$DAYSTOKEEP" ]; then
            rm -rf "$dir"
        fi
    done
    rm -rf latest
}

create_venv_and_install() {
    log "Generating nightly build for $TIMESTAMP"
    python3 -m venv --system-site-packages "$NIGHTLYDIR" && cd "$NIGHTLYDIR" || exit 1
    source bin/activate

    log "Cloning repositories..."
    git clone "$WOUDC_API_GITREPO"
    git clone "$WOUDC_EXTCSV_GITREPO"
    git clone "$PYGEOAPI_GITREPO"

    log "Installing pygeoapi..."
    cd pygeoapi || exit 1
    git checkout 0.16.1
    pip3 install -r requirements.txt
    python3 setup.py install

    log "Installing woudc-extcsv..."
    cd ../woudc-extcsv || exit 1
    python3 setup.py install

    log "Installing woudc-api..."
    cd ../woudc-api || exit 1
    python3 setup.py install
    cd ..
}

configure_woudc_api() {
    log "Generating schemas.opengis.net..."
    mkdir schemas.opengis.net
    curl -O http://schemas.opengis.net/SCHEMAS_OPENGIS_NET.zip
    unzip ./SCHEMAS_OPENGIS_NET.zip "ogcapi/*" -d schemas.opengis.net
    rm -f ./SCHEMAS_OPENGIS_NET.zip

    log "Configuring woudc-api configurations..."
    cp woudc-api/deploy/default/woudc-api-config.yml woudc-api/deploy/nightly
    sed -i 's#basepath: /#basepath: /woudc-api/nightly/latest#' woudc-api/deploy/nightly/woudc-api-config.yml
    sed -i 's^# cors: true^cors: true^' woudc-api/deploy/nightly/woudc-api-config.yml

    log "Generating woudc-api-openapi.yml..."
    pygeoapi openapi generate woudc-api/deploy/nightly/woudc-api-config.yml > woudc-api/deploy/nightly/woudc-api-openapi.yml
    sed -i "s#http://schemas.opengis.net#$WOUDC_API_URL/schemas#g" woudc-api/deploy/nightly/woudc-api-openapi.yml
}

set_symlink_and_permissions() {
    log "Creating 'latest' symlink and setting correct permissions..."
    ln -s "$NIGHTLYDIR" latest
    chgrp eccc-hpc-cmdx -R "$NIGHTLYDIR"
    chmod -R 775 "$NIGHTLYDIR"
    log "Done."
}

main() {
    cd "$BASEDIR" || exit 1
    cleanup_old_builds
    create_venv_and_install
    configure_woudc_api
    set_symlink_and_permissions
}

main "$@"
