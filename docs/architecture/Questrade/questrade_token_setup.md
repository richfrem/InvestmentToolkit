# Questrade API Token Setup Guide

This guide explains how to generate a Questrade API Refresh Token and securely store it as an environment variable.

## 1. Context for Personal Apps
For personal applications, the OAuth2 flow is simplified and does **NOT** require a `client_id` or `client_secret`.  One time 

- **Developer Portal**: [Questrade User Apps](https://apphub.questrade.com/UI/UserApps.aspx)
- **Token Redemption URL**: `https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<TOKEN>`

## 2. Generate Refresh Token

1.  Log in to your Questrade account.
2.  Go to **Account Management** > **API Centre**.
3.  Register a new application if you haven't already.
4.  Click on **Generate Token** for your application. This generates a **One-Week Application Token**.
5.  Use that application token to get your long-lived `refresh_token` by opening the redemption URL in your browser (or letting the app handle it):
    `https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<your_one_week_token>`
6.  Copy the **`refresh_token`** from the returned JSON response.

> [!WARNING]
> - **Application Tokens**: Last 7 days. They are only used to "seed" the first long-lived refresh token.
> - **Refresh Tokens**: Are **SINGLE-USE** and are rotated every time the app fetches new data.

### Example API Response
When you redeem your token (either via the script or manually), you will get a response like this:
```json
{
  "access_token": "<token>",
  "api_server": "https://api01.iq.questrade.com/",
  "expires_in": 1800,
  "refresh_token": "Rqk-<token>",
  "token_type": "Bearer"
}
```

> [!WARNING]
> Refresh tokens are single-use and expire if not redeemed. Once redeemed, a new refresh token will be issued.

## 2. Secure Storage (macOS/Linux)

For better security, we store the token as an environment variable in your shell profile rather than a plaintext `.env` file in the repository.

1.  Open your `~/.zshrc` (or `~/.bash_profile`) file:
    ```bash
    nano ~/.zshrc
    ```
2.  Add the following line at the end:
    ```bash
    export QUESTRADE_REFRESH_TOKEN="your_copied_refresh_token_here"
    ```
3.  Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).
4.  Reload your profile:
    ```bash
    source ~/.zshrc
    ```

## 3. How the App Uses the Token

The integration scripts will now look for the `QUESTRADE_REFRESH_TOKEN` environment variable. 

- On each run, the script will redeem the current token for a fresh one.
- **CRITICAL**: Since environment variables are static in the shell config, the script will need to update the *running* process environment. For persistent rotation across sessions, the script may still need to log the *latest* token for you to update in your `.zshrc` if a manual run is performed, or ideally, we manage a local cache that is *separate* from the repo.

> [!NOTE]
> The implementation will prioritize the environment variable but may provide a mechanism to output the rotated token so you can update your profile if the automated rotation (in-memory) isn't sufficient for your needs.
