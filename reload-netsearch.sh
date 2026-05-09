#!/bin/bash
kill $(lsof -ti :3002) 2>/dev/null
sleep 2
cd /home/local/SSO/yt0115/NetSearch_sqlite
npm run dev >> /tmp/netsearch.log 2>&1 &
