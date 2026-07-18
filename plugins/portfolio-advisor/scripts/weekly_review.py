#!/usr/bin/env python3
"""
weekly_review.py — Weekly Portfolio Advisor and Market Sweep.

Fetches 5-day price changes, calculates range-based target drift, and generates
a specialized weekly Grok news sweep prompt.
"""

import sys
import os
import json
import argparse
from datetime import datetime, date
from pathlib import Path

# Add backend py_services path to sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / 'investment_screener/backend/py_services'))

try:
    from history_store import HistoricalPriceStore
except ImportError:
    HistoricalPriceStore = None

try:
    from evolution_events import generate_evolution_correlation_report
except ImportError:
    generate_evolution_correlation_report = None

TARGET_JSON = REPO_ROOT / 'investment_screener/backend/data/theses/target-portfolio.json'
PORTFOLIO_JSON = REPO_ROOT / 'investment_screener/backend/data/portfolio.json'
WATCHLIST_JSON = REPO_ROOT / 'investment_screener/backend/data/watchlist.json'
ETF_ANALYSIS_DIR = REPO_ROOT / 'investment_screener/backend/data/etf_analysis'

def get_dynamic_exclusions():
    """Build exclusion list dynamically by scanning etf_analysis directory and cash reserves."""
    exclusions = {'USD_CASH', 'PSU-U.TO', 'PSU.U.TO'}
    if ETF_ANALYSIS_DIR.exists():
        for p in ETF_ANALYSIS_DIR.glob('*.json'):
            exclusions.add(p.stem.upper())
    return exclusions

def get_recent_reviews_context(repo_root):
    """Scans temp/daily-reviews/ and temp/weekly-reviews/ for reviews from the last 14 days and extracts key details to avoid repeating requests."""
    import glob
    from datetime import datetime, timedelta
    
    daily_path = os.path.join(repo_root, "investment_screener/backend/data/history/reviews/daily/*.md")
    weekly_path = os.path.join(repo_root, "investment_screener/backend/data/history/reviews/weekly/*.md")
    files = glob.glob(daily_path) + glob.glob(weekly_path)
    
    cutoff = datetime.now() - timedelta(days=14)
    recent_context = []
    
    # Sort files by modification time, newest first
    files = sorted(files, key=os.path.getmtime, reverse=True)
    
    for fp in files[:5]: # look at the 5 most recent files
        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        if mtime < cutoff:
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            # Extract bullet points from Executive Summary
            lines = content.splitlines()
            bullets = []
            capture = False
            for line in lines:
                if "## Executive Summary" in line:
                    capture = True
                    continue
                if capture:
                    if line.strip().startswith("##") or line.strip().startswith("---"):
                        break
                    if line.strip().startswith("*"):
                        bullets.append(line.strip())
            if bullets:
                fn = os.path.basename(fp)
                recent_context.append(f"- **From {fn} (Date: {mtime.strftime('%Y-%m-%d')}):**")
                recent_context.extend([f"  {b}" for b in bullets[:3]])
        except Exception:
            pass
            
    if recent_context:
        return "### Recent Summary Context (Already Captured/Do Not Ask Same Details):\n" + "\n".join(recent_context) + "\n\n"
    return ""

