# Questrade Portfolio Viewer

A secure app to view your Questrade holdings via API, display in a dashboard, and save to local spreadsheet.

## Features
- Fetch holdings from Questrade API.
- Display in responsive table.
- Manual OAuth authentication.
- Local .ts storage (V1).

## Setup
1. Register for Questrade API, get client ID/secret.
2. Copy `.env.example` to `.env`, fill in credentials.
3. Install dependencies: `npm run install-all`.
4. Setup DB: `cd backend && npx prisma migrate dev --name init`.
5. Run: `./start.sh` to start both servers, or `./stop.sh` to stop them.

## Running the App
- Use `./start.sh` to start backend (port 3001) and frontend (port 5173) servers.
- Use `./stop.sh` to stop the servers.
- Backend API: http://localhost:3001
- Frontend: http://localhost:5173

## Security
- .env for secrets.
- Husky pre-commit scans for secrets.
- No password storage.

## Roadmap
See `docs/Roadmap.md`.