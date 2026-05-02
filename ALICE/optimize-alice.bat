@echo off
echo Optimizing Alice for Lower Latency...

REM Set environment variables for better performance
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1

REM Set Windows high performance mode
powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

REM Increase process priority for Alice
echo Starting Alice with optimized settings...

cd agent-starter-react
start /HIGH "Alice Frontend" cmd /k "pnpm dev"

echo Alice optimization complete!
echo Access Alice at: http://localhost:3003
pause