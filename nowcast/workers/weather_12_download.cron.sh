# cron script to run Salish Sea NEMO model nowcast weather download worker.
#
# usage:
#   NOWCAST=/results/nowcast-sys
#   WORKERS=tools/SalishSeaNowcast/nowcast/workers
#   0 10 * * *  ${NOWCAST}/${WORKERS}/weather_12_download.cron.sh

PYTHON=/results/nowcast-sys/nowcast-env/bin/python
# NOWCAST=/home/dlatorne/public_html/MEOPAR/nowcast
# CONFIG=${NOWCAST}/nowcast.yaml
NOWCAST=/results/nowcast-sys/nowcast
CONFIG=${NOWCAST}/nowcast.yaml
${PYTHON} -m nowcast.workers.download_weather ${CONFIG} 12
