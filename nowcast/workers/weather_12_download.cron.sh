# cron script to run Salish Sea NEMO model nowcast weather download worker.
#
# usage:
#   NOWCAST_PKG=/results/nowcast-sys/tools/SalishSeaNowcast
#   WORKERS=nowcast/workers
#   0 10 * * *  ${NOWCAST_PKG}/${WORKERS}/weather_12_download.cron.sh

PYTHON=/results/nowcast-sys/nowcast-env/bin/python
NOWCAST=/home/dlatorne/public_html/MEOPAR/nowcast
CONFIG=${NOWCAST}/nowcast.yaml
${PYTHON} -m nowcast.workers.download_weather ${CONFIG} 12
