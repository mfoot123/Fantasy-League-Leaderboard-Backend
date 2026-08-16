# Fantasy-League-Leaderboard-Backend

## Project B: backend API

This repository is configured as a separate Vercel backend project exposing the public leaderboard API.

### Public API
- Health check: `/`
- Example users route: `/users?year=2025`

### Vercel deployment
1. Import this repository into a new Vercel project.
2. Set the project root to the repository root.
3. Ensure the serverless entrypoint is the Flask app in `api/index.py`.
4. The app is exposed through the rewrite in `vercel.json`, so the public URL resolves to paths like:
   - `https://your-api-project.vercel.app/`
   - `https://your-api-project.vercel.app/users?year=2025`

### Local development
```bash
cd api
PYTHONPATH=. python3 App.py
```

The app runs as a standard Flask app locally and exports the WSGI callable needed by Vercel.
