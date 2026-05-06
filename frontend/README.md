# Paragi Frontend (Next.js)

## Setup

```powershell
cd frontend
npm install
```

## Run

```powershell
cd frontend
npm run dev
```

Open: http://localhost:3000

## Routes

- `/login` local auth register/login
- `/chat` chat UI with local chat sessions + side memory graphs
- `/graphs` full graph dashboard + stored query list

## Env

Use `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Notes

- Backend must run first at `http://127.0.0.1:8000`.
- Personal + main graph hovers use backend `description` fields from `/graph/summary`.
- Chat sessions are stored in browser localStorage per user ID.
