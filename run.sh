#! /bin/bash
pip install -r /downloader/requirements.txt
apt-get update && apt-get install -y ffmpeg

while :; do
  git pull --rebase
  python /downloader/main.py -o $OUTFOLDER
  sleep 108000
done
