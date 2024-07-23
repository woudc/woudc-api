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

import logging
import urllib.parse

from elasticsearch import Elasticsearch, exceptions

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

        # Extract URL information from self.data
        self.es_host, self.index_name = self.data.rsplit('/', 1)
        parsed_url = urllib.parse.urlparse(self.es_host)
        # Extract username and password for auth, if available
        if parsed_url.username and parsed_url.password:
            auth = (parsed_url.username, parsed_url.password)
        else:
            LOGGER.error('ES username and password was undefined. Did you \
                         forget to load your env variables before compiling?')
            auth = None

        LOGGER.debug(f'host: {self.es_host}')
        LOGGER.debug(f'index: {self.index_name}')

        LOGGER.debug('Connecting to Elasticsearch')
        self.es = Elasticsearch(
            [self.es_host],
            http_auth=auth,
            verify_certs=False  # Bypass SSL verification
        )
        if not self.es.ping():
            msg = f'Cannot connect to Elasticsearch: {self.es_host}'
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
