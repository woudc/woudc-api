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

# Development stage
FROM ubuntu:jammy AS develop-stage

# Default environment variables if none are passed in
ARG PYGEOAPI_GITREPO=https://github.com/geopython/pygeoapi.git
ARG WOUDC_EXTCSV_GITREPO=https://github.com/woudc/woudc-extcsv.git

# Set environment variables
ENV BASEDIR=/data/web/woudc-api-nightly
ENV APPDIR=${BASEDIR}/woudc-api
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR ${BASEDIR}

# Set up the repository mirror for faster package retrieval
RUN sed -i 's/http:\/\/archive.ubuntu.com\/ubuntu\//mirror:\/\/mirrors.ubuntu.com\/mirrors.txt/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:gcpp-kalxas/wmo && \
    add-apt-repository ppa:ubuntugis/ppa && \
    apt-get update && \
    apt-get install -y python3 python3-pip python3-flask git curl unzip python3-certifi && \
    # Install pygeoapi
    git clone ${PYGEOAPI_GITREPO} -b 0.19.0 --depth=1 && \
    cd pygeoapi && \
    pip install -r requirements.txt && \
    pip install . && \
    cd ${BASEDIR} && \
    # Install woudc-extcsv
    git clone ${WOUDC_EXTCSV_GITREPO} -b master --depth=1 && \
    cd woudc-extcsv && \
    pip install . && \
    cd ${BASEDIR}

# Copy application code
COPY . ${APPDIR}

# Install application dependencies
RUN cd ${APPDIR} && \
    pip install -r requirements.txt && \
    pip install gunicorn gevent Flask-Cors && \
    pip install .

# Cleanup unnecessary packages and files
RUN apt-get remove --purge -y git && \
    apt-get clean && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Fix permissions (mark entrypoint as executable)
RUN chmod +x ${APPDIR}/entrypoint.sh

# Start entrypoint.sh
ENTRYPOINT /bin/sh -c "${APPDIR}/entrypoint.sh"

