#!/bin/sh
sudo apt install screen -y
cd /duino-coin/
python3 PC_Miner.py
while [ 1 ]; do
sleep 10
done
sleep 999
