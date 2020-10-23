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

import click
from flask import Flask, redirect

from pygeoapi.flask_app import BLUEPRINT as pygeoapi_blueprint

app = Flask(__name__, static_url_path='/static')

app.url_map.strict_slashes = False
app.register_blueprint(pygeoapi_blueprint, url_prefix='/oapi')

try:
    from flask_cors import CORS
    CORS(app)
except ImportError:  # CORS handled by upstream server
    pass


@app.route('/')
def hello_world():
    return redirect('https://woudc.org/about/data-access.php#web-services',
                    code=302)


@click.command()
@click.pass_context
def serve(ctx):
    """
    Serve woudc-api via Flask. Runs woudc-api
    as a flask server. Not recommend for production.
    :returns: void
    """

    HOST = os.environ.get('WOUDC_API_BIND_HOST', '0.0.0.0')
    PORT = os.environ.get('WOUDC_API_BIND_PORT', 5000)

    app.run(debug=True, host=HOST, port=PORT)


if __name__ == '__main__':  # run locally, for testing
    serve()
