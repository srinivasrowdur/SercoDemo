FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including ffmpeg and nginx
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    ffmpeg \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create necessary directories
RUN mkdir -p /app/audio /app/transcriptions /app/conversations

# Configure nginx
RUN echo 'server {\n\
    listen 8080;\n\
    location / {\n\
        proxy_pass http://localhost:8501;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Upgrade $http_upgrade;\n\
        proxy_set_header Connection "upgrade";\n\
        proxy_set_header Host $host;\n\
        proxy_cache_bypass $http_upgrade;\n\
    }\n\
    location /static {\n\
        alias /app/.streamlit/static;\n\
        types {\n\
            text/css css;\n\
            application/javascript js;\n\
            font/woff2 woff2;\n\
        }\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=localhost
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=true

# Create startup script
RUN echo '#!/bin/bash\n\
nginx\n\
streamlit run --server.port=8501 --server.address=localhost app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose the port
EXPOSE 8080

# Run both nginx and streamlit
CMD ["/app/start.sh"] 