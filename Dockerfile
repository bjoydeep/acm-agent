# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env.example .
COPY .streamlit/ ./.streamlit/

# Create non-root user for security (OpenShift compatible)
RUN groupadd -r appuser && useradd -r -g appuser -m appuser
RUN chown -R appuser:appuser /app
RUN mkdir -p /home/appuser/.streamlit && chown -R appuser:appuser /home/appuser
USER appuser

# Set HOME directory to a writable location in OpenShift
ENV HOME=/tmp

# Expose Streamlit port
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_GLOBAL_DISABLE_WATCHER_WARNINGS=true

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')" || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false", "--global.developmentMode=false"]