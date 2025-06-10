import argparse
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
import finnhub
import questionary

FINNHUB_API_KEY = "d1451m1r01qrqeas456gd1451m1r01qrqeas4570"
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

def plot_revenue_and_margin(years, revenue, operating_margin, company_name="Company"):
    fig, ax1 = plt.subplots()
    color = 'tab:blue'
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Revenue (USD millions)', color=color)
    ax1.plot(years, revenue, color=color, marker='o', label='Revenue')
    ax1.tick_params(axis='y', labelcolor=color)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Operating Margin (%)', color=color)
    ax2.plot(years, operating_margin, color=color, marker='s', label='Operating Margin')
    ax2.tick_params(axis='y', labelcolor=color)
    plt.title(f'{company_name} Revenue and Operating Margin Trend')
    fig.tight_layout()
    plt.show()

def plot_peer_bars(companies, roic, ps_ratio, debt_to_equity):
    # Replace None with 0 and mark missing values for annotation
    roic_clean = [v if v is not None else 0 for v in roic]
    ps_ratio_clean = [v if v is not None else 0 for v in ps_ratio]
    debt_to_equity_clean = [v if v is not None else 0 for v in debt_to_equity]
    missing = [i for i, v in enumerate(roic) if v is None or ps_ratio[i] is None or debt_to_equity[i] is None]

    x = np.arange(len(companies))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width, roic_clean, width, label='ROIC (%)')
    rects2 = ax.bar(x, ps_ratio_clean, width, label='P/S Ratio')
    rects3 = ax.bar(x + width, debt_to_equity_clean, width, label='Debt-to-Equity')
    ax.set_ylabel('Metric Value')
    ax.set_title('Peer Comparison: ROIC, P/S, Debt-to-Equity')
    ax.set_xticks(x)
    ax.set_xticklabels(companies)
    ax.legend()
    # Annotate missing values
    for i in missing:
        ax.text(x[i], max(roic_clean[i], ps_ratio_clean[i], debt_to_equity_clean[i]) + 0.5, 'N/A', ha='center', color='red', fontsize=8)
    plt.tight_layout()
    plt.show()

# Helper to fetch annual revenue and margin from Finnhub
def fetch_finnhub_financials(ticker):
    try:
        fin = finnhub_client.financials_reported(symbol=ticker, freq='annual')
        years, revenue, op_margin = [], [], []
        for report in fin.get('data', []):
            year = int(report['year'])
            fs = report['report']['ic']
            rev = fs.get('totalRevenue', None)
            op_income = fs.get('operatingIncome', None)
            if rev is not None and op_income is not None:
                years.append(year)
                revenue.append(float(rev) / 1e6)
                margin = float(op_income) / float(rev) * 100 if float(rev) != 0 else None
                op_margin.append(round(margin, 2) if margin is not None else None)
        return years[::-1], revenue[::-1], op_margin[::-1]
    except Exception:
        return [], [], []

# Helper to fetch peer metrics from Finnhub
# (Finnhub free API does not provide all ratios, so fallback to Yahoo if missing)
def fetch_finnhub_peer_metrics(tickers):
    roic, ps_ratio, debt_to_equity = [], [], []
    for t in tickers:
        try:
            fin = finnhub_client.financials_reported(symbol=t, freq='annual')
            # P/S and Debt/Equity are not always available, so fallback to Yahoo if missing
            info = finnhub_client.company_basic_financials(t, 'all').get('metric', {})
            ps = info.get('priceToSalesAnnual', None)
            de = info.get('debtEquity', None)
            ps_ratio.append(round(float(ps), 2) if ps else None)
            debt_to_equity.append(round(float(de), 2) if de else None)
            roic.append(None)  # Not available in free Finnhub
        except Exception:
            roic.append(None)
            ps_ratio.append(None)
            debt_to_equity.append(None)
    return roic, ps_ratio, debt_to_equity

# Updated fetch_financials to try Finnhub first, then Yahoo as fallback

def fetch_financials(ticker):
    years, revenue, op_margin = fetch_finnhub_financials(ticker)
    if not years or not revenue or not op_margin:
        # Fallback to Yahoo
        ticker_obj = yf.Ticker(ticker)
        try:
            rev = ticker_obj.financials.loc['Total Revenue']
            years = list(rev.index.year)
            revenue = [float(r) / 1e6 for r in rev.values]
        except Exception:
            years, revenue = [], []
        try:
            op_income = ticker_obj.financials.loc['Operating Income']
            op_margin = [float(oi) / float(r) * 100 if r else None for oi, r in zip(op_income.values, rev.values)]
            op_margin = [round(m, 2) if m is not None else None for m in op_margin]
        except Exception:
            op_margin = []
        return years[::-1], revenue[::-1], op_margin[::-1]
    return years, revenue, op_margin

