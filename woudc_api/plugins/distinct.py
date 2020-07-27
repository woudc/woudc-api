# =================================================================
#
# Terms and Conditions of Use
#
# Unless otherwise noted, computer program source code of this
# distribution # is covered under Crown Copyright, Government of
# Canada, and is distributed under the MIT License.
#
# The Canada wordmark and related graphics associated with this
# distribution are protected under trademark law and copyright law.
# No permission is granted to use them outside the parameters of
# the Government of Canada's corporate identity program. For
# more information, see
# http://www.tbs-sct.gc.ca/fip-pcim/index-eng.asp
#
# Copyright title to all 3rd party software distributed with this
# software is held by the respective copyright holders as noted in
# those files. Users are asked to read the 3rd Party Licenses
# referenced with those assets.
#
# Copyright (c) 2020 Government of Canada
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
import logging

from elasticsearch import Elasticsearch

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError


LOGGER = logging.getLogger(__name__)

PROCESS_SETTINGS = {
    'id': 'woudc-data-registry-select-distinct',
    'title': 'WOUDC Data Registry Group Search',
    'description': 'A WOUDC Data Registry Search Index extension approximating'
                   ' the SELECT DISTINCT query in SQL by returning groups'
                   ' of unique values for selected fields.',
    'keywords': [],
    'links': [],
    'inputs': [
        {
            'id': 'index',
            'title': 'Index to Search',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'distinct',
            'title': 'Core Query Fields',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'source',
            'title': 'Satellite Source Fields',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 0
        }
    ],
    'outputs': [{
        'id': 'woudc-data-registry-distinct-response',
        'title': 'WOUDC Data Registry Group Select Output',
        'output': [{
            'formats': [{
                'mimeType': 'application/json'
            }]
        }]
    }],
    'example': {
        'inputs': [
            {
                'id': 'index',
                'type': 'text/plain',
                'value': 'instrument'
            },
            {
                'id': 'distinct',
                'type': 'application/json',
                'value': [ 'name', 'model', 'dataset', 'station_id' ]
            },
            {
                'id': 'source',
                'type': 'application/json',
                'value': [ 'data_class', 'station_name', 'waf_url' ]
            }
        ]
    }
}


class GroupSearchProcessor(BaseProcessor):
    """
    WOUDC Data Registry API extension for querying distinct groups.

    Returns lists of unique groups of fields, like a "SELECT DISTINCT"
    query in SQL.
    """

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: Provider definition?
        :returns: `woudc_api.plugins.groupings.GroupSearchProcessor`
        """

        BaseProcessor.__init__(self, provider_def, PROCESS_SETTINGS)

        LOGGER.debug('Setting Elasticsearch properties')
        url_tokens = os.environ.get('WDR_ELASTICSEARCH_URL').split('/')
        host = url_tokens[2]

        LOGGER.debug('Host: {}'.format(host))
        self.index_prefix = 'woudc_data_registry.'

        LOGGER.debug('Connecting to Elasticsearch')
        self.es = Elasticsearch(host)

        if not self.es.ping():
            msg = 'Cannot connect to Elasticsearch'
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

        LOGGER.debug('Checking Elasticsearch version')
        version = float(self.es.info()['version']['number'][:3])
        if version < 7:
            msg = 'Elasticsearch version below 7 not supported ({})' \
                  .format(version)
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

    def execute(self, inputs):
        """
        Responds to an incoming request to this endpoint of the API.

        :param inputs: Body of the incoming request.
        :returns: Body of the response sent for that request.
        """

        return None
