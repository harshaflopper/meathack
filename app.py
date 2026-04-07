#!/usr/bin/env python3

import os
import sys
import subprocess

# Set environment variables for HF Spaces
os.environ["PYTHONPATH"] = "/app"
os.environ["PYTHONUNBUFFERED"] = "1"

def main():
    """Main entry point for HF Spaces"""
    try:
        # Start the FastAPI server
        cmd = [
            "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "7860",
            "--workers", "1",
            "--timeout-keep-alive", "120"
        ]
        
        print("Starting NeuroCache LLM Memory Optimizer...")
        print("API will be available at: http://localhost:7860")
        
        # Run uvicorn
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