# Updated fetch_peer_metrics to try Finnhub first, then Yahoo as fallback

def fetch_peer_metrics(tickers):
    roic, ps_ratio, debt_to_equity = fetch_finnhub_peer_metrics(tickers)
    # If any metric is missing, try to fill from Yahoo
    for i, t in enumerate(tickers):
        if ps_ratio[i] is None or debt_to_equity[i] is None:
            try:
                ticker_obj = yf.Ticker(t)
                info = ticker_obj.info
                if ps_ratio[i] is None:
                    ps = info.get('priceToSalesTrailing12Months', None)
                    ps_ratio[i] = round(ps, 2) if ps else None
                if debt_to_equity[i] is None:
                    de = info.get('debtToEquity', None)
                    debt_to_equity[i] = round(de, 2) if de else None
            except Exception:
                pass
    # ROIC is not available in either free API
    return roic, ps_ratio, debt_to_equity

def fetch_metric_for_peers(tickers, metric):
    # Only fetch the selected metric for each peer
    values = []
    for t in tickers:
        val = None
        # Try Finnhub first
        try:
            info = finnhub_client.company_basic_financials(t, 'all').get('metric', {})
            if metric == 'P/S Ratio':
                ps = info.get('priceToSalesAnnual', None)
                val = round(float(ps), 2) if ps else None
            elif metric == 'Debt-to-Equity':
                de = info.get('debtEquity', None)
                val = round(float(de), 2) if de else None
            # ROIC not available in free Finnhub
        except Exception:
            pass
        # Fallback to Yahoo
        if val is None:
            try:
                ticker_obj = yf.Ticker(t)
                info = ticker_obj.info
                if metric == 'P/S Ratio':
                    ps = info.get('priceToSalesTrailing12Months', None)
                    val = round(ps, 2) if ps else None
                elif metric == 'Debt-to-Equity':
                    de = info.get('debtToEquity', None)
                    val = round(de, 2) if de else None
                # ROIC not available
            except Exception:
                pass
        values.append(val)
    return values

def plot_peer_metric_bar(companies, values, metric):
    values_clean = [v if v is not None else 0 for v in values]
    missing = [i for i, v in enumerate(values) if v is None]
    x = np.arange(len(companies))
    width = 0.5
    fig, ax = plt.subplots(figsize=(8, 5))
    rects = ax.bar(x, values_clean, width, label=metric)
    ax.set_ylabel(metric)
    ax.set_title(f'Peer Comparison: {metric}')
    ax.set_xticks(x)
    ax.set_xticklabels(companies)
    # Annotate missing values
    for i in missing:
        ax.text(x[i], max(values_clean[i], 0) + 0.5, 'N/A', ha='center', color='red', fontsize=8)
    plt.tight_layout()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Stock chart visualizer for screener framework.")
    parser.add_argument('--ticker', type=str, help='Main company ticker (e.g., PLTR)')
    parser.add_argument('--peers', nargs='+', type=str, default=[], help='Peer company tickers (e.g., SNOW CRWD INDUSTRYMEDIAN)')
    parser.add_argument('--metric', type=str, help='Metric to compare (e.g., ROIC, P/S Ratio, Debt-to-Equity)')
    args = parser.parse_args()

    # Interactive prompts if not provided
    if not args.ticker:
        args.ticker = questionary.text("Enter main company ticker (e.g., PLTR):").ask()
    if not args.peers:
        peers_str = questionary.text("Enter peer tickers separated by space (e.g., SNOW CRWD):").ask()
        args.peers = peers_str.strip().split()
    metric_choices = ['ROIC', 'P/S Ratio', 'Debt-to-Equity']
    if not args.metric:
        args.metric = questionary.select(
            "Select metric for peer comparison:",
            choices=metric_choices
        ).ask()

    # Fetch main company data
    years, revenue, op_margin = fetch_financials(args.ticker)
    if not years or not revenue or not op_margin:
        print(f"Could not fetch financials for {args.ticker}")
        return
    companies = [args.ticker.upper()] + [p.upper() for p in args.peers]
    peer_tickers = [args.ticker] + args.peers

    plot_revenue_and_margin(years, revenue, op_margin, company_name=args.ticker.upper())

    if args.metric == 'ROIC':
        print("ROIC is not available via free APIs and will show as N/A.")
        values = [None for _ in peer_tickers]
    else:
        values = fetch_metric_for_peers(peer_tickers, args.metric)
    plot_peer_metric_bar(companies, values, args.metric)

if __name__ == "__main__":
    main()
