🤖 Agentic Finance BNB — Autonomous Trading Agent

BNB Hack 2026 Submission AI Trading Agent Edition

🌟 Overview

Agentic Finance is an autonomous AI trading agent for BNB Chain. 

Unlike bots that wait for user clicks, this bot runs 24/7, scans markets using Tavily RAG, and autonomously DMs users when STRONG BUY/SELL opportunities are detected.

Built for BNB Hack: AI Trading Agent Edition

🎯 What Makes This "Agentic"

1. Autonomous Auto-Scanner — Scans BTC/ETH/BNB/XRP/SOL every 5 minutes without user input

2. Tavily RAG Brain — Real news → sentiment → trade decision. Not hardcoded.

3. Risk-Aware Execution — Every signal includes ATR-based Entry/Stop/Target + 1-10 Risk Score

✨ Features

🤖 Autonomous Trading Agent

- Auto-Scanner: Monitors 5 coins 24/7, alerts only on high-confidence signals

- Smart Intervals: 5 min baseline, drops to 1 min during high volatility 

- Zero Click Trading: Bot decides when to alert you, not the other way around

🧠 AI-Powered Analysis

- Tavily RAG: Powered by Tavily AI  08:15 UTC Real news summaries, not fake sentiment

- Multi-Source Data: CoinMarketCap + CoinGecko + Binance aggregated

- Technical Indicators: RSI, ATR, Support/Resistance calculated live

- Risk Score: 1-10 rating on every signal. HIGH risk = smaller position

📊 Risk Management 

- ATR-Based Levels: Entry/Stop/Target use Average True Range, not arbitrary %

- Risk/Reward Ratio: Shown on every signal. Example:  R/R: 1:1.67

- LONG + SHORT: Dynamic sizing. Shorts use Entry > Stop > Target logic

- On-Chain Gas: Real-time BNB Chain gas price affects signal score

🔗 BNB Chain Native

- Web3 RPC: Direct connection to `bsc-rpc.publicnode.com'

- Gas Tracker:  BNB Chain (3.0 Gwei) shown on every signal

- Trust Wallet: One-click HTTPS link → swap on BSC

- BEP-20 Ready: Architecture supports token trading

🏗️ Architecture

Agentic Finance BNB is built as a real-time, multi-layered AI Trading Agent focused on the BNB Smart Chain ecosystem.

Core System Flow

User Interface Layer

• Telegram Bot with rich inline keyboard menu

• One-click access to signals, sector map, whale radar, gas price, and AI intel

Data Acquisition Layer

• Primary: CoinMarketCap Pro API (price, volume, market cap, 24h change)

• Fallbacks: CoinGecko + Binance API

• On-Chain: BNB Smart Chain public RPCs (multiple endpoints with failover)

Technical Analysis Layer

• RSI (14-period)

• ATR (Average True Range) for volatility

• Dynamic Support & Resistance levels

• Multi-timeframe price action analysis

AI Intelligence Layer

• Tavily AI (Advanced Search + RAG) for real-time news and sentiment analysis

• Cleans and summarizes market news

• Detects bullish/bearish sentiment from latest sources

Risk & Decision Engine

• Combines price momentum, RSI, sentiment, and gas fees

• Calculates composite Risk Score (1-10)

• Generates intelligent BUY / SELL / HOLD signals with Entry, Stop Loss, and Target

Output & Execution Layer

• Formatted trading signals with clear rationale

• Direct Trust Wallet deep links for instant swap/send

• Auto-Scanner mode (autonomous background scanning every 5 minutes)

🛠️ Tech Stack

Core: Python 3.9+, python-telegram-bot, asyncio, aiohttp 

AI: Tavily RAG API — include_answer=True for clean summaries 

Data: CoinMarketCap API, CoinGecko API, Binance Klines 

Web3: web3.py → BNB Smart Chain RPC 

Deploy: Railway/Render + GitHub Actions

📦 Installation

git clone https://github.com/yourusername/agentic-finance-bnb.git
cd agentic-finance-bnb
pip install -r requirements.txt

requirements.txt

python-telegram-bot==20.7
aiohttp==3.9.1
web3==6.15.1
tavily-python==0.3.0

Environment

export TELEGRAM_BOT_TOKEN="your_token"
export CMC_API_KEY="your_cmc_key"
export TAVILY_API_KEY="your_tavily_key"


🚀 Usage For Judges — 30 Second Test:

1. /start
2. Tap 🤖 Auto-Scan → See "Autonomous trading agents powered by Tavily AI"
3. Tap 🧠 AI Intel → See Powered by Tavily AI | 07:23 UTC with real news
4. Tap 🔶 BNB → See Signal with Risk: 4/10 (MEDIUM) + Entry/Stop/Target + Tavily (Bullish)

📊 Example Autonomous Alert

🤖 Auto-Scan Alert

🚀 BNB (BNB)

📌 STRONG BUY | 85%
📊 Score: +3.2/10
⚠️ Risk: 4/10 (MEDIUM)

Price: $571.20
Entry: $571.15
Stop Loss: $566.30
Take Profit: $579.25
R/R: 1:1.67

AI Analysis
+2.35% move, RSI 58, bullish sentiment. BNB Chain achieved sub-second finality.

Data Sources
✅ CoinMarketCap
✅ Tavily (Bullish)
✅ BNB Chain (3.0 Gwei)

🕐 07:08 UTC
_Autonomous scan powered by Tavily AI_

🔥 Trade on Trust Wallet


🏆 Bounty Compliance

| Bounty | Implementation | Proof |
| --- | --- | --- |
| $36k Main Pool | Autonomous Auto-Scanner + ATR Risk Management + BNB Chain RPC | `Auto-Scanner ON` + Risk 1-10 + Gas price |
| $2k Tavily | RAG drives sentiment → signal score. Timestamp proof. | `Powered by Tavily AI \| 07:23 UTC` |
| $2k CMC | Primary price/volume/market cap source. CMC Rank shown. | `✅ CoinMarketCap` + `Mkt Cap: $87.2B` |
| $2k Trust Wallet | One-click HTTPS deep link to swap | `🔥 Trade on Trust Wallet` button |


🔒 API Rate Limits & Safety

 • CMC Free: 333 calls/day → 5 min scan = 288/day ✅ Safe
 
 • Tavily Free: 1000/month → Only scans when Auto-Scan ON ✅
 
 • User Cooldown: 2s between manual requests
 
 • No keys in repo: All via env vars

📝 License

MIT License - see LICENSE file

🙏 Acknowledgments

• BNB Chain for hackathon + RPC

• CoinMarketCap for price data API

• Tavily for RAG that actually works

• Trust Wallet for deep links

📞 Demo & Support

• Live Bot: https://t.me/YourBotUsername

• Demo Video: https://youtu.be/yourlink

• Telegram: @yourusername

Built for BNB Hack 2026 — AI Trading Agent Edition
Not financial advice. Autonomous agents can be wrong.


