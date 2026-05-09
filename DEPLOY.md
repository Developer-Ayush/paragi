# Deployment Guide

Paragi can be deployed using Docker Compose or manually on a server.

## Docker Deployment (Recommended)

The easiest way to deploy Paragi is using Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Steps
1. Clone the repository.
2. Run the following command in the root directory:
   ```bash
   docker-compose up -d --build
   ```
3. The frontend will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.

### Using Ollama for LLM
To use Ollama for LLM refinement:
1. Ensure Ollama is running on your host machine.
2. Update `docker-compose.yml` or set environment variables:
   ```yaml
   backend:
     environment:
       - PARAGI_LLM_BACKEND=ollama
       - PARAGI_LLM_BASE_URL=http://host.docker.internal:11434
   ```
3. (Optional) Run `ollama pull gemma3:4b` on your host.

---

## Manual Deployment

### Backend
1. `cd backend`
2. Create and activate a virtual environment.
3. `pip install -r requirements.txt`
4. `python -m spacy download en_core_web_sm`
5. `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend
1. `cd frontend`
2. Create a `.env.local` file with `NEXT_PUBLIC_API_BASE_URL=http://your-api-url:8000`.
3. `npm install`
4. `npm run build`
5. `npm start`

## Data Persistence
By default, Docker uses a volume named `paragi-data` for the backend's HDF5 storage, Bloom filters, and logs.
Manual deployment stores data in `backend/data` unless `PARAGI_DATA_DIR` is set.
