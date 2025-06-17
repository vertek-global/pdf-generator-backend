FROM python:3.10-slim
RUN apt-get update && apt-get install -y texlive-full && apt-get clean
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]