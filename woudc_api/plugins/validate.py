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
# Copyright (c) 2022 Government of Canada
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
from woudc_extcsv import (ExtendedCSV, MetadataValidationError,
                          NonStandardDataError)

LOGGER = logging.getLogger(__name__)


PROCESS_SETTINGS = {
    'id': 'woudc-data-registry-validate',
    'title': 'WOUDC Data Registry Search Page Helper',
    'description': 'A WOUDC Data Registry Extended CSV extension that'
                   ' validates the format of the inputted extended CSV'
                   ' object, with resulting error and warnings in the output.',
    'keywords': [],
    'links': [],
    'inputs': {
        'extcsv': {
            'title': 'Extended CSV for validation',
            'schema': {
                'type': 'string'
            },
            'minOccurs': 1,
            'maxOccurs': 1
        },
        'check_metadata': {
            'title': 'Perform Quality Assurance',
            'schema': {
                'type': 'bool'
            },
            'minOccurs': 0,
            'maxOccurs': 1
        }
    },
    'outputs': {
        'woudc-data-registry-validate-response': {
            'title': 'WOUDC Data Registry Validator Output',
            "schema": {
                "type": "object",
                "contentMediaType": "application/json"
            }
        }
    },
    'example': {
        'inputs': {
            'extcsv': '',
        }
    }
}

location_settings = {
  'latitude_error_distance': 1.0,
  'longitude_error_distance': 1.0,
  'height_error_distance': 50.0,
  'polar_ignore_longitude': True,
  'polar_latitude_range': 1.0,
  'ships_ignore_location': False,
}


