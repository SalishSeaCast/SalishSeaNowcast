# cron script to run Salish Sea NEMO model nowcast weather download worker.
#
# usage:
#   MEOPAR=/data/dlatorne/MEOPAR
#   NOWCAST_TOOLS=tools/SalishSeaTools/salishsea_toola/nowcast
#   0 3 * * *  ${MEOPAR}/${NOWCAST_TOOLS}/workers/weather_06_download.cron.sh

PYTHON=/home/dlatorne/anaconda/envs/nowcast/bin/python
NOWCAST=/home/dlatorne/public_html/MEOPAR/nowcast
CONFIG=${NOWCAST}/nowcast.yaml
${PYTHON} -m salishsea_tools.nowcast.workers.download_weather ${CONFIG} 06
