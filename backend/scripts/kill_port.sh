#!/bin/bash
# Script to kill process on a specific port

PORT=${1:-8000}

echo "🔍 Checking for processes on port $PORT..."

PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "✅ No process found on port $PORT"
    exit 0
fi

echo "⚠️  Found process $PID on port $PORT"
echo "🔪 Killing process..."

kill -9 $PID

if [ $? -eq 0 ]; then
    echo "✅ Successfully killed process $PID on port $PORT"
else
    echo "❌ Failed to kill process $PID"
    exit 1
fi

