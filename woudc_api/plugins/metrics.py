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
from elastic_transport import TlsError

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
    'inputs': {
        'domain': {
            'title': 'Metric Domain',
            'schema': {
                'type': 'string',
                'enum': [
                    'dataset',
                    'contributor',
                ]
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        'timescale': {
            'title': 'Time Scale',
            'schema': {
                'type': 'string',
                'enum': [
                    'year',
                    'month',
                ]
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        'bbox': {
            'title': 'Bounding Box',
            'schema': {
                'type': 'array',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        'dataset': {
            'title': 'Dataset Filter',
            'schema': {
                'type': 'string',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        'level': {
            'title': 'Data Level Filter',
            'schema': {
                'type': 'string',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        'country': {
            'title': 'Country Filter',
            'schema': {
                'type': 'string',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        'station': {
            'title': 'Station Filter',
            'schema': {
                'type': 'string',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        },
        'network': {
            'title': 'Instrument Filter',
            'schema': {
                'type': 'string',
            },
            'minOccurs': 0,
            'maxOccurs': 1
        }
    },
    'outputs': {
        'woudc-data-registry-metrics-response': {
            'title': 'WOUDC Data Registry Metrics Output',
            'schema': {
                'type': 'object',
                'contentMediaType': 'application/json'
            }
        }
    },
    'example': {
        'inputs': {
            'domain': 'contributor',
            'timescale': 'year',
            'network': 'Brewer',
            'country': 'CAN'
        }
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

        LOGGER.debug('Setting Elasticsearch properties')
        es_url = os.getenv('WOUDC_API_ES_URL',
                           'http://elastic:password@localhost:9200')
        self.verify_certs = os.getenv(
                            'WOUDC_API_VERIFY_CERTS',
                            'True').strip().lower() in ('true', '1', 'yes')
        host = es_url.split('@', 1)[-1]

        self.index_prefix = os.getenv('WOUDC_API_ES_INDEX_PREFIX',
                                      'woudc_data_registry') + '.'
        self.index = self.index_prefix + 'data_record'

        LOGGER.debug(f"Host: {host}")
        LOGGER.debug(f"Index name: {self.index}")

        LOGGER.debug(
            f"Connecting to Elasticsearch (verify_certs=${self.verify_certs})"
        )
        try:
            self.es = Elasticsearch(es_url, verify_certs=self.verify_certs)
        except TlsError as err:
            if self.verify_certs:
                msg = (
                    f"SSL certificate verification failed: {err}.\n"
                    "Check your SSL certificates or set "
                    "WOUDC_API_VERIFY_CERTS=False if "
                    "connecting to an internal dev server."
                )
            else:
                msg = f"Unexpected TLS error: {err}"

            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

        if not self.es.ping():
            msg = f"Cannot connect to Elasticsearch: {host}"
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

        LOGGER.debug('Checking Elasticsearch version')
        version = float(self.es.info()['version']['number'][:3])
        if version < 8:
            msg = (
                f"Elasticsearch version below 8 not supported ({version})"
            )
            LOGGER.error(msg)
            raise ProcessorExecuteError(msg)

    def execute(self, inputs: dict, **kwargs):
        """
        Responds to an incoming request to this endpoint of the API.

        :param inputs: Body of the incoming request.
        :returns: Body of the response sent for that request.
        """

        domain = inputs.pop('domain')
        timescale = inputs.pop('timescale')
        peer_records = False
        if 'dataset' in inputs:
            if inputs['dataset'] in ['peer_data_records',
                                     'ndacc_total',
                                     'ndacc_uv',
                                     'ndacc_vertical']:
                self.index = self.index_prefix + 'peer_data_record'
                peer_records = True

        if domain == 'dataset':
            return self.metrics_dataset(timescale, peer_records, **inputs)
        elif domain == 'contributor':
            return self.metrics_contributor(timescale, peer_records, **inputs)

    def generate_geo_shape_filter(self, minx, miny, maxx, maxy):
        return {
            'geo_shape': {
                'geometry': {
                    'shape': {
                        'type': 'envelope',
                        'coordinates': [
                            [minx, maxy],
                            [maxx, miny]
                        ]
                    },
                    'relation': 'within'
                }
            }
        }

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
        source = kwargs.get('source', None)
        country = kwargs.get('country', None)
        station = kwargs.get('station', None)
        network = kwargs.get('network', None)
        source = kwargs.get('source', None)
        bbox = kwargs.get('bbox', None)

        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        filters = []

        if peer_records:
            if dataset == 'ndacc_total':
                filters.append({'properties.measurement.raw': 'TOTALCOL'})
            if dataset == 'ndacc_uv':
                filters.append({'properties.measurement.raw': 'UV'})
            if dataset == 'ndacc_vertical':
                filters.append({'properties.measurement.raw': 'OZONE'})
            if dataset in ['ndacc_total', 'ndacc_uv', 'ndacc_vertical']:
                filters.append({'properties.source.raw': 'ndacc'})

            if source is not None:
                filters.append({'properties.source.raw': source})
            if country is not None:
                filters.append({'properties.platform_country.raw': country})
            if station is not None:
                filters.append({'properties.platform_id.raw': station})
            if network is not None:
                filters.append({'properties.instrument_name.raw': network})
            if bbox is not None:
                minx, miny, maxx, maxy = [float(b) for b in bbox]
            field = 'properties.start_datetime'
        else:
            if dataset is not None:
                filters.append({'properties.content_category.raw': dataset})
            if level is not None:
                filters.append({'properties.content_level': level})
            if country is not None:
                filters.append({'properties.platform_country.raw': country})
            if station is not None:
                filters.append({'properties.platform_id.raw': station})
            if network is not None:
                filters.append({'properties.instrument_name.raw': network})
            if bbox is not None:
                minx, miny, maxx, maxy = [float(b) for b in bbox]
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

        if bbox is not None:
            query['aggregations']['filters']['filter']['bool']['filter'] =\
                self.generate_geo_shape_filter(minx, miny, maxx, maxy)

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
        bbox = kwargs.get('bbox', None)

        if timescale == 'year':
            date_interval = '1y'
            date_format = 'yyyy'
        elif timescale == 'month':
            date_interval = '1M'
            date_format = 'yyyy-MM'
        date_aggregation_name = '{}ly'.format(timescale)

        filters = []
        if peer_records:
            if dataset == 'ndacc_total':
                filters.append({'properties.measurement.raw': 'TOTALCOL'})
            if dataset == 'ndacc_uv':
                filters.append({'properties.measurement.raw': 'UV'})
            if dataset == 'ndacc_vertical':
                filters.append({'properties.measurement.raw': 'OZONE'})
            if dataset in ['ndacc_total', 'ndacc_uv', 'ndacc_vertical']:
                filters.append({'properties.source.raw': 'ndacc'})

            if source is not None:
                filters.append({'properties.source.raw': source})
            if country is not None:
                filters.append({'properties.country_id.raw': country})
            if station is not None:
                filters.append({'properties.station_id.raw': station})
            if network is not None:
                filters.append({'properties.instrument_type.raw': network})
            if bbox is not None:
                minx, miny, maxx, maxy = [float(b) for b in bbox]
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
            if bbox is not None:
                minx, miny, maxx, maxy = [float(b) for b in bbox]
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

        if bbox is not None:
            query['aggregations']['filters']['filter']['bool']['filter'] =\
                self.generate_geo_shape_filter(minx, miny, maxx, maxy)

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
