/**
 * Backend Server Entry Point
 *
 * - Loads environment variables
 * - Sets up the Express app and middleware
 * - Registers API routes (including Questrade proxy routes)
 * - Starts the server and listens on the configured port
 *
 * Start this server with:
 *   npm run dev
 * or
 *   ts-node --esm src/index.ts
 */
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import questradeRoutes from './routes/questrade.ts';

dotenv.config();

const app = express();
const PORT = process.env.BACKEND_PORT || 3001;

app.use(cors());
app.use(express.json());

app.use('/api', questradeRoutes);

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});

export default app;