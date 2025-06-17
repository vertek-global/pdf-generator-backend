FROM python:3.10-slim

# Install required system packages
RUN apt-get update && \
    apt-get install -y texlive-xetex && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Use Railway's PORT
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]