class ExtendedCSVProcessor(BaseProcessor):
    """
    WOUDC Data Registry API extension for validating Extended CSV.

    Returns JSON output of a pass or fail message, along with error
    and warning messages.
    """

    def __init__(self, provider_def):
        """
        Initialize object

        :param provider_def: Provider definition?
        :returns: `woudc_api.plugins.validate.ExtendedCSVProcessor`
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

        LOGGER.debug(f"Host: {host}")
        LOGGER.debug(f"Index prefix name: {self.index_prefix}")

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

    def check_project(self):
        """
        Validates the instance's Extended CSV source file's
        #CONTENT.Class value by comparison with aggregation
        query results. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #CONTENT.Class
                  value was successfully validated.
        """

        success = True
        index = 'project'
        field = 'identifier'
        buckets = self.query_aggregations(index, field)
        projects = []
        for subbucket in buckets:
            projects += [subbucket['key']]
        if self.project not in projects:
            valueline = self.ecsv.line_num('CONTENT') + 2
            if not self.ecsv._add_to_report(51, valueline, value=self.project):
                success = False
        return success

    def check_dataset(self):
        """
        Validates the instance's Extended CSV source file's
        #CONTENT.Category value by comparison with aggregation
        query results. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #CONTENT.Category
                  value was successfully validated.
        """

        success = True
        index = 'dataset'
        field = 'identifier'
        buckets = self.query_aggregations(index, field)
        datasets = []
        for subbucket in buckets:
            datasets += [subbucket['key']]
        datasets.append('UmkehrN14')
        if self.dataset not in datasets:
            valueline = self.ecsv.line_num('CONTENT') + 2
            if not self.ecsv._add_to_report(52, valueline, value=self.dataset):
                success = False
        return success

    def check_content(self):
        """
        Validates the instance's Extended CSV source file's
        #CONTENT.Level and #CONTENT.Form by comparison with
        discovery metadata. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #CONTENT.Level and
                  #CONTENT.Form validated successfully.
        """
        success = True
        valueline = self.ecsv.line_num('CONTENT') + 2

        if not isinstance(self.form, int):
            try:
                if not self.ecsv._add_to_report(57, valueline,
                                                oldvalue=self.form,
                                                newvalue=int(self.form)):
                    success = False
                self.form = int(self.form)
            except ValueError:
                if not self.ecsv._add_to_report(58, valueline):
                    success = False

        if not isinstance(self.level, float):
            try:
                newvalue = float(self.level)
                if not self.ecsv._add_to_report(54, valueline,
                                                oldvalue=self.level,
                                                newvalue=newvalue):
                    success = False
                self.level = newvalue
            except ValueError:
                if not self.ecsv._add_to_report(55, valueline):
                    success = False

        if self.dataset == 'UmkehrN14':
            if 'C_PROFILE' in self.ecsv.extcsv:
                if self.level != 2.0:
                    if not self.ecsv._add_to_report(53, valueline, value=2.0):
                        success = False
                    self.level = 2.0
            elif self.level != 1.0:
                if not self.ecsv._add_to_report(53, valueline, value=1.0):
                    success = False
                self.level = 1.0
            self.dataset += '_' + str(self.level)

        if not success:
            return success

        index = 'discovery_metadata'
        field = 'identifier'
        content_body = self.query_by_field(index, field, self.dataset)
        _levels = content_body[0]['_source']['properties']['levels']
        levels = []
        for level in _levels:
            label = level['label_en']
            levels.append(label[len(label)-3:])

        if str(self.level) not in levels:
            if not self.ecsv._add_to_report(56, valueline,
                                            dataset=self.dataset):
                success = False

        return success

    def check_contributor(self):
        """
        Validates the instance's Extended CSV source file's
        #DATA_GENERATION.Agency by comparison with query results.
        Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #DATA_GENERATION.Agency
                  value was successfully validated.
        """

        success = True
        index = self.index_prefix + 'contributor'
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "properties.project.raw": self.project,
                            }
                        },
                        {
                            "match": {
                                "properties.acronym.raw": self.agency,
                            }
                        }
                    ]
                }
            }
        }
        response = self.es.search(index=index, body=query)
        contributor_body = response['hits']['hits']
        if len(contributor_body) != 1:
            valueline = self.ecsv.line_num('DATA_GENERATION') + 2
            if not self.ecsv._add_to_report(67, valueline):
                success = False
        return success

    def check_station(self):
        """
        Validates the instance's Extended CSV source file's
        #PLATFORM table by comparison with query results.
        Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #PLATFORM table
                  was successfully validated.
        """

        success = True
        valueline = self.ecsv.line_num('PLATFORM') + 2

        LOGGER.debug('Validating station {}:{}'.format(
            self.station_id, self.station_name)
        )
        water_codes = ['*IW', 'IW', 'XZ']
        if self.station_type == 'SHP' and any([
            not self.country, self.country in water_codes
        ]):
            self.country = 'XY'
            if not self.ecsv._add_to_report(75, valueline):
                success = False

        if len(self.station_id) < 3:
            if not self.ecsv._add_to_report(70, valueline):
                success = False

        self.station_id = self.station_id.rjust(3, '0')

        LOGGER.debug('Validating WOUDC station id...')
        index = 'station'
        field = 'woudc_id'
        station_body = self.query_by_field(index, field, self.station_id)
        if len(station_body) != 1:
            if not self.ecsv._add_to_report(71, valueline):
                success = False
                return success

        station_properties = station_body[0]['_source']['properties']
        LOGGER.debug('Validating station type...')
        platform_types = ['STN', 'SHP']
        if self.station_type in platform_types and \
                self.station_type == station_properties['type']:
            LOGGER.debug('Validated station type {}'.format(self.station_type))
        else:
            if not self.ecsv._add_to_report(72, valueline):
                success = False

        LOGGER.debug('Validating station name...')
        if station_properties['name'] == self.station_name:
            LOGGER.debug('Validated with name {} for id {}'.format(
                self.station_name, self.station_id))
        else:
            if not self.ecsv._add_to_report(73, valueline):
                success = False

        if not success:
            return success

        LOGGER.debug('Validating station country...')

        index = 'country'
        field = 'identifier'
        country_body = self.query_by_field(index, field, self.country)
        if len(country_body) != 1:
            if not self.ecsv._add_to_report(74, valueline):
                success = False
        else:
            country_properties = country_body[0]['_source']['properties']
            country_name_en = country_properties['country_name_en']
            if country_name_en != station_properties['country_name_en']:
                if not self.ecsv._add_to_report(74, valueline):
                    success = False
            else:
                LOGGER.debug('Validated with country: {} for id: {}'
                             .format(country_name_en, self.country))
        return success

    def check_deployment(self):
        """
        Validates the instance's Extended CSV source file's
        deployment by creating the corresponding instrument ID and
        searching for it. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's corresponding deployment
                  was found in the deployment index.
        """

        success = True
        deployment_id = ':'.join([self.station_id, self.agency, self.project])

        index = 'deployment'
        field = 'identifier'
        deployment_body = self.query_by_field(index, field, deployment_id)
        if len(deployment_body) != 1:
            valueline = self.ecsv.line_num('PLATFORM') + 2
            if not self.ecsv._add_to_report(88, valueline,
                                            ident=deployment_id):
                success = False
        return success

    def check_instrument_name_and_model(self):
        """
        Validates the instance's Extended CSV source file's
        #INSTRUMENT.Name and #INSTRUMENT.Model values by querying for
        them in the instrument index. True if no errors were encountered.

        :returns: `bool` of whether the input file's #INSTRUMENT.Name and
                  #INSTRUMENT.Model were found in the instrument index.
        """

        success = True
        index = 'instrument'
        valueline = self.ecsv.line_num('INSTRUMENT') + 2

        if not self.instrument_name or \
                self.instrument_name.lower() in ['na', 'n/a']:
            if not self.ecsv._add_to_report(82, valueline):
                success = False
            self.instrument_name = 'UNKNOWN'
        else:
            # Check data registry for matching instrument name
            field = 'name'
            buckets = self.query_aggregations(index, field)
            names = []
            for subbucket in buckets:
                names += [subbucket['key']]
            if self.instrument_name not in names:
                if not self.ecsv._add_to_report(85, valueline,
                                                value=self.instrument_name):
                    success = False

        if not self.instrument_model or str(
            self.instrument_model
        ).lower() in ['na', 'n/a']:
            if not self.ecsv._add_to_report(83, valueline):
                success = False
            self.instrument_model = 'UNKNOWN'
        else:
            # Check data registry for matching instrument model
            field = 'model'
            buckets = self.query_aggregations(index, field)
            models = []
            for subbucket in buckets:
                models += [subbucket['key']]
            if self.instrument_model not in models:
                if not self.ecsv._add_to_report(86, valueline):
                    success = False
        return success

    def check_instrument(self):
        """
        Validates the instance's Extended CSV source file's
        #INSTRUMENT table by creating the corresponding instrument ID
        and searching for it. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #INSTRUMENT table
                  collectively validated successfully.
        """

        success = True
        if not self.instrument_number or str(
            self.instrument_number
        ).lower() in ['na', 'n/a']:
            self.instrument_number = 'UNKNOWN'
        self.build_instrument_id()

        index = 'instrument'
        field = 'identifier'
        instrument_body = self.query_by_field(index, field, self.instrument_id)
        if len(instrument_body) != 1:
            valueline = self.ecsv.line_num('INSTRUMENT') + 2
            if not self.ecsv._add_to_report(87, valueline):
                success = False
        return success

    def check_location(self):
        """
        Validates the instance's Extended CSV source file's
        #LOCATION table by checking the geometry of the corresponding
        instrument document in the instrument index. Returns True if
        no errors were encountered.

        :returns: `bool` of whether the input file's #LOCATION values
                  match the results found in the instrument index.
        """

        success = True
        valueline = self.ecsv.line_num('LOCATION') + 2
        try:
            lat_numeric = float(self.latitude)
            if -90 <= lat_numeric <= 90:
                LOGGER.debug('Validated instrument latitude')
            elif not self.ecsv._add_to_report(78, valueline, field='Latitude',
                                              lower=-90, upper=90):
                success = False
        except ValueError:
            if not self.ecsv._add_to_report(76, valueline, field='Longitude'):
                success = False

            self.latitude = lat_numeric = None

        try:
            lon_numeric = float(self.longitude)
            if -180 <= lon_numeric <= 180:
                LOGGER.debug('Validated instrument longitude')
            elif not self.ecsv._add_to_report(78, valueline, field='Longitude',
                                              lower=-180, upper=180):
                success = False
        except ValueError:
            if not self.ecsv._add_to_report(76, valueline, field='Longitude'):
                success = False

            self.longitude = lon_numeric = None

        try:
            height_numeric = float(self.height) if self.height else None
            if not self.height or -50 <= height_numeric <= 5100:
                LOGGER.debug('Validated instrument height')
            elif not self.ecsv._add_to_report(79, valueline, lower=-50,
                                              upper=5100):
                success = False
        except ValueError:
            if not self.ecsv._add_to_report(77, valueline):
                success = False

            self.height = height_numeric = None

        ignore_ships = not location_settings['ships_ignore_location']

        if not success:
            return success
        elif self.station_type == 'SHP' and ignore_ships:
            LOGGER.debug('Not validating shipboard instrument location')
            return success
        else:
            index = 'instrument'
            field = 'identifier'
            location_body = self.query_by_field(index, field,
                                                self.instrument_id)
            coordinates = location_body[0]['_source']['geometry'][
                    'coordinates'
            ]

            lat_interval = location_settings['latitude_error_distance']
            lon_interval = location_settings['longitude_error_distance']
            height_interval = location_settings['height_error_distance']

            polar_latitude_range = location_settings['polar_latitude_range']
            ignore_polar_lon = location_settings['polar_ignore_longitude']

            in_polar_region = lat_numeric is not None \
                and abs(lat_numeric) > 90 - polar_latitude_range

            if lat_numeric is not None and coordinates[1] is not None \
               and abs(lat_numeric - coordinates[1]) >= lat_interval:
                if not self.ecsv._add_to_report(80, valueline,
                                                field='Latitude'):
                    success = False
            if lon_numeric is not None and coordinates[0] is not None:
                if in_polar_region and ignore_polar_lon:
                    LOGGER.info('Skipping longitude check in polar region')
                elif abs(lon_numeric - coordinates[0]) >= lon_interval:
                    if not self.ecsv._add_to_report(80, valueline,
                                                    field='Longitude'):
                        success = False
            if height_numeric is not None and coordinates[2] is not None \
               and abs(height_numeric - coordinates[2]) >= height_interval:
                if not self.ecsv._add_to_report(81, valueline):
                    success = False

        return success

    def check_data_generation(self):
        """
        Validates the instance's Extended CSV source file's
        #DATA_GENERATION.Date and #DATA_GENERATION.Version by comparison
        with other tables. Returns True if no errors were encountered.

        :returns: `bool` of whether the input file's #DATA_GENERATION table
                  collectively validated successfully.
        """
        success = True

        valueline = self.ecsv.line_num('DATA_GENERATION')
        if not self.dg_date:
            if not self.ecsv._add_to_report(62, valueline):
                success = False

        try:
            numeric_version = float(self.version)
        except TypeError:
            if not self.ecsv._add_to_report(63, valueline, default=1.0):
                success = False
            return success
        if not 0 <= numeric_version <= 20:
            if not self.ecsv._add_to_report(64, valueline, lower=0.0,
                                            upper=20.0):
                success = False
        if str(self.version) == str(int(numeric_version)):
            if not self.ecsv._add_to_report(65, valueline):
                success = False

        return success

    def check_time_series(self):
        """
        Validate the input Extended CSV source file's dates across all tables
        to ensure that no date is more recent that #DATA_GENERATION.Date.

        :returns: `bool` of whether the input file's time fields collectively
                  validated successfully.
        """

        success = True

        for table, body in self.ecsv.extcsv.items():
            if table == 'DATA_GENERATION':
                continue

            valueline = self.ecsv.line_num(table) + 2

            date_column = body.get('Date', [])
            if not isinstance(date_column, list):
                date_column = [date_column]

            for line, other_date in enumerate(date_column, valueline):
                if (isinstance(other_date, (str, int, type(None)))
                   or isinstance(self.dg_date, (str, int, type(None)))):
                    err_code = 91 if table.startswith('TIMESTAMP') else 92
                    if not self.ecsv._add_to_report(err_code, line,
                                                    table=table):
                        success = False
                else:
                    if other_date > self.dg_date:
                        err_code = 91 if table.startswith('TIMESTAMP') else 92
                        if not self.ecsv._add_to_report(err_code,
                                                        line, table=table):
                            success = False

            time_column = body.get('Time', [])
            if not isinstance(time_column, list):
                time_column = [time_column]

            if self.ts_time:
                for line, other_time in enumerate(time_column, valueline):
                    if (isinstance(other_time, (str, int, type(None)))
                       or isinstance(self.ts_time, (str, int, type(None)))):
                        pass
                    elif other_time < self.ts_time:
                        if not self.ecsv._add_to_report(93, line):
                            success = False

        return success

    def build_instrument_id(self):
        """
        Creates and returns an Instrument instance from the contents of
        the inputted csv
        """
        id_elements = [self.instrument_name, self.instrument_model,
                       self.instrument_number, self.dataset,
                       self.station_id, self.agency, self.project]
        self.instrument_id = ':'.join(id_elements)

    def query_by_field(self, index, field, value):
        """
        Query Elasticsearch index data by field

        :param index: Name of index to query to
        :param field: Field name to be queried
        :param value: Value of the field in any query results
        :returns: List of query results
        """

        _index = self.index_prefix + index
        query = {
            "query": {
                "term": {
                    "properties." + field + ".raw": value,
                }
            }
        }
        response = self.es.search(index=_index, body=query)
        response_body = response['hits']['hits']
        return response_body

    def query_aggregations(self, index, field):
        """
        Query Elasticsearch index for aggregations
        (distinct values and value counts)

        :param index: Name of index to query to
        :param field: Field name to be queried
        :returns: List of aggregation results
        """

        _index = self.index_prefix + index
        query = {
            'size': 0,
            'aggregations': {
                'aggregation': {
                    'terms': {
                        'field': 'properties.' + field + '.raw',
                        'order': {'_key': 'asc'},
                        'size': 10000
                    }
                }
            },
        }

        response = self.es.search(index=_index, body=query)
        response_body = response['aggregations']['aggregation']
        buckets = response_body['buckets']
        return buckets

    def execute(self, inputs: dict, **kwargs):
        """
        Responds to an incoming request to this endpoint of the API.

        :param inputs: Body of the incoming request.
        :param metadata_only: True or False to relax checks
                              - defaults to False
        :returns: Body of the response sent for that request.
        """

        metadata_only = kwargs.get("metadata_only", False)
        extcsv = inputs.get('extcsv', None)
        check_metadata = inputs.get('check_metadata', None)

        self.success = True
        try:
            self.ecsv = ExtendedCSV(extcsv)
        except (MetadataValidationError, NonStandardDataError):
            self.ecsv = ExtendedCSV('')
            self.ecsv._add_to_report(209)
            self.success = False

        if self.success:
            try:
                self.ecsv.validate_metadata_tables()
                self.ecsv.validate_dataset_tables()
            except (MetadataValidationError, NonStandardDataError):
                self.success = False

        if self.success and check_metadata:
            # Perform metadata checks
            self.project = self.ecsv.extcsv['CONTENT']['Class']
            self.dataset = self.ecsv.extcsv['CONTENT']['Category']
            self.level = self.ecsv.extcsv['CONTENT']['Level']
            self.form = self.ecsv.extcsv['CONTENT']['Form']
            self.agency = self.ecsv.extcsv['DATA_GENERATION']['Agency']
            self.dg_date = self.ecsv.extcsv['DATA_GENERATION']['Date']
            self.version = \
                self.ecsv.extcsv['DATA_GENERATION'].get('Version', None)
            self.station_type = self.ecsv.extcsv['PLATFORM']['Type']
            self.station_id = str(self.ecsv.extcsv['PLATFORM']['ID'])
            self.station_name = self.ecsv.extcsv['PLATFORM']['Name']
            self.country = self.ecsv.extcsv['PLATFORM']['Country']
            self.instrument_name = self.ecsv.extcsv['INSTRUMENT']['Name']
            self.instrument_model = \
                str(self.ecsv.extcsv['INSTRUMENT']['Model'])
            self.instrument_number = \
                str(self.ecsv.extcsv['INSTRUMENT']['Number'])
            self.latitude = self.ecsv.extcsv['LOCATION']['Latitude']
            self.longitude = self.ecsv.extcsv['LOCATION']['Longitude']
            self.height = self.ecsv.extcsv['LOCATION'].get('Height', None)
            self.ts_date = self.ecsv.extcsv['TIMESTAMP']['Date']
            self.ts_time = self.ecsv.extcsv['TIMESTAMP'].get('Time', None)

            # Check project
            LOGGER.debug('Validating project')
            project_ok = self.check_project()

            # Check dataset
            LOGGER.debug('Validating dataset')
            dataset_ok = self.check_dataset()

            # Check content level and form
            if dataset_ok:
                LOGGER.info('Validating content and form')
                self.check_content()
            else:
                LOGGER.warning('Skipping content and form check: depends on'
                               ' values with errors')

            # Check contributor
            LOGGER.debug('Validating contributor')
            if not project_ok:
                LOGGER.warning('Skipping contributor check: depends on'
                               ' values with errors')
                contributor_ok = False
            else:
                contributor_ok = self.check_contributor()

            # Check station
            LOGGER.debug('Validating station')
            platform_ok = self.check_station()

            # Check deployment
            if not all([project_ok, contributor_ok, platform_ok]):
                LOGGER.warning('Skipping deployment check: depends on'
                               ' values with errors')
            else:
                LOGGER.debug('Validating agency deployment')
                self.check_deployment()

            # Check instrument name and model
            LOGGER.debug('Validating instrument')
            instrument_model_ok = self.check_instrument_name_and_model()
            if not all([
                dataset_ok, platform_ok, contributor_ok, instrument_model_ok
            ]):
                LOGGER.warning('Skipping instrument check: depends on'
                               ' values with errors')
                instrument_ok = False
            else:
                instrument_ok = self.check_instrument()

            # Check location
            if not instrument_ok:
                LOGGER.info('Validating location')
            else:
                LOGGER.warning('Skipping location check: depends on'
                               ' values with errors')
                self.check_location()

            # Check data generation date and version
            LOGGER.info('Validating data generation version')
            self.check_data_generation()

            # Check time series
            if metadata_only:
                LOGGER.info("""Lax mode detected. NOT validating
                            dataset-specific tables""")
            else:
                LOGGER.info('Validating time series')
                self.check_time_series()

            self.success = len(self.ecsv.errors) == 0

        summary = {
                'response': self.success,
                'errors': self.ecsv.errors,
                'warnings': self.ecsv.warnings
                }

        return 'application/json', summary
