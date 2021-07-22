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
    'id': 'woudc-data-registry-metrics',
    'title': 'WOUDC Data Registry Metrics Provider',
    'description': 'An extension of the WOUDC Data Registry search index,'
                   ' providing an API for metrics queries that assess'
                   ' file submission and/or usage statistics.',
    'keywords': [],
    'links': [],
    'inputs': [
        {
            'id': 'domain',
            'title': 'Metric Domain',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': False,
                        'options': [
                            'dataset',
                            'contributor',
                        ]
                    }
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'timescale',
            'title': 'Time Scale',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': False,
                        'options': [
                            'year',
                            'month',
                        ]
                    }
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'dataset',
            'title': 'Dataset Filter',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': True,
                    }
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'level',
            'title': 'Data Level Filter',
            'input': {
                'literalDataDomain': {
                    'dataType': 'number',
                    'valueDefinition': {
                        'anyValue': True,
                    }
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'country',
            'title': 'Country Filter',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': True,
                    }
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'station',
            'title': 'Station Filter',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': True,
                    }
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'network',
            'title': 'Instrument Filter',
            'input': {
                'literalDataDomain': {
                    'dataType': 'string',
                    'valueDefinition': {
                        'anyValue': True,
                    }
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        }
    ],
    'outputs': [{
        'id': 'woudc-data-registry-metrics-response',
        'title': 'WOUDC Data Registry Metrics Output',
        'output': {
            'formats': [{
                'mimeType': 'application/json'
            }]
        }
    }],
    'example': {
        'inputs': [
            {
                'id': 'domain',
                'type': 'text/plain',
                'value': 'dataset'
            },
            {
                'id': 'timescale',
                'type': 'text/plain',
                'value': 'year'
            },
            {
                'id': 'network',
                'type': 'text/plain',
                'value': 'Brewer'
            },
            {
                'id': 'country',
                'type': 'text/plain',
                'value': 'CAN'
            }
        ]
    }
}


