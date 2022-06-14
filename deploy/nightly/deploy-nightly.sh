# =================================================================
#
# Author: Tom Kralidis <tom.kralidis@canada.ca>
#
# Copyright (c) 2021 Tom Kralidis
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

BASEDIR=/data/web/woudc-api-nightly
PYGEOAPI_GITREPO=https://github.com/geopython/pygeoapi.git
WOUDC_API_GITREPO=https://github.com/woudc/woudc-api.git
DAYSTOKEEP=7

export WOUDC_API_URL=https://gods-geo.woudc-dev.cmc.ec.gc.ca/woudc-api/nightly/latest/oapi/
export WOUDC_API_BIND_HOST=0.0.0.0/
export WOUDC_API_BIND_PORT=5000
export WOUDC_API_ES_URL=http://localhost:9200
export WOUDC_API_OGC_SCHEMAS_LOCATION=/data/web/woudc-api-nightly/latest/schemas.opengis.net


# you should be okay from here

DATETIME=`date +%Y%m%d`
TIMESTAMP=`date +%Y%m%d.%H%M`
NIGHTLYDIR=woudc-api-$TIMESTAMP

echo "Deleting nightly builds > $DAYSTOKEEP days old"

cd $BASEDIR

for f in `find . -type d -name "woudc-api-20*"`
do
    DATETIME2=`echo $f | awk -F- '{print $3}' | awk -F. '{print $1}'`
    let DIFF=(`date +%s -d $DATETIME`-`date +%s -d $DATETIME2`)/86400
    if [ $DIFF -gt $DAYSTOKEEP ]; then
        rm -fr $f
    fi
done

rm -fr latest
echo "Generating nightly build for $TIMESTAMP"
python3.8 -m venv --system-site-packages $NIGHTLYDIR && cd $NIGHTLYDIR
source bin/activate
git clone $WOUDC_API_GITREPO
git clone $PYGEOAPI_GITREPO
cd pygeoapi
pip3 install cython
pip3 install "click >= 7.1" pyproj==1.9.6
pip3 install -r requirements.txt
pip3 install flask_cors elasticsearch
python3.8 setup.py install
cd ../woudc-api
python3.8 setup.py install
cd ..

mkdir schemas.opengis.net
curl -O http://schemas.opengis.net/SCHEMAS_OPENGIS_NET.zip && unzip ./SCHEMAS_OPENGIS_NET.zip "ogcapi/*" -d schemas.opengis.net && rm -f ./SCHEMAS_OPENGIS_NET.zip

cp woudc-api/deploy/default/woudc-api-config.yml woudc-api/deploy/nightly
sed -i 's#basepath: /#basepath: /woudc-api/nightly/latest#' woudc-api/deploy/nightly/woudc-api-config.yml
sed -i 's^# cors: true^cors: true^' woudc-api/deploy/nightly/woudc-api-config.yml

pygeoapi openapi generate woudc-api/deploy/nightly/woudc-api-config.yml > woudc-api/deploy/nightly/woudc-api-openapi.yml
sed -i "s#http://schemas.opengis.net#$WOUDC_API_URL/schemas#g" woudc-api/deploy/nightly/woudc-api-openapi.yml

cd ..

ln -s $NIGHTLYDIR latest
chgrp dmsec -R $NIGHTLYDIR # ensure correct group permission
chmod -R 775 $NIGHTLYDIR # ensure group writable