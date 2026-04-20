import requests

# Fetch latest block hash, then full block data
tip_hash = requests.get("https://blockstream.info/api/blocks/tip/hash").text.strip()
data = requests.get(f"https://blockstream.info/api/block/{tip_hash}").json()

# Leading zeros in hash are the visible result of Proof of Work
# 'bits' encodes the compact 256-bit target T: SHA256(SHA256(header)) must be < T
print(f"Height : {data['height']}")
print(f"Hash   : {data['id']}")       # observe leading 000000...
print(f"Bits   : {data['bits']}")     # compact target encoding
print(f"Nonce  : {data['nonce']}")
print(f"Txs    : {data['tx_count']}")