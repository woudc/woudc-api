#!/bin/bash
###################################################################
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
###################################################################

echo "START /entrypoint.sh"

set -e  # Exit on error

# Use the BASEDIR and APPDIR environment variables from Dockerfile
echo "BASEDIR is set to: $BASEDIR"
echo "APPDIR is set to: $APPDIR"

# Default environment variables
export WOUDC_API_URL=${WOUDC_API_URL}  # WOUDC API URL
export PYGEOAPI_CONFIG=${PYGEOAPI_CONFIG}  # PyGeoAPI configuration file
export PYGEOAPI_OPENAPI=${PYGEOAPI_OPENAPI}  # PyGeoAPI OpenAPI specification

# Gunicorn environment settings with defaults
export CONTAINER_NAME="woudc-api-nightly"  # Name of the container
export CONTAINER_HOST=${WOUDC_API_BIND_HOST:-0.0.0.0}  # Host to bind to
export CONTAINER_PORT=${WOUDC_API_BIND_PORT:-6080}  # Port to bind to
export WSGI_WORKERS=${WSGI_WORKERS:-1}  # Number of WSGI workers
export WSGI_WORKER_TIMEOUT=${WSGI_WORKER_TIMEOUT:-6000}  # Timeout for WSGI workers
export WSGI_WORKER_CLASS=${WSGI_WORKER_CLASS:-gevent}  # Worker class for Gunicorn

# What to invoke: default is to run gunicorn server
entry_cmd=${1:-run}

# Shorthand (bash) commands
function error() {
    echo "ERROR: $@"
}
function log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $*"
}

# Signal trapping for graceful shutdown
trap 'log "Shutting down..."; exit 0' SIGTERM

log "Generating schemas.opengis.net..."
cd ${BASEDIR}
mkdir -p schemas.opengis.net
if ! curl -O http://schemas.opengis.net/SCHEMAS_OPENGIS_NET.zip; then
  error "Failed to download schemas.opengis.net ZIP"
  exit 1
fi
if ! unzip -o ./SCHEMAS_OPENGIS_NET.zip "ogcapi/*" -d schemas.opengis.net; then
  error "Failed to unzip schemas.opengis.net"
  exit 1
fi
rm -f ./SCHEMAS_OPENGIS_NET.zip

# woudc-api configuration
log "Configuring woudc-api configurations..."
sed -i 's^# cors: true^cors: true^' "${PYGEOAPI_CONFIG}"

log "Generating woudc-api-openapi.yml with PYGEOAPI_CONFIG=${PYGEOAPI_CONFIG} and PYGEO_API_OPENAPI=${PYGEOAPI_OPENAPI}..."
log "Creating backup of default woudc-api-openapi.yml as: ${PYGEOAPI_OPENAPI}-backup"
cp "${PYGEOAPI_OPENAPI}" "${PYGEOAPI_OPENAPI}-backup"
if ! pygeoapi openapi generate "${PYGEOAPI_CONFIG}" --output-file "${PYGEOAPI_OPENAPI}"; then
  error "OpenAPI document could not be generated ERROR"
  log "Reverting back to using the default OpenAPI document that was backed up..."
  # cp "${DEFAULT_PYGEOAPI_OPENAPI}" "${PYGEOAPI_OPENAPI}"
  cp "${PYGEOAPI_OPENAPI}-backup" "${PYGEOAPI_OPENAPI}"
  rm "${PYGEOAPI_OPENAPI}-backup"
fi
sed -i "s#http://schemas.opengis.net#$WOUDC_API_URL/schemas#g" "${PYGEOAPI_OPENAPI}"

log "OpenAPI document generated. Continuing woudc-api start up..."

case ${entry_cmd} in
    run)
        log "Start gunicorn name=${CONTAINER_NAME} on ${CONTAINER_HOST}:${CONTAINER_PORT} with ${WSGI_WORKERS} workers"
        exec gunicorn --workers "${WSGI_WORKERS}" \
                --worker-class="${WSGI_WORKER_CLASS}" \
                --timeout "${WSGI_WORKER_TIMEOUT}" \
                --name="${CONTAINER_NAME}" \
                --bind "${CONTAINER_HOST}:${CONTAINER_PORT}" \
                --reload \
                --reload-extra-file "${PYGEOAPI_CONFIG}" \
                pygeoapi.flask_app:APP
      ;;
    *)
      error "unknown command arg: must be 'run'"
      ;;
esac

log "END /entrypoint.sh"
