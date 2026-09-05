# MedLens

MedLens organizes documented medical information, links facts to source evidence, and keeps human verification separate from AI extraction.

## Local Development

1. Copy `backend/.env.example` to `backend/.env`.
2. Add your own Groq API key locally if real extraction is enabled.
3. Never commit `.env` files or place Groq credentials in frontend variables.
4. Start the backend from `backend/` with `python -m uvicorn app.main:app --reload`.
5. Start the frontend from `frontend/` with `npm run dev`.

The frontend may use `VITE_API_BASE_URL` for the non-secret backend URL. Never use `VITE_GROQ_API_KEY` or expose provider credentials to the browser.
