#! /bin/bash
pip install -r /downloader/requirements.txt
apt install ffmpeg -y

while :; do
  git pull --rebase
  python /downloader/main.py -o $OUTFOLDER
  sleep 108000
done
