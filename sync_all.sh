#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Step 1: UltraDNS sync ==="
python3 ultradns.py

echo "=== Step 2: Cloudflare DNS sync ==="
python3 cloudflare_dns.py

echo "=== Step 3: Local DNS CSV sync ==="
python3 import_local_dns.py
