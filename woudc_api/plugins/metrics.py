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
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': False,
                    'options': [
                        'dataset',
                        'contributor',
                    ]
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'timescale',
            'title': 'Time Scale',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': False,
                    'options': [
                        'year',
                        'month',
                    ]
                }
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        {
            'id': 'dataset',
            'title': 'Dataset Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True,
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'country',
            'title': 'Country Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True,
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'station',
            'title': 'Station Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True,
                }
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        {
            'id': 'network',
            'title': 'Instrument Filter',
            'literalDataDomain': {
                'dataType': 'string',
                'valueDefinition': {
                    'anyValue': True,
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


def wrap_filter(query, prop, value):
    """
    Returns a copy of the query argumnt, wrapped in an additional
    filter requiring the property named by <prop> have a certain value.

    :param query: An Elasticsearch aggregation query dictionary.
    :param prop: The name of a filterable property.
    :param value: Value for the property that the query will match.
    :returns: Query dictionary wrapping the original query in an extra filter.
    """

    property_to_field = {
        'dataset': 'properties.content_category',
        'country': 'properties.platform_country',
        'station': 'properties.platform_id',
        'network': 'properties.instrument_name'
    }
    field = property_to_field[prop]

    wrapper = {
        'size': 0,
        'aggregations': {
            prop: {
                'filter': {
                    'match': {
                        field: value
                    }
                },
                'aggregations': query['aggregations']
            }
        }
    }

    return wrapper


def unwrap_filter(response, category):
    """
    Strips one layer of aggregations (named by <category>) from
    a ElasticSearch query response, leaving it still in proper ES
    response format.

    :param response: An Elasticsearch aggregation response dictionary.
    :param category: Name of the topmost aggregation in the response.
    :returns: The same response, with one level of aggregation removed.
    """

    unwrapped = response.copy()
    unwrapped['aggregations'] = response['aggregations'][category]

    return unwrapped


def convert_to_rows(response, agg_layers, prefix={}):
    """
    Converts the hierarchical, dictionary type of response from an
    an Elasticsearch query into a more SQL-like list of rows (tuples).

    The Elasticsearch response is expected to have a specific format, where
    a series of bucket aggregations are nested in each other. The names of
    these aggregations are listed in order in <agg_layers>, from top to bottom.

    The bottom-level bucket (after all these nested aggregations) must contain
    a doc_count as well as a numerically-valued aggregation named total_obs.

    Each row of the output is a `dict` of values, matching each of the buckets
    described in <agg_layers> followed by doc_count and the total_obs value.
    The keys in the `dict` are descriptive terms, not necessarily the same as
    the property names in Elasticsearch.

    :param response: An Elasticsearch query response dictionary.
    :param agg_layers: List of aggregation names from top to bottom.
    :returns: Contents of the Elasticsearch response in list-of-rows format.
    """

    if 'aggregations' in response:
        response = response['aggregations']

    if len(agg_layers) == 0:
        total_files = response['doc_count']
        total_obs = int(response['total_obs']['value'])

        if total_files == 0:
            return []
        else:
            row = prefix.copy()
            row['total_files'] = total_files
            row['total_obs'] = total_obs

            return [row]
    else:
        layer_input_name, layer_output_name = agg_layers[0]
        remaining_layers = agg_layers[1:]

        rows = []
        for bucket in response[layer_input_name]['buckets']:
            if 'key_as_string' in bucket:
                key = bucket['key_as_string']
            else:
                key = bucket['key']

            next_prefix = prefix.copy()
            next_prefix[layer_output_name] = key

            rows.extend(convert_to_rows(bucket, remaining_layers, next_prefix))

        return rows


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

        url_tokens = os.environ.get('WDR_ELASTICSEARCH_URL').split('/')

        LOGGER.debug('Setting Elasticsearch properties')
        self.index = url_tokens[-1]
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

        if domain == 'dataset':
            return self.metrics_dataset(timescale, **inputs)
        elif domain == 'contributor':
            return self.metrics_contributor(timescale, **inputs)

    def metrics_dataset(self, timescale, **kwargs):
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

        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        query_core = {
            date_aggregation_name: {
                'date_histogram': {
                    'field': 'properties.timestamp_date',
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
                'total_files': {
                    'terms': {
                        'field': 'properties.content_category.raw'
                    },
                    'aggregations': {
                        'levels': {
                            'terms': {
                                'field': 'properties.content_level'
                            },
                            'aggregations': query_core
                        }
                    }
                }
            }
        }

        filterables = ['country', 'station', 'network']
        filterables.reverse()

        for category in filterables:
            if category in kwargs:
                query = wrap_filter(query, category, kwargs[category])

        response = self.es.search(index=self.index, body=query)
        filterables.reverse()

        for category in filterables:
            if category in kwargs:
                response = unwrap_filter(response, category)

        aggregation_names = [
            ('total_files', 'dataset'),
            ('levels', 'level'),
            (date_aggregation_name, timescale)
        ]
        rows = convert_to_rows(response, aggregation_names)

        return rows

    def metrics_contributor(self, timescale, **kwargs):
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

        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        query_core = {
            date_aggregation_name: {
                'date_histogram': {
                    'field': 'properties.timestamp_date',
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

        aggregation_defs = [
            ('total_files', 'properties.data_generation_agency.raw'),
            ('stations', 'properties.platform_id.raw'),
            ('datasets', 'properties.content_category.raw'),
            ('levels', 'properties.content_level'),
            ('instruments', 'properties.instrument_name.raw')
        ]
        aggregation_defs.reverse()

        for aggregation_name, field in aggregation_defs:
            query_core = {
                aggregation_name: {
                    'terms': {
                        'field': field
                    },
                    'aggregations': query_core
                }
            }

        query = {
            'size': 0,
            'aggregations': query_core
        }

        filterables = ['dataset', 'station', 'network']
        filterables.reverse()

        for category in filterables:
            if category in kwargs:
                query = wrap_filter(query, category, kwargs[category])

        response = self.es.search(index=self.index, body=query)
        filterables.reverse()

        for category in filterables:
            if category in kwargs:
                response = unwrap_filter(response, category)

        aggregation_names = [
            ('total_files', 'contributor'),
            ('stations', 'station'),
            ('datasets', 'dataset'),
            ('levels', 'level'),
            ('instruments', 'network'),
            (date_aggregation_name, timescale)
        ]
        rows = convert_to_rows(response, aggregation_names)

        return rows

    def __repr__(self):
        return '<MetricsProcessor> {}'.format(self.name)