class MetricsProcessor(BaseProcessor):
    """
    WOUDC Data Registry metrics API extension.

    Provides an endpoint for a number of metrics queries, which
    return statistics about the contents or usage of the WOUDC data registry.

    Different kinds of metrics are distinguished by their "domain", which
    acts like a string identifier passed to this process as an input.
    This way, multiple types of queries can be served from one endpoint.

    The metrics query system takes the place of the metrics tables in
    WOUDC BPS's web-db database.
    """

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: provider definition
        :returns: `woudc_api.plugins.metrics.MetricsProcessor`
        """

        BaseProcessor.__init__(self, provider_def, PROCESS_SETTINGS)

        url_tokens = os.environ.get('WOUDC_API_ES_URL').split('/')

        LOGGER.debug('Setting Elasticsearch properties')
        self.index = 'woudc_data_registry.data_record'
        host = url_tokens[2]

        LOGGER.debug('Host: {}'.format(host))
        LOGGER.debug('Index name: {}'.format(self.index))

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

        domain = inputs.pop('domain')
        timescale = inputs.pop('timescale')
        peer_records = False
        if ('dataset' in inputs) and (inputs['dataset'] == 'peer_data_records'):
            self.index = 'woudc_data_registry.peer_data_record'
            peer_records = True

        if domain == 'dataset':
            return self.metrics_dataset(timescale, peer_records, **inputs)
        elif domain == 'contributor':
            return self.metrics_contributor(timescale, peer_records, **inputs)

    def metrics_dataset(self, timescale, peer_records, **kwargs):
        """
        Returns submission metrics from the WOUDC Data Registry, describing
        number of files and observations submitted for each dataset over
        periods of time.

        Optionally filters for matching value of country, station, and network,
        if present in kwargs.

        :param timescale: Either 'year' or 'month', describing time range size.
        :param kwargs: Optional property values to filter by.
        :returns: Response from the filtered query, converted to
                  "list-of-rows" format in JSON.
        """
        dataset = kwargs.get('dataset', None)
        level = kwargs.get('level', None)

        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        filters = []
        
        if peer_records:
            if source is not None:
                filters.append({'properties.source.raw': source})
            field = 'properties.start_datetime'
        else: 
            if dataset is not None:
                filters.append({'properties.content_category.raw': dataset})
            if level is not None:
                filters.append({'properties.content_level': level})
            field = 'properties.timestamp_date'

        conditions = [{'term': body} for body in filters]

        query_core = {
            date_aggregation_name: {
                'date_histogram': {
                    'field': field,
                    'calendar_interval': date_interval,
                    'format': date_format
                },
                'aggregations': {
                    'total_obs': {
                        'sum': {
                            'field': 'properties.number_of_observations'
                        }
                    }
                }
            }
        }

        query = {
            'size': 0,
            'aggregations': {
                'filters': {
                    'filter': {
                        'bool': {
                            'must': conditions
                        }
                    },
                    'aggregations': query_core
                }
            }
        }

        response = self.es.search(index=self.index, body=query)
        response_body = response['aggregations']

        total_files = response_body['filters']['doc_count']
        histogram = response_body['filters'][date_aggregation_name]

        rows = []
        for document in histogram['buckets']:
            if document['doc_count'] > 0:
                rows.append({
                    'total_files': document['doc_count'],
                    'total_obs': int(document['total_obs']['value']),
                    timescale: document['key_as_string']
                })

        response = {
            'total_files': total_files,
            'metrics': rows
        }

        return 'application/json', response

    def metrics_contributor(self, timescale, peer_records, **kwargs):
        """
        Returns submission metrics from the WOUDC Data Registry, describing
        number of files and observations submitted from each agency over
        periods of time.

        Optionally filters for matching value of dataset, station, and network,
        if specified as kwargs.

        :param timescale: Either 'year' or 'month', describing time range size.
        :param kwargs: Optional property values to filter by.
        :returns: Response from the filtered query, converted to
                  "list-of-rows" format in JSON.
        """

        dataset = kwargs.get('dataset', None)
        country = kwargs.get('country', None)
        station = kwargs.get('station', None)
        network = kwargs.get('network', None)
        source = kwargs.get('source', None)
        
        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        filters = []
        if peer_records:
            if source is not None:
                filters.append({'properties.source.raw': source})
            if station is not None:
                filters.append({'properties.station_id.raw': station})
            if network is not None:
                filters.append({'properties.instrument_type.raw': network})
            field = 'properties.start_datetime'
        else:
            if dataset is not None:
                filters.append({'properties.content_category.raw': dataset})
            if country is not None:
                filters.append({'properties.platform_country.raw': country})
            if station is not None:
                filters.append({'properties.platform_id.raw': station})
            if network is not None:
                filters.append({'properties.instrument_name.raw': network})
            field = 'properties.timestamp_date'

        conditions = [{'term': body} for body in filters]

        query_core = {
            date_aggregation_name: {
                'date_histogram': {
                    'field': field,
                    'calendar_interval': date_interval,
                    'format': date_format
                },
                'aggregations': {
                    'total_obs': {
                        'sum': {
                            'field': 'properties.number_of_observations'
                        }
                    }
                }
            }
        }

        query = {
            'size': 0,
            'aggregations': {
                'filters': {
                    'filter': {
                        'bool': {
                            'must': conditions
                        }
                    },
                    'aggregations': query_core
                }
            }
        }

        response = self.es.search(index=self.index, body=query)
        response_body = response['aggregations']

        total_files = response_body['filters']['doc_count']
        histogram = response_body['filters'][date_aggregation_name]

        rows = []
        for document in histogram['buckets']:
            if document['doc_count'] > 0:
                rows.append({
                    'total_files': document['doc_count'],
                    'total_obs': int(document['total_obs']['value']),
                    timescale: document['key_as_string']
                })

        response = {
            'total_files': total_files,
            'metrics': rows
        }

        return 'application/json', response

    def __repr__(self):
        return '<MetricsProcessor> {}'.format(self.name)
