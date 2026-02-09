# Database Setup

## Overview
Uses Prisma with SQLite for local persistence. Minimal setup for V1 (caching future).

## Setup Commands
```bash
cd backend
npm install
npx prisma generate
npx prisma migrate dev --name init
```

## Schema
See `prisma/schema.prisma` for HoldingCache model.

## Usage
- Run migrations on setup.
- For V1, data stored in .ts file; DB for future features.