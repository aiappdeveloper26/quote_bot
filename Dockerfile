FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better build caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot
COPY . .

# Render provides the PORT env var; the bot's web server reads it.
CMD ["python", "quote_bot.py"]
