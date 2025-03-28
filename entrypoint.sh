#!/bin/bash

# Create necessary directories
mkdir -p audio
mkdir -p transcriptions
mkdir -p conversations


# Use PORT environment variable with a default of 8501
PORT="${PORT:-8501}"


# Run the Streamlit app
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
