#! /bin/bash
pip install -r requirements.txt

while :; do
  git pull --rebase
  python main.py -o $OUTFOLDER
  sleep 108000
done
