# API Server Entry Point
# Run this separately if you need the API endpoints
# Command: uvicorn api:app --host 0.0.0.0 --port $PORT

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run main app
from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

