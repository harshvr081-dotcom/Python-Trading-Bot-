# Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI for placing orders on the **Binance USDT-M Futures Testnet**.

## Project Structure

```
trading_bot/
├── main.py            # CLI layer (argparse, output formatting, error reporting)
├── binance_client.py  # API layer (HTTP, signing, error parsing)
├── validator.py       # Input validation (independent of CLI and API)
├── log_config.py      # Logging setup (rotating file + coloured console)
├── requirements.txt
├── logs/
│   └── trading_bot.log   # created automatically on first run
└── README.md
```

## Setup

### 1. Get Testnet Credentials

1. Visit <https://testnet.binancefuture.com> and log in with your GitHub account.
2. Go to **API Key** (top-right menu) → **Generate** a key pair.
3. Copy the **API Key** and **Secret Key**.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Credentials

**Recommended — environment variables (keeps secrets out of shell history):**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

Or pass them inline for a single run:

```bash
BINANCE_API_KEY="..." BINANCE_API_SECRET="..." python main.py ...
```

## Usage

```
python main.py --symbol SYMBOL --side {BUY,SELL} --type {MARKET,LIMIT}
               --quantity QTY [--price PRICE] [--tif {GTC,IOC,FOK}]
               [--api-key KEY] [--api-secret SECRET] [-v]
```

### Examples

```bash
# Market BUY 0.01 BTC
python main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Limit SELL 0.01 BTC at $90,000
python main.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000

# Verbose output (shows DEBUG logs in console)
python main.py --symbol ETHUSDT --side BUY --type MARKET --quantity 0.1 -v

# ETH Limit BUY with IOC time-in-force
python main.py --symbol ETHUSDT --side BUY --type LIMIT \
               --quantity 0.1 --price 2000 --tif IOC
```

### Sample Output

```
────────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol    : BTCUSDT
  Side      : BUY
  Type      : MARKET
  Quantity  : 0.01
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────────────────
  Order ID      : 3422651284
  Client Order  : web_abc123
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.01
  Executed Qty  : 0.01
  Avg Price     : 84321.50
  Update Time   : 2025-03-26 10:22:14 UTC
────────────────────────────────────────────────────────────

✅  Order placed successfully!  (orderId=3422651284, status=FILLED)
```

## CLI Arguments

| Argument | Required | Description |
|---|---|---|
| `--symbol` | ✅ | Trading pair, e.g. `BTCUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` | ✅ | `MARKET` or `LIMIT` |
| `--quantity` | ✅ | Order quantity |
| `--price` | LIMIT only | Limit price |
| `--tif` | No | Time-in-force: `GTC` (default) / `IOC` / `FOK` |
| `--api-key` | No* | Binance API key (or `BINANCE_API_KEY` env var) |
| `--api-secret` | No* | Binance API secret (or `BINANCE_API_SECRET` env var) |
| `-v` / `--verbose` | No | Show DEBUG logs on console |

\* Credentials must be provided via env var or CLI flag.

## Logging

All API requests, responses, and errors are logged to `logs/trading_bot.log` (rotating, max 5 MB × 3 files). Console output defaults to WARNING+ to stay clean; add `-v` for DEBUG-level detail.

## Error Handling

| Scenario | Exit Code | Output |
|---|---|---|
| Missing credentials | 1 | Clear instructions printed |
| Invalid CLI input | 2 | `VALIDATION ERROR: ...` |
| Binance API error | 3 | `API ERROR [code]: message` |
| Network / timeout | 4 | `NETWORK ERROR: ...` / `TIMEOUT: ...` |
| Unexpected error | 5 | `UNEXPECTED ERROR: ...` |

## Architecture

The code is split into three distinct layers with no upward dependencies:

```
CLI (main.py)
  └── uses Validator (validator.py)        ← pure logic, no I/O
  └── uses BinanceFuturesClient            ← HTTP + signing
        (binance_client.py)
  └── uses log_config.py                  ← logging setup only
```

- **`binance_client.py`** — knows nothing about CLI or argparse; can be imported as a library.
- **`validator.py`** — pure Python, zero dependencies; easily unit-tested.
- **`main.py`** — only concern is parsing user input and printing results.
