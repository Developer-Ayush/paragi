FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for h5py and spaCy
RUN apt-get update && apt-get install -y \
    build-essential \
    libhdf5-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

COPY . .

# Create data directory
RUN mkdir -p data

ENV PARAGI_DATA_DIR=/app/data
ENV PARAGI_PREFER_HDF5=1
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
