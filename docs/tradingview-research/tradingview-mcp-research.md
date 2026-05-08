# TradingView Integration Research

**Researched:** 2026-05-08 (updated with third repo comparison)
**Repos reviewed:**
- `temp/tradingview-mcp` — CDP Desktop bridge ([github.com/tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp))
- `temp/tradingview-api` — Official Charting Library docs ([tradingview.com/charting-library-docs](https://www.tradingview.com/charting-library-docs/latest/api/))
- `temp/atilaahmettaner-tradingview-mcp` — REST API aggregator ([github.com/atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp))

**Context:** TradingView Premium subscription + Questrade integrated with TradingView for order execution. Current InvestmentToolkit uses yfinance (delayed) for prices and Questrade API for position data.

---

## Three Distinct Approaches

Three repos, three fundamentally different architectures — all complementary:

| | CDP Desktop (`temp/tradingview-mcp`) | REST Aggregator (`temp/atilaahmettaner-tradingview-mcp`) | Charting Library (`temp/tradingview-api`) |
|---|---|---|---|
| **Type** | Community CDP bridge | REST API + Python services | Official frontend SDK |
| **Connection** | Chrome DevTools Protocol → Desktop | HTTP calls to public APIs | Frontend widget (no data) |
| **TradingView Desktop required** | ✅ Yes — must be running | ❌ No | ❌ No |
| **Works on VPS / cloud** | ❌ No | ✅ Yes | N/A |
| **Language** | Node.js | Python | TypeScript/JS |
| **Setup** | Install TV Desktop, enable CDP | `pip install tradingview-mcp-server` | npm + license |
| **Auth** | None (local Desktop session) | None (public APIs) | None in lib; your backend |
| **Real-time prices** | Yes — your Premium sub | Yes — Yahoo Finance | Via your backend |
| **Backtesting** | ❌ No | ✅ Yes (6 strategies, Sharpe/Calmar) | ❌ No |
| **Sentiment/news** | ❌ No | ✅ Yes (Reddit + RSS) | ❌ No |
| **Create TV alerts** | ✅ Yes | ❌ No | ❌ No |
| **Chart control/screenshots** | ✅ Yes | ❌ No | ✅ Via widget |
| **Agent-readable JSON** | ✅ Yes | ✅ Yes | ❌ No |
| **Official** | No | No | Yes |
| **License** | MIT | MIT | Free public / commercial for private |

**The natural combination for InvestmentToolkit:**
- **REST aggregator** → screener scanning, backtesting strategies, sentiment checks, multi-exchange market overview (no Desktop needed, works anytime)
- **CDP Desktop** → real-time prices from your Premium sub, alert creation at DCF targets, chart screenshots (requires Desktop running)
- **Charting Library** → future: embed professional charts in the React frontend (Phase 3, requires license)

---

## Part 1 — TradingView MCP (CDP Bridge)

### What It Is

A 78-tool MCP server that connects Claude Code to a locally running TradingView Desktop app via Chrome DevTools Protocol (CDP). No API keys. No network traffic interception. Uses your existing TradingView session.

**Connection chain:**
```
Claude Code ←→ MCP Server (stdio) ←→ CDP (localhost:9222) ←→ TradingView Desktop (Electron)
```

### Launch TradingView with CDP (macOS)
```bash
# Script included in repo:
./temp/tradingview-mcp/scripts/launch_tv_debug_mac.sh

# Or manually:
open -a "TradingView" --args --remote-debugging-port=9222
```

### Key Tools for InvestmentToolkit

**Real-time prices:**
| Tool | Returns | Use Case |
|------|---------|---------|
| `quote_get` | Real-time OHLC, price, change% for any symbol | Replace yfinance in heatmap |
| `watchlist_get` | All watchlist symbols + live price/change% | Bulk portfolio price pull |
| `batch_run` + `get_ohlcv` | OHLCV across many symbols in one call | Portfolio-wide refresh |
| `data_get_ohlcv` | Up to 500 bars, any timeframe | DCF price snapshots |

**Workflow integration:**
| Tool | Use Case |
|------|---------|
| `alert_create` | Auto-create price alerts at DCF fair value targets |
| `capture_screenshot` | Embed chart screenshots in strategic review reports |
| `data_get_study_values` | Pull RSI/MACD values — add technical signals to screener |
| `draw_shape` | Mark DCF target prices and thesis breaker levels on charts |

**Streaming (CLI mode):**
```bash
# Stream real-time quotes for all portfolio positions:
npx tradingview-mcp stream quote --symbol CRWV --interval 5000
npx tradingview-mcp stream all  # all panes simultaneously
```

### MCP Config
Add to `.mcp.json` in project root:
```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/Users/richardfremmerlid/Projects/InvestmentToolkit/temp/tradingview-mcp/src/server.js"]
    }
  }
}
```

### Limitations
- **Undocumented API** — any TradingView Desktop update can break it; always keep yfinance fallback
- **Desktop must be running** — not available when TradingView is closed
- **Terms of Use** — personal/research use only; no data redistribution
- **500-bar max** per OHLCV request
- **Agent latency** — seconds per tool call; not suitable for millisecond trading

---

## Part 2 — TradingView Charting Library (Official SDK)

### What It Is

The **official** TradingView frontend widget for embedding professional charts in web applications. This is the same chart engine used on TradingView.com. It includes:
- 100+ built-in technical indicators
- 110+ drawing tools
- Multiple chart types (Candles, Heikin Ashi, Renko, Kagi, Point & Figure, etc.)
- Real-time streaming support
- Full **Broker/Trading** module for order placement UI

**Critical distinction:** The library is a **UI framework only** — it does not provide market data. You supply your own data via a `Datafeed` interface it defines.

### How the Datafeed Interface Works

```typescript
// You implement this interface and connect your data source:
interface IExternalDatafeed {
  onReady(callback: OnReadyCallback): void;
  resolveSymbol(symbolName: string, onResolve: ResolveCallback): void;
  getBars(symbolInfo, resolution, onHistoryCallback): void;     // historical OHLCV
  subscribeBars(symbolInfo, resolution, onRealtimeCallback): void; // live updates
  getQuotes(symbols, onQuotesCallback): void;                   // real-time quotes
}

// Wire to TradingView chart widget:
new TradingView.widget({
  datafeed: new YourDatafeed(), // your implementation
  container: 'chart_container',
  // ...
});
```

Your backend implements `getBars()` and `subscribeBars()` — could be yfinance, TradingView MCP, Questrade WebSocket, or anything else.

### Broker Module (Trade Execution UI)

The Broker module gives you a **full order management UI** inside the chart:
- Market, limit, stop orders with bracket support
- Position tracking with P&L
- Account balance display
- Order preview and validation
- Leverage control

**For you:** Since Questrade is already integrated with TradingView, you effectively have a model: the Charting Library's Broker module could be wired to Questrade's OAuth2 API to create a self-hosted trading terminal with your InvestmentToolkit thesis overlaid.

### Data Types Supported

| Data Type | Via Datafeed | Notes |
|-----------|-------------|-------|
| OHLCV bars | `getBars()` | All resolutions from ticks to monthly |
| Real-time bars | `subscribeBars()` | Streaming via your WebSocket |
| Real-time quotes | `getQuotes()` | Bid/ask, last, change% |
| DOM (Depth of Market) | `DOMCallback` | Order book data |
| Symbol search | `searchSymbols()` | Your symbol list |
| News feed | Plugin | Custom news provider |

### Licensing

| Use | License |
|-----|---------|
| Public website with TV attribution visible | **Free** |
| Private/internal tool (your InvestmentToolkit) | **Requires commercial license** |
| Commercial product | **Requires commercial license** |

**For your InvestmentToolkit (personal, not public):** Technically requires a commercial license. In practice, many personal projects use it without one, but be aware of this if you share or productize the tool.

---

## Part 3 — How They Work Together for InvestmentToolkit

The ideal architecture uses both layers:

```
┌─────────────────────────────────────────────────────────┐
│           InvestmentToolkit Frontend (React)            │
│                                                         │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │  TradingView         │  │  Portfolio Dashboard      │ │
│  │  Charting Library    │  │  (ScreenerTable,          │ │
│  │  (embedded chart)    │  │   PortfolioTable)         │ │
│  └──────────┬───────────┘  └──────────────────────────┘ │
│             │ Datafeed interface                         │
└─────────────┼───────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────┐
│            Backend (Node.js / Python)                   │
│                                                         │
│  Datafeed API endpoint ────► fetch_prices_tradingview.py│
│  (serves OHLCV, quotes)       ├── TradingView MCP       │
│                               │   (real-time, Premium)  │
│  Questrade API ◄──────────────┤                         │
│  (positions, book value)      └── yfinance fallback     │
│                                   (delayed)             │
│  DCF projections ─────────────► target-portfolio.json   │
└─────────────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────┐
│            AI Agent Layer (Claude Code)                 │
│                                                         │
│  /x-news-sweep ──────────────► TradingView MCP tools    │
│  /evaluate-stock ────────────► quote_get + alert_create │
│  /review-portfolio ──────────► batch_run (price refresh)│
└─────────────────────────────────────────────────────────┘
```

---

## Recommended Integration Roadmap

### Phase 1 — Real-Time Prices via MCP (1–2 days, high ROI)

**Goal:** Replace yfinance delayed prices with TradingView real-time in the screener heatmap.

1. Install MCP: `cd temp/tradingview-mcp && npm install`
2. Add to `.mcp.json` (config above)
3. Build `py_services/fetch_prices_tradingview.py`:
   - Calls MCP `watchlist_get` or `batch_run quote_get` for portfolio tickers
   - Falls back to yfinance if TradingView Desktop not running
   - Same output schema as current `fetch_portfolio_heatmap.py`
4. Update backend to use new script
5. Test: launch TV with CDP flag, run `/x-news-sweep`, confirm real-time prices

**Result:** Screener 1d% changes are live. DCF snapshots use real-time price at eval time.

### Phase 2 — Automated DCF Alerts (2–4 hrs, medium ROI)

**Goal:** After each `/evaluate-stock`, auto-create TradingView price alerts at bear/base/bull scenario prices.

Add to `/evaluate-stock` skill (Phase 6 of the skill):
```python
# After writing projection JSON, create alerts:
for scenario in ['bear', 'base', 'bull']:
    price = projection['scenarios'][scenario]['scenarioPrice']
    mcp.call('alert_create', {
        'symbol': ticker,
        'price': price,
        'condition': 'crossing',
        'name': f'{ticker} {scenario} DCF target'
    })
```

**Result:** You get notified in TradingView when any holding hits a scenario price.

### Phase 3 — Charting Library Embed (1–2 weeks, high complexity)

**Goal:** Replace the current Recharts/basic charts in InvestmentToolkit with full TradingView professional charts.

1. Get Charting Library access (trial or commercial license from TradingView)
2. Build `DatafeedService.ts` in frontend that:
   - Calls `/api/prices/history` for `getBars()` (backed by yfinance or TV MCP)
   - Opens WebSocket for `subscribeBars()` live updates
3. Create `TradingViewChart.tsx` component wrapping the library widget
4. Add DCF overlays via Pine Script or `draw_shape` — mark fair value levels on charts
5. (Optional) Wire Broker module to Questrade API for trade execution inside the chart

**Result:** Full professional chart experience with your thesis/DCF data overlaid. The chart your AI agents analyze is the same chart you trade from.

---

## Quick-Start Checklist

- [ ] `cd temp/tradingview-mcp && npm install`
- [ ] Add `tradingview` entry to `.mcp.json`
- [ ] Launch TradingView: `./temp/tradingview-mcp/scripts/launch_tv_debug_mac.sh`
- [ ] Test in Claude Code: ask to run `tv_health_check`, then `quote_get` on CRWV
- [ ] Add portfolio tickers to a TradingView watchlist named "InvestmentToolkit"
- [ ] (Optional) Request Charting Library trial at tradingview.com/advanced-charts/

---

## Files in `temp/tradingview-api/`

| File | Content |
|------|---------|
| `intro.md` | Overview of Advanced Charts / Trading Platform SDK |
| `api-main.md` | API architecture — three modules (Datafeed, Chart, Broker) |
| `data-feed.md` | Datafeed module reference — most important for integration |
| `charting-library.md` | UI widget module — chart types, indicators, drawing tools |
| `module-broker.md` | Trading/broker module — order management, positions |

---

## Part 4 — Atila's REST Aggregator (`temp/atilaahmettaner-tradingview-mcp`)

**Repo:** [github.com/atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)  
**Language:** Python 3.10+ | **License:** MIT | **Version:** 0.7.1 (actively maintained, last commit Aug 2025)

### What It Is

A **Python MCP server** that aggregates multiple public data sources — TradingView's screener API, Yahoo Finance, Reddit, and RSS news feeds — into 30+ MCP tools. **Requires no TradingView Desktop, no API keys, and no credentials.** Works from any environment including Docker, VPS, and cloud.

```python
# Core dependencies (from pyproject.toml):
tradingview-screener>=0.6.4   # TradingView public screener API
tradingview-ta>=3.3.0          # Technical analysis via TradingView data
feedparser>=6.0.12             # RSS parsing for news
mcp[cli]>=1.12.0               # MCP server framework
```

Data flows via REST:
```
Claude ←→ MCP server ←→ HTTP REST → TradingView screener API
                                   → Yahoo Finance chart API
                                   → Reddit public JSON API
                                   → RSS feeds (Reuters, CoinDesk, CoinTelegraph)
```

### Full Tool List (30+ tools)

**Screener & Market Overview**
| Tool | What It Does |
|------|-------------|
| `top_gainers` | Top % gainers on any exchange, any timeframe |
| `top_losers` | Top % losers |
| `bollinger_scan` | Assets in Bollinger Band squeeze (low BBW) |
| `rating_filter` | Filter by TV rating score (-3=Strong Sell → +3=Strong Buy) |
| `market_snapshot` | S&P500, NASDAQ, VIX, BTC, ETH, EUR/USD, SPY, GLD in one call |

**Technical Analysis (per ticker)**
| Tool | What It Does |
|------|-------------|
| `coin_analysis` | Price + 23 indicators (RSI, MACD, BB, EMA, ATR, Ichimoku, etc.) + signals |
| `multi_timeframe_analysis` | 5-level alignment: W → D → 4H → 1H → 15m |
| `get_candlestick_patterns` | 15 pattern detector (doji, hammer, engulfing, shooting star, etc.) |
| `volume_breakout_scanner` | Simultaneous volume + price breakout screen |
| `volume_confirmation_analysis` | OBV + volume profile + distribution analysis |
| `smart_volume_scanner` | Volume + RSI combo screen |
| `consecutive_candles_scan` | N consecutive growing/shrinking candles screen |
| `advanced_candle_pattern` | Multi-timeframe candle pattern detection |

**AI Multi-Agent Analysis**
| Tool | What It Does |
|------|-------------|
| `multi_agent_analysis` | 3-agent debate: Technical analyst vs Sentiment analyst vs Risk manager → STRONG BUY / BUY / HOLD / SELL / STRONG SELL consensus |

**Real-Time Pricing**
| Tool | What It Does |
|------|-------------|
| `yahoo_price` | Current price, 52w high/low, market state, % change |
| `stock_extended_hours` | Pre-market, regular, post-market prices (US stocks) |
| `bitcoin_market_pulse` | BTC price, dominance %, total crypto mcap, risk label |

**Sentiment & News**
| Tool | What It Does |
|------|-------------|
| `market_sentiment` | Reddit bullish/bearish score + top posts for any symbol |
| `financial_news` | Headlines from Reuters, CoinDesk, CoinTelegraph with summaries |
| `combined_analysis` | **Power tool:** technicals + Reddit sentiment + live news → unified confluence call |

**Backtesting Engine (v0.7.0)**
| Tool | What It Does |
|------|-------------|
| `backtest_strategy` | 6 strategies (RSI, Bollinger, MACD, EMA cross, Supertrend, Donchian) — returns Sharpe, Calmar, max drawdown, win rate, profit factor, expectancy |
| `compare_strategies` | Leaderboard ranking all 6 strategies + buy-and-hold comparison |
| `walk_forward_backtest_strategy` | Overfitting detection — per-fold in-sample vs out-of-sample robustness score |

**Exchange Support:** NASDAQ, NYSE, BINANCE, COINBASE, KUCOIN, BYBIT, and 35+ others including EGX (Egypt), BIST (Turkey), ASX (Australia), HKEX, SSE, TWSE.

### Authentication

**Zero.** All data sources are public APIs:
- TradingView screener: public endpoints
- Yahoo Finance: no auth (rate-limited, optional proxy)
- Reddit: public JSON API
- RSS: public

Optional `PROXY_*` env vars for Webshare rotating proxies to bypass Yahoo Finance rate limits — gracefully ignored if not set.

### Setup

```bash
# Install (one line):
pip install tradingview-mcp-server

# Or from local clone:
cd temp/atilaahmettaner-tradingview-mcp
pip install -e .

# No TradingView Desktop, no API keys, no config files required.
```

### Advantages Over CDP Approach

| Capability | CDP Desktop | REST Aggregator |
|------------|-------------|----------------|
| Works without TradingView running | ❌ | ✅ |
| Cloud / VPS / Docker deployable | ❌ | ✅ |
| Built-in backtesting (Sharpe, Calmar) | ❌ | ✅ |
| Reddit sentiment analysis | ❌ | ✅ |
| News headlines (Reuters/CoinDesk) | ❌ | ✅ |
| 40+ exchange/market support | ❌ | ✅ |
| Multi-agent AI consensus signal | ❌ | ✅ |
| No maintenance risk from TV updates | ❌ | ✅ |

### Limitations vs CDP Approach

| Capability | CDP Desktop | REST Aggregator |
|------------|-------------|----------------|
| Real-time from YOUR Premium sub | ✅ | ❌ (Yahoo = same ~15min delay) |
| Create/manage TradingView alerts | ✅ | ❌ |
| Chart screenshots | ✅ | ❌ |
| Pine Script development | ✅ | ❌ |
| Fundamental data (P/E, revenue, EPS) | ❌ | ❌ — both rely on yfinance for this |

### Relevance for InvestmentToolkit

The REST aggregator fills gaps the CDP plugin cannot cover without Desktop running:

1. **`/tv-screener-scan`** (future skill) — daily top gainers/losers across NASDAQ/NYSE + crypto exchanges, flagging unusual volume or Bollinger squeeze in holdings
2. **`/tv-backtest TICKER STRATEGY`** (future skill) — quick strategy backtest for a position to validate entry timing
3. **`combined_analysis`** → enrich the Grok sweep prompt: pull Reddit sentiment + news headlines for each [DD]-flagged position before pasting into Grok
4. **`multi_timeframe_analysis`** → add technical alignment signal to the screener table (W/D/4H/1H all bullish = green badge)
5. **`market_snapshot`** → daily session opener: one-line macro context (VIX level, BTC dominance, S&P trend)

### Phase 4 — REST Aggregator Integration (recommended addition to implementation plan)

**Install:**
```bash
cd temp/atilaahmettaner-tradingview-mcp && pip install -e .
# Add to requirements.in: tradingview-screener>=0.6.4 tradingview-ta>=3.3.0 feedparser>=6.0.12
```

**New plugin skills to add (`plugins/tradingview/skills/`):**

| Skill file | Trigger | What it calls |
|------------|---------|--------------|
| `screener-scan/SKILL.md` | `/tv-screener-scan` | `top_gainers`, `top_losers`, `bollinger_scan` on NASDAQ/NYSE |
| `market-pulse/SKILL.md` | `/tv-market-pulse` | `market_snapshot` + `bitcoin_market_pulse` for daily opener |
| `backtest/SKILL.md` | `/tv-backtest TICKER` | `compare_strategies` for any portfolio ticker |
| `combined-signal/SKILL.md` | `/tv-signal TICKER` | `combined_analysis` (technicals + sentiment + news) |

**New scripts to add (`plugins/tradingview/scripts/`):**

| Script | Purpose |
|--------|---------|
| `atila_client.py` | Thin subprocess caller for the REST aggregator CLI (mirrors `tv_client.py` pattern) |
| `atila_screener.py` | Top gainers/losers/squeeze scan → formatted table |
| `atila_signal.py` | Combined analysis for a ticker → thesis-aligned summary |
| `atila_backtest.py` | Strategy comparison → ranked leaderboard |

---

## Updated Roadmap (All Three Sources)

| Phase | What | Source | Effort | Status |
|-------|------|--------|--------|--------|
| 1 | Real-time prices in heatmap | CDP Desktop | Done | ✅ Implemented |
| 2 | DCF alerts in TradingView | CDP Desktop | Done | ✅ Implemented |
| 3 | Chart screenshots | CDP Desktop | Done | ✅ Implemented |
| 4 | REST screener scan + market pulse | REST Aggregator | 1–2 days | 🔲 Planned |
| 5 | Combined signal (tech + sentiment + news) | REST Aggregator | 1 day | 🔲 Planned |
| 6 | Strategy backtesting per ticker | REST Aggregator | 1 day | 🔲 Planned |
| 7 | Charting Library embed in React | Official SDK | 1–2 weeks | 🔲 Future |

---

*Research by Claude Sonnet 4.6 — 2026-05-08*  
*Sources: `temp/tradingview-mcp` (CDP, full code review) + `temp/atilaahmettaner-tradingview-mcp` (REST, full code review) + `temp/tradingview-api` (official Charting Library docs)*
