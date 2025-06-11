import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
import finnhub

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
    values = []
    for t in tickers:
        val = None
        try:
            info = finnhub_client.company_basic_financials(t, 'all').get('metric', {})
            if metric == 'Revenue Growth % (Past)':
                # Not available directly, fallback to Yahoo
                ticker_obj = yf.Ticker(t)
                hist = ticker_obj.history(period='5y')
                if len(hist) > 1:
                    revs = hist['Close']
                    val = ((revs[-1] - revs[0]) / revs[0]) * 100 if revs[0] else None
            elif metric == 'Operating Margin':
                # Not available directly, fallback to Yahoo
                ticker_obj = yf.Ticker(t)
                try:
                    fin = ticker_obj.financials
                    op_income = fin.loc['Operating Income']
                    rev = fin.loc['Total Revenue']
                    val = (float(op_income[-1]) / float(rev[-1])) * 100 if rev[-1] else None
                except Exception:
                    val = None
            elif metric == 'P/S Ratio':
                ps = info.get('priceToSalesAnnual', None)
                val = round(float(ps), 2) if ps else None
            elif metric == 'Debt-to-Equity Ratio':
                de = info.get('debtEquity', None)
                val = round(float(de), 2) if de else None
            elif metric == 'ROIC':
                val = None  # Not available in free APIs
            elif metric == 'FCF Yield':
                val = None  # Not available in free APIs
            elif metric == 'PEG Ratio':
                val = info.get('pegRatio', None)
                val = round(float(val), 2) if val else None
            elif metric == 'Forward P/E':
                val = info.get('peForward', None)
                val = round(float(val), 2) if val else None
            elif metric == 'Interest Coverage Ratio':
                val = None  # Not available in free APIs
            elif metric == 'Current Ratio':
                val = info.get('currentRatioAnnual', None)
                val = round(float(val), 2) if val else None
            elif metric == 'Net Debt':
                val = None  # Not available in free APIs
            elif metric == 'Revenue Growth % (Future)':
                val = None  # Not available in free APIs
            elif metric == 'Free Cash Flow (FCF) Growth Rate':
                val = None  # Not available in free APIs
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

def fetch_all_metrics_for_ticker(ticker):
    """
    Fetch all supported metrics for a single ticker. Returns a dict of {metric: value}.
    Metrics not available via free APIs will be set to None.
    """
    info = {}
    try:
        finnhub_metrics = finnhub_client.company_basic_financials(ticker, 'all').get('metric', {})
    except Exception:
        finnhub_metrics = {}
    try:
        ticker_obj = yf.Ticker(ticker)
        yahoo_info = ticker_obj.info
        yahoo_fin = ticker_obj.financials if hasattr(ticker_obj, 'financials') else None
    except Exception:
        yahoo_info = {}
        yahoo_fin = None
    # Revenue Growth % (Past)
    try:
        hist = ticker_obj.history(period='5y')
        if len(hist) > 1:
            revs = hist['Close']
            info['Revenue Growth % (Past)'] = ((revs[-1] - revs[0]) / revs[0]) * 100 if revs[0] else None
        else:
            info['Revenue Growth % (Past)'] = None
    except Exception:
        info['Revenue Growth % (Past)'] = None
    # Revenue Growth % (Future) - Not available via free APIs
    info['Revenue Growth % (Future)'] = None
    # Operating Margin
    try:
        if yahoo_fin is not None:
            op_income = yahoo_fin.loc['Operating Income']
            rev = yahoo_fin.loc['Total Revenue']
            info['Operating Margin'] = (float(op_income[-1]) / float(rev[-1])) * 100 if rev[-1] else None
        else:
            info['Operating Margin'] = None
    except Exception:
        info['Operating Margin'] = None
    # Free Cash Flow (FCF) Growth Rate - Not available via free APIs
    info['Free Cash Flow (FCF) Growth Rate'] = None
    # FCF Yield - Not available via free APIs
    info['FCF Yield'] = None
    # Return on Invested Capital (ROIC) - Not available via free APIs
    info['Return on Invested Capital (ROIC)'] = None
    # Price/Sales (P/S) Ratio
    ps = finnhub_metrics.get('priceToSalesAnnual', None)
    if ps is None:
        ps = yahoo_info.get('priceToSalesTrailing12Months', None)
    info['Price/Sales (P/S) Ratio'] = round(float(ps), 2) if ps else None
    # Price to Earnings Growth (PEG) Ratio
    peg = finnhub_metrics.get('pegRatio', None)
    info['Price to Earnings Growth (PEG) Ratio'] = round(float(peg), 2) if peg else None
    # Forward P/E
    pef = finnhub_metrics.get('peForward', None)
    info['Forward P/E'] = round(float(pef), 2) if pef else None
    # Debt-to-Equity Ratio
    de = finnhub_metrics.get('debtEquity', None)
    if de is None:
        de = yahoo_info.get('debtToEquity', None)
    info['Debt-to-Equity Ratio'] = round(float(de), 2) if de else None
    # Interest Coverage Ratio - Not available via free APIs
    info['Interest Coverage Ratio'] = None
    # Current Ratio
    cr = finnhub_metrics.get('currentRatioAnnual', None)
    info['Current Ratio'] = round(float(cr), 2) if cr else None
    # Net Debt - Not available via free APIs
    info['Net Debt'] = None
    return info

class StockScreenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quick Stock Screener - Peer Comparison")
        self.metric_choices = [
            'Revenue Growth % (Past)',
            'Revenue Growth % (Future)',
            'Operating Margin',
            'Free Cash Flow (FCF) Growth Rate',
            'FCF Yield',
            'Return on Invested Capital (ROIC)',
            'Price/Sales (P/S) Ratio',
            'Price to Earnings Growth (PEG) Ratio',
            'Forward P/E',
            'Debt-to-Equity Ratio',
            'Interest Coverage Ratio',
            'Current Ratio',
            'Net Debt'
        ]
        self.all_metrics = {}
        self.create_widgets()

    def create_widgets(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(frm, text="Main Ticker:").grid(row=0, column=0, sticky="e")
        self.ticker_entry = ttk.Entry(frm, width=10)
        self.ticker_entry.grid(row=0, column=1, sticky="w")
        self.ticker_entry.insert(0, "PLTR")

        ttk.Label(frm, text="Peers (space-separated):").grid(row=0, column=2, sticky="e")
        self.peers_entry = ttk.Entry(frm, width=30)
        self.peers_entry.grid(row=0, column=3, sticky="w")
        self.peers_entry.insert(0, "SNOW CRWD")

        self.fetch_btn = ttk.Button(frm, text="Fetch Data", command=self.fetch_data)
        self.fetch_btn.grid(row=0, column=4, padx=10)

        ttk.Label(frm, text="Metric:").grid(row=1, column=0, sticky="e")
        self.metric_var = tk.StringVar()
        self.metric_dropdown = ttk.Combobox(frm, textvariable=self.metric_var, values=self.metric_choices, state="readonly", width=35)
        self.metric_dropdown.grid(row=1, column=1, columnspan=2, sticky="w")
        self.metric_dropdown.bind("<<ComboboxSelected>>", self.on_metric_selected)
        self.metric_dropdown.set(self.metric_choices[0])
        self.metric_dropdown.config(state="disabled")

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(frm, textvariable=self.status_var, foreground="blue")
        self.status_label.grid(row=2, column=0, columnspan=5, sticky="w")

    def fetch_data(self):
        ticker = self.ticker_entry.get().strip().upper()
        peers = self.peers_entry.get().strip().upper().split()
        if not ticker:
            messagebox.showerror("Input Error", "Please enter a main ticker.")
            return
        self.status_var.set("Fetching all metrics for all companies. Please wait...")
        self.fetch_btn.config(state="disabled")
        self.metric_dropdown.config(state="disabled")
        self.root.update()
        companies = [ticker] + peers
        self.all_metrics = {}
        for t in companies:
            self.all_metrics[t] = fetch_all_metrics_for_ticker(t)
        self.status_var.set(f"Fetched data for: {', '.join(companies)}")
        self.metric_dropdown.config(state="readonly")
        self.fetch_btn.config(state="normal")
        self.on_metric_selected()

    def on_metric_selected(self, event=None):
        metric = self.metric_var.get()
        if not metric or not self.all_metrics:
            return
        companies = list(self.all_metrics.keys())
        values = [self.all_metrics[s].get(metric, None) for s in companies]
        if all(v is None for v in values):
            messagebox.showinfo("Metric Not Available", f"{metric} is not available via free APIs and will show as N/A.")
        plot_peer_metric_bar(companies, values, metric)

if __name__ == "__main__":
    root = tk.Tk()
    app = StockScreenerApp(root)
    root.mainloop()
