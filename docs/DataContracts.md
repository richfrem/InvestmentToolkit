# NOTE: All data contracts in this project are aligned with the official Questrade API schemas for consistency and reliability. See ADR 006 (adrs/006-data-contracts-aligned-with-questrade.md) for details and rationale. When updating or adding new contracts, always reference the Questrade API documentation and update ADR 006 if the approach changes.
# Data Contracts

## Holding Schema (Zod)
```typescript
import { z } from 'zod';

export const HoldingSchema = z.object({
  symbol: z.string(),
  quantity: z.number(),
  bookValue: z.number(),
  marketValue: z.number(),
});

export type Holding = z.infer<typeof HoldingSchema>;
```

## API Contracts
- **GET /api/holdings:** Returns `Holding[]`.
- **GET /api/current-holdings:** Returns current holdings from .ts file.
- **GET /api/auth/start:** Initiates OAuth flow.
- **GET /api/auth/callback:** Handles OAuth callback, logs refresh token.