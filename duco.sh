#!/bin/sh
sudo apt install screen -y
git clone https://github.com/AllCoinCrypto/duino-coin/
cd /duino-coin/
python3 PC_Miner.py
while [ 1 ]; do
sleep 2
done
sleep 6
