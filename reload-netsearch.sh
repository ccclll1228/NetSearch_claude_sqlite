#!/bin/bash
export PATH=/root/.nvm/versions/node/v20.20.2/bin:/usr/local/bin:/usr/bin:/bin:$PATH

# 精準殺掉 3002
kill $(lsof -ti :3002) 2>/dev/null
sleep 3

cd /home/local/SSO/yt0115/NetSearch_sqlite

nohup npm run dev >> /tmp/netsearch.log 2>&1 &

echo "[$(date)] restarted PID=$!" >> /tmp/netsearch-restart.log
