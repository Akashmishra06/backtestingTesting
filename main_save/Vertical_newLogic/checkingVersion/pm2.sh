cd "/root/AkashMockAlgo/checkingVersion"
/usr/local/bin/pm2 start "strategyLauncher.py" --interpreter="/root/AkashMockAlgo/venv/bin/python3" --name="checkingVersion-1" --no-autorestart --time