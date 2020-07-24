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

from pygeoapi.process.base import BaseProcessor


PROCESS_SETTINGS = {
    'id': 'woudc-data-registry-explore',
    'title': 'WOUDC Data Registry Search Page Helper',
    'description': 'A WOUDC Data Registry Search Index extension that'
                   ' provides items for all the WOUDC data search page'
                   ' dropdowns, all in one request.',
    'keywords': [],
    'links': [],
    'inputs': [
        {
            'id': 'dataset',
            'title': 'Dataset to Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'country',
            'title': 'Country to Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'station',
            'title': 'Station to Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        }
    ],
    'outputs': [{
        'id': 'woudc-data-registry-explore-response',
        'title': 'WOUDC Data Registry Search Page Output',
        'output': [{
            'formats': [{
                'mimeType': 'application/json'
            }]
        }]
    }],
    'example': {
        'inputs': [
            {
                'id': 'dataset',
                'type': 'text/plain',
                'value': 'OzoneSonde'
            },
            {
                'id': 'country',
                'type': 'text/plain',
                'value': 'CAN'
            },
            {
                'id': 'station',
                'type': 'text/plain',
                'value': '077'
            }
        ]
    }
}


class SearchPageProcessor(BaseProcessor):
    """
    WOUDC Data Registry API extension for the search page.

    Produces lists of features that are relevant for populating the
    dropdowns on the WOUDC data search page. Designed to supply all
    dropdowns in one request to reduce how long it takes.

    Supports several filters, one for most selections on the search page.
    """

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: Provider definition?
        :returns: `woudc_api.plugins.explore.SearchPageProcessor`
        """

        BaseProcessor.__init__(self, provider_def, PROCESS_SETTINGS)
