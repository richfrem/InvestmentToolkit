-- CreateTable
CREATE TABLE "HoldingCache" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "symbol" TEXT NOT NULL,
    "quantity" REAL NOT NULL,
    "bookValue" REAL NOT NULL,
    "marketValue" REAL NOT NULL,
    "fetchedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
