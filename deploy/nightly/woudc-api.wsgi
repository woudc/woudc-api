# =================================================================
#
# Author: Tom Kralidis <tom.kralidis@canada.ca>
#
# Copyright (c) 2020 Tom Kralidis
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

import os
import sys

os.environ['PYGEOAPI_CONFIG'] = '/data/web/woudc-api-nightly/latest/woudc-api/deploy/nightly/woudc-api-config.yml'
os.environ['PYGEOAPI_OPENAPI'] = '/data/web/woudc-api-nightly/latest/woudc-api/deploy/nightly/woudc-api-openapi.yml'
os.environ['WOUDC_API_BIND_HOST'] = '0.0.0.0'
os.environ['WOUDC_API_BIND_PORT'] = '5000'
os.environ['WOUDC_API_URL'] = 'https://gods-geo.woudc-dev.cmc.ec.gc.ca/woudc-api/nightly/latest'
os.environ['WOUDC_API_ES_URL'] = 'http://localhost:9200'

sys.path.insert(0, '/data/web/woudc-api-nightly/latest/lib/python3.6/site-packages')

from woudc_api.app import app as application
