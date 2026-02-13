# Quickstart: Setting up Questrade Sync

## 1. Prerequisites
- A Questrade account.
- Questrade API access enabled (via the Questrade API Centre).
- macOS (preferred) with Python 3.x installed.

## 2. Generate Initial Token
1. Log in to [Questrade API Centre](https://api01.iq.questrade.com/api-centre).
2. Create a new "Personal App".
3. Copy the **Manual Refresh Token**.
   - *Note: This token is valid for one use and expires in 1 week if not used.*

## 3. Seed the Toolkit
1. Open the InvestmentToolkit dashboard.
2. Click **Setup Questrade**.
3. Paste the Manual Refresh Token into the input field.
4. Click **Connect**.

## 4. Run First Sync
Once connected, click the **Sync Now** button. 
- The toolkit will redeem your manual token for a rotating toolkit-managed token.
- Your `.questrade_cache` will be created.
- `portfolio.json` will update with your current holdings.

## 5. Troubleshooting
- **"Token Expired"**: Re-generate a manual token from Questrade and repeat step 3.
- **"API Error"**: Check your internet connection or verify Questrade API status.