def load_json(path):
    import json
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def run_weekly_review(write_prompt_path=None):
    portfolio = load_json(PORTFOLIO_JSON)
    targets = load_json(TARGET_JSON)
    watchlist_data = load_json(WATCHLIST_JSON)
    
    holdings_map = {h['symbol'].upper(): h for h in portfolio.get('holdings', [])}
    target_holdings = targets.get('holdings', [])
    watchlist_items = watchlist_data.get('watchlist', [])
    
    total_equity = portfolio.get('totals', {}).get('totalUSD', 0.0)
    if total_equity == 0:
        total_equity = sum(h.get('market_value', 0.0) for h in holdings_map.values())
        
    print(f"Weekly Review — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Total Portfolio Value: ${total_equity:,.2f} USD\n")
    
    store = HistoricalPriceStore() if HistoricalPriceStore else None
    
    # We will build a list of tickers to review: holdings + target holdings + watchlist
    tickers_to_review = set()
    for h in target_holdings:
        tickers_to_review.add(h['ticker'].upper())
    for t in holdings_map.keys():
        tickers_to_review.add(t.upper())
    for w in watchlist_items:
        tickers_to_review.add(w['ticker'].upper())
        
    # Remove dynamically-derived ETFs/Cash
    exclusions = get_dynamic_exclusions()
    tickers_to_review = tickers_to_review - exclusions
    tickers_to_review = sorted(list(tickers_to_review))
    
    print(f"{'Ticker':<10} | {'Price':<9} | {'1W Change':<10} | {'Target%':<8} | {'Actual%':<8} | {'Drift%':<7} | {'Status':<12}")
    print("-" * 78)
    
    grok_tickers_data = []
    
    for ticker in tickers_to_review:
        # Get actual info
        holding = holdings_map.get(ticker, {})
        actual_shares = holding.get('shares', 0.0)
        curr_price = holding.get('price', 0.0)
        
        # Get target info
        target = next((t for t in target_holdings if t['ticker'].upper() == ticker), {})
        target_wt = target.get('targetWeight', 0.0)
        
        # If we don't have current price from portfolio, try to resolve it
        if curr_price == 0:
            if store:
                try:
                    import yfinance as yf
                    t_yf = yf.Ticker(ticker)
                    curr_price = t_yf.fast_info.last_price or 0.0
                except:
                    pass
        
        actual_val = actual_shares * curr_price
        actual_wt = (actual_val / total_equity) * 100 if total_equity > 0 else 0.0
        
        # Get weekly price change
        change_1w_str = "—"
        if store and curr_price > 0:
            try:
                changes = store.calc_changes(ticker, curr_price)
                change_1w = changes.get("change_1w")
                if change_1w is not None:
                    change_1w_str = f"{change_1w:+.2f}%"
            except Exception as e:
                pass
                
        # Range-based drift check:
        # Instead of strict trim/accumulate, we define a tolerance band.
        drift = actual_wt - target_wt
        ratio = (actual_wt / target_wt) if target_wt > 0 else 0.0
        
        if target_wt == 0:
            status = "EXIT" if actual_wt > 0 else "WATCHLIST"
        elif actual_wt == 0:
            status = "INITIATE"
        elif abs(drift) <= 1.0 or (0.80 <= ratio <= 1.20):
            status = "IN_RANGE"
        elif ratio < 0.80:
            status = "UNDERWEIGHT"
        else:
            status = "OVERWEIGHT"
            
        print(f"{ticker:<10} | ${curr_price:<8.2f} | {change_1w_str:<10} | {target_wt:>7.2f}% | {actual_wt:>7.2f}% | {drift:>+6.2f}% | {status:<12}")
        
        grok_tickers_data.append({
            "ticker": ticker,
            "target": target_wt,
            "actual": actual_wt,
            "price": curr_price,
            "change_1w": change_1w_str,
            "status": status
        })
        
    print("\nRange Check Summary:")
    in_range = [g['ticker'] for g in grok_tickers_data if g['status'] == 'IN_RANGE']
    over = [g['ticker'] for g in grok_tickers_data if g['status'] == 'OVERWEIGHT']
    under = [g['ticker'] for g in grok_tickers_data if g['status'] == 'UNDERWEIGHT']
    initiates = [g['ticker'] for g in grok_tickers_data if g['status'] == 'INITIATE']
    watch = [g['ticker'] for g in grok_tickers_data if g['status'] == 'WATCHLIST']
    
    print(f"  - In Range (±1.0% drift or 80-120% ratio): {', '.join(in_range) if in_range else 'None'}")
    print(f"  - Overweight (>120% target ratio): {', '.join(over) if over else 'None'}")
    print(f"  - Underweight (<80% target ratio): {', '.join(under) if under else 'None'}")
    print(f"  - Initiates (Undeployed target): {', '.join(initiates) if initiates else 'None'}")
    print(f"  - Watchlist: {', '.join(watch) if watch else 'None'}")
    
    # Load the Grok Weekly Sweep Prompt from template
    template_path = REPO_ROOT / "plugins/portfolio-advisor/assets/templates/weekly_sweep.md.template"
    try:
        template = template_path.read_text()
        prompt_content = template
        prompt_content = prompt_content.replace("{{DATE}}", datetime.now().strftime("%Y-%m-%d"))
        prompt_content = prompt_content.replace("{{TICKERS}}", ", ".join(tickers_to_review))
        
        # Inject recent summary context
        recent_ctx = get_recent_reviews_context(REPO_ROOT)
        if recent_ctx:
            prompt_content = prompt_content.replace("## Instructions for Grok", recent_ctx + "## Instructions for Grok")
    except Exception as e:
        print(f"Error loading weekly sweep template: {e}")
        prompt_content = f"# Weekly Sweep\n\nInclude: {', '.join(tickers_to_review)}"

    if write_prompt_path:
        out_path = Path(write_prompt_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt_content)
        print(f"\n[Prompt Written to {out_path}]")

        # Create weekly response placeholder
        placeholder_path = REPO_ROOT / f"temp/news-sweep-responses/grok/weekly-{datetime.now().strftime('%b%d-%Y').lower()}.md"
        placeholder_path.parent.mkdir(parents=True, exist_ok=True)
        if not placeholder_path.exists():
            placeholder_path.write_text(f"# Grok Weekly Sweep Response — {datetime.now().strftime('%Y-%m-%d')}\n\nPlease paste the raw Grok response below:\n\n---\n")
            print(f"[Response Placeholder Created at {placeholder_path}]")

    # ── Evolution events correlation report (G4 — non-blocking) ──────────────
    if generate_evolution_correlation_report:
        try:
            # Get week boundaries (Mon-Fri of current week)
            today = date.today()
            week_start = today - __import__('datetime').timedelta(days=today.weekday())
            week_end = week_start + __import__('datetime').timedelta(days=4)

            report = generate_evolution_correlation_report(
                week_start.isoformat(),
                week_end.isoformat(),
            )

            if report and report.get("total_events", 0) > 0:
                print(f"\n🔄  EVOLUTION EVENTS — Week of {week_start.isoformat()}:")
                for evt_type, summary in report.get("event_summary", {}).items():
                    if summary.get("count", 0) > 0:
                        tickers_str = ", ".join(summary.get("tickers", [])[:5])
                        avg_7d = summary.get("avg_7day_return")
                        avg_30d = summary.get("avg_30day_return")
                        avg_7d_str = f"{avg_7d:+.1f}%" if avg_7d is not None else "—"
                        avg_30d_str = f"{avg_30d:+.1f}%" if avg_30d is not None else "—"
                        print(f"    {evt_type:<25} {summary['count']:>2} events  avg_7d: {avg_7d_str:>6}  avg_30d: {avg_30d_str:>6}  ({tickers_str})")
        except Exception as e:
            # Non-blocking
            pass

    return grok_tickers_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-output", default=str(REPO_ROOT / "temp/grok-prompts/weekly_grok_prompt.md"))
    args = parser.parse_args()
    run_weekly_review(write_prompt_path=args.prompt_output)
