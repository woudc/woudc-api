# =================================================================
#
# Authors: Kevin Ngai <kevin.ngai@ec.gc.ca>
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

import os
import logging

from elasticsearch import Elasticsearch, exceptions
from elastic_transport import TlsError

from pygeoapi.provider.elasticsearch_ import ElasticsearchProvider
from pygeoapi.provider.base import (ProviderConnectionError,
                                    ProviderQueryError)

LOGGER = logging.getLogger(__name__)


class ElasticsearchWOUDCProvider(ElasticsearchProvider):
    """Custom Elasticsearch Provider for WOUDC"""

    def __init__(self, provider_def):
        """
        Initialize object with custom behavior for WOUDC

        :param provider_def: provider definition

        :returns: woudc_api.provider.elasticsearch.ElasticsearchWOUDCProvider
        """
        LOGGER.debug('Initializing ElasticsearchWOUDCProvider')
        LOGGER.debug(f'provider_def: {provider_def}')

        # Ensure that 'properties' attribute is set up
        self.properties = getattr(self, 'properties', {})
        self.select_properties = getattr(self, 'select_properties', [])

        # Extract from provider_def

        # Call BaseProvider.__init__ directly.
        # Don't use ElasticsearchProvider.__init__
        # with super().__init__(provider_def).
        from pygeoapi.provider.base import BaseProvider
        BaseProvider.__init__(self, provider_def)

        LOGGER.debug('Setting WOUDC specific Elasticsearch properties')

        self.verify_certs = os.getenv(
                            'WOUDC_API_VERIFY_CERTS',
                            'True').strip().lower() in ('true', '1', 'yes')

        # Extract URL information from self.data
        self.es_host, self.index_name = self.data.rsplit('/', 1)

        LOGGER.debug(
            f"Connecting to Elasticsearch (verify_certs={self.verify_certs})"
        )

        try:
            self.es = Elasticsearch(
                self.es_host,
                verify_certs=self.verify_certs
            )
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
            raise ProviderConnectionError(msg)

        if not self.es.ping():
            msg = f"Cannot connect to Elasticsearch: {self.es_host}"
            LOGGER.error(msg)
            raise ProviderConnectionError(msg)

        LOGGER.debug('Determining ES version')
        v = self.es.info()['version']['number'][:3]
        if float(v) < 8:
            msg = 'only ES 8+ supported'
            LOGGER.error(msg)
            raise ProviderConnectionError(msg)

        LOGGER.debug('Grabbing field information')
        try:
            self._fields = self.get_fields()
        except exceptions.NotFoundError as err:
            LOGGER.error(err)
            raise ProviderQueryError(err)

    # def query(self, offset=0, limit=10, resulttype='results',
    #           bbox=[], datetime_=None, properties=[], sortby=[],
    #           select_properties=[], skip_geometry=False, q=None,
    #           filterq=None, **kwargs):

    #     language = kwargs.get('language')
    #     if language is not None:
    #         language = language.language
    #     else:
    #         language = 'en'

    #     new_features = []

    #     records = super().query(
    #         offset=offset, limit=limit,
    #         resulttype=resulttype, bbox=bbox,
    #         datetime_=datetime_, properties=properties,
    #         sortby=sortby,
    #         select_properties=select_properties,
    #         skip_geometry=skip_geometry,
    #         q=q)

    #     if self.index_name.endswith('discovery_metadata'):
    #         LOGGER.debug('Intercepting default ES response')
    #         for feature in records['features']:
    #             if feature['id'].endswith(language):
    #                 feature['id'] = feature['id'].rsplit(f'_{language}')[0]
    #                 new_features.append(feature)
    #         records['features'] = new_features
    #         records['numberMatched'] = len(records['features']) + offset
    #         records['numberReturned'] = len(records['features'])

    #     return records

    # def get(self, identifier, **kwargs):
    #     """
    #     Get ES document by id

    #     :param identifier: feature id

    #     :returns: dict of single GeoJSON feature
    #     """

    #     language = kwargs.get('language')
    #     if language is not None:
    #         language = language.language
    #     else:
    #         language = 'en'

    #     LOGGER.info('Getting identifier: %s with language: %s',
    #                 identifier, language)

    #     if self.index_name.endswith('discovery_metadata'):
    #         identifier2 = f'{identifier}_{language}'
    #     else:
    #         identifier2 = identifier

    #     dataset = super().get(identifier2, **kwargs)

    #     dataset['id'] = dataset['id'].rsplit(f'_{language}')[0]

    #     return dataset
