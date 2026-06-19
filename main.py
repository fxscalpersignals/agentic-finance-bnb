import os
import logging
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

# ================= CONFIG =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CMC_API_KEY = os.getenv("CMC_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

if not TOKEN:
    logging.error("❌ TELEGRAM_BOT_TOKEN not set!")
    exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

RPC_ENDPOINTS = [
    "https://bsc-rpc.publicnode.com",
    "https://bsc-dataseed.binance.org/",
]

w3 = None
if WEB3_AVAILABLE:
    for endpoint in RPC_ENDPOINTS:
        try:
            w3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                logging.info(f"✅ Web3 connected to {endpoint}")
                break
        except:
            continue

HEADERS = {"User-Agent": "AgenticFinance-BNBHack/4.0"}
TIMEOUT = aiohttp.ClientTimeout(total=12)

COINS = ["btc", "eth", "bnb", "xrp", "sol"]
COIN_SYMBOLS = {"btc": "BTC", "eth": "ETH", "bnb": "BNB", "xrp": "XRP", "sol": "SOL"}
COIN_NAMES = {"btc": "Bitcoin", "eth": "Ethereum", "bnb": "BNB", "xrp": "Ripple", "sol": "Solana"}

TRUST_REFERRAL = "https://link.trustwallet.com/open_url?coin_id=20000714&url=https://app.trustwallet.com/swap?asset=c20000714"

tavily = TavilyClient(api_key=TAVILY_KEY) if TAVILY_AVAILABLE and TAVILY_KEY else None

analytics = {"signals": 0, "gas_checks": 0, "tavily_used": 0, "onchain_checks": 0, "auto_scans": 0}
start_time = datetime.now()
gas_cache = {"price": None, "time": datetime.now()}
auto_scan_enabled = {} # NEW: Track which users have auto-scan on

# ================= HELPERS =================
def format_price(price):
    if not price: return "N/A"
    try:
        p = float(price)
        if p < 0.01: return f"${p:.6f}"
        elif p < 1: return f"${p:.4f}"
        elif p < 100: return f"${p:.2f}"
        return f"${p:,.0f}"
    except:
        return str(price)

def format_large_num(num):
    if not num: return "N/A"
    try:
        n = float(num)
        if n >= 1e9: return f"${n/1e9:.2f}B"
        elif n >= 1e6: return f"${n/1e6:.2f}M"
        elif n >= 1e3: return f"${n/1e3:.2f}K"
        return f"${n:.0f}"
    except:
        return str(num)

def clean_tavily_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'!\[Image[^\]]*\]', '', text)
    text = re.sub(r'#{1,6}\s*|\*{1,3}|_{1,3}|`{1,3}', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\|.*?\|', '', text)
    text = re.sub(r'---+|\||\s{2,}', ' ', text)
    text = re.sub(r'Pricing:.*?(USD|USDT)', '', text, flags=re.I)
    text = re.sub(r'Resistance\s*\d.*|Support\s*\d.*', '', text, flags=re.I)
    text = re.sub(r'TLDR.*?:|Daily.*?EMA|ASTER \d+', '', text, flags=re.I)
    text = re.sub(r'Binance\]|CoinGecko\]|Forbes\]|Marketcap', '', text, flags=re.I)
    text = re.sub(r'\d+\.\d+\s*%|[\$€£]\d+', '', text)
    text = re.sub(r'An image of.*', '', text, flags=re.I)
    text = re.sub(r'Image \d+:', '', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def summarize_tavily(text: str) -> str:
    text = clean_tavily_text(text)
    if not text: return ""

    sentences = re.split(r'[.!?]', text)
    for s in sentences:
        s = s.strip()
        if 15 < len(s) < 70 and not any(x in s.lower() for x in ['click', 'sign up', 'buy now', 'price', '$', '%', 'chart', 'http', 'image', 'select']):
            return s
    return ""

def calculate_risk_score(rsi: float, atr: float, price: float, sentiment: str, gas: float, change: float) -> Tuple[int, str]:
    """NEW: Calculate 1-10 risk score. Higher = riskier"""
    risk = 5 # Base risk

    # RSI risk
    if rsi > 80 or rsi < 20: risk += 2
    elif rsi > 70 or rsi < 30: risk += 1
    elif 40 < rsi < 60: risk -= 1

    # Volatility risk
    atr_pct = (atr / price) * 100
    if atr_pct > 5: risk += 2
    elif atr_pct > 3: risk += 1
    elif atr_pct < 1: risk -= 1

    # Sentiment risk
    if sentiment == "Bearish": risk += 1
    elif sentiment == "Bullish": risk -= 1

    # Gas risk
    if gas > 10: risk += 1
    elif gas < 3: risk -= 1

    # Momentum risk
    if abs(change) > 10: risk += 2
    elif abs(change) > 5: risk += 1

    risk = max(1, min(10, risk))

    if risk <= 3: label = "LOW"
    elif risk <= 6: label = "MEDIUM"
    elif risk <= 8: label = "HIGH"
    else: label = "EXTREME"

    return risk, label

def build_menu():
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data="sig_btc"), InlineKeyboardButton("Ξ ETH", callback_data="sig_eth")],
        [InlineKeyboardButton("🔶 BNB", callback_data="sig_bnb"), InlineKeyboardButton("💧 XRP", callback_data="sig_xrp")],
        [InlineKeyboardButton("◎ SOL", callback_data="sig_sol"), InlineKeyboardButton("📊 Sectors", callback_data="sectors")],
        [InlineKeyboardButton("🐋 Whales", callback_data="whale"), InlineKeyboardButton("🧠 AI Intel", callback_data="news")],
        [InlineKeyboardButton("🤖 Auto-Scan", callback_data="autoscantoggle"), InlineKeyboardButton("⛽ Gas", callback_data="gas")], # NEW
        [InlineKeyboardButton("📈 Stats", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= TECHNICAL INDICATORS =================
def calculate_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1: return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100.0
    if avg_gain == 0: return 0.0
    rs = avg_gain / avg_loss
    return max(0, min(100, 100 - (100 / (1 + rs))))

def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1: return 0.02 * closes[-1] if closes else 100
    trs = []
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        trs.append(max(hl, hc, lc))
    if not trs: return 0.02 * closes[-1]
    return sum(trs[-period:]) / period

def calculate_support_resistance(closes: List[float], highs: List[float], lows: List[float]) -> Tuple[float, float]:
    if len(closes) < 50:
        current = closes[-1] if closes else 100
        return current * 0.97, current * 1.03
    recent_highs = highs[-50:]
    recent_lows = lows[-50:]
    resistance = max(recent_highs)
    support = min(recent_lows)
    current = closes[-1]
    if current > resistance * 0.98:
        resistance = resistance * 1.05
    return support, resistance

# ================= BNB CHAIN =================
async def get_bnb_gas_price() -> Dict:
    global gas_cache
    if (datetime.now() - gas_cache["time"]).total_seconds() < 30 and gas_cache["price"] is not None:
        return {"gwei": gas_cache["price"], "source": "Cache"}

    gas_price = None
    source = "Unknown"

    if w3 and w3.is_connected():
        try:
            gas_wei = w3.eth.gas_price
            gas_price = float(w3.from_wei(gas_wei, 'gwei'))
            source = "BNB Chain"
        except:
            pass

    if gas_price is None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.bscscan.com/api?module=gastracker&action=gasoracle", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "1":
                            gas_price = float(data["result"]["ProposeGasPrice"])
                            source = "BSCScan"
        except:
            pass

    if gas_price is None or gas_price <= 0:
        gas_price = 3.0
        source = "Fallback"

    gas_cache["price"] = gas_price
    gas_cache["time"] = datetime.now()
    analytics["gas_checks"] += 1
    return {"gwei": round(gas_price, 2), "source": source}

# ================= SESSION =================
async def get_session(app):
    if "session" not in app.bot_data:
        app.bot_data["session"] = aiohttp.ClientSession(timeout=TIMEOUT)
    return app.bot_data["session"]

async def close_session(app):
    session = app.bot_data.get("session")
    if session and not session.closed:
        await session.close()

async def init_app(app):
    await get_session(app)
    logging.info("✅ Application initialized")

# ================= PRICE FETCH =================
async def fetch_with_retry(session, url, headers=None, retries=2):
    for _ in range(retries):
        try:
            async with session.get(url, headers=headers or HEADERS, timeout=8) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            await asyncio.sleep(0.5)
    return None

async def fetch_price(session, symbol: str) -> Optional:
    if not CMC_API_KEY: return None
    try:
        await asyncio.sleep(0.6)
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={COIN_SYMBOLS[symbol]}"
        data = await fetch_with_retry(session, url, {"X-CMC_PRO_API_KEY": CMC_API_KEY})
        if data and "data" in data and COIN_SYMBOLS[symbol] in data["data"]:
            item = data["data"][COIN_SYMBOLS[symbol]]["quote"]["USD"]
            return {
                "price": float(item["price"]),
                "change": float(item.get("percent_change_24h", 0)),
                "volume": float(item.get("volume_24h", 0)),
                "market_cap": float(item.get("market_cap", 0)),
                "cmc_rank": int(item.get("cmc_rank", 0)),
                "source": "CoinMarketCap"
            }
    except Exception as e:
        logging.debug(f"CMC error: {e}")
    return None

async def fetch_klines(session, symbol: str, limit: int = 100) -> Optional:
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}USDT&interval=1h&limit={limit}"
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "closes": [float(c[4]) for c in data],
                    "highs": [float(c[2]) for c in data],
                    "lows": [float(c[3]) for c in data],
                }
    except Exception as e:
        logging.debug(f"Klines error: {e}")
    return None

# ================= SECTOR MAP =================
async def get_sector_map(session) -> str:
    sectors = {
        "AI/DePIN": ["eth", "sol"],
        "DeFi": ["bnb", "eth"],
        "Payments": ["xrp"],
        "Layer 1": ["sol", "bnb"],
        "RWA": ["btc"]
    }
    msg = "*Sector Map*\n\n"

    for sector, coins in sectors.items():
        changes = []
        for c in coins:
            data = await fetch_price(session, c)
            if data: changes.append(data["change"])

        if changes:
            avg = sum(changes) / len(changes)
            emoji = "🚀" if avg > 3 else "🟢" if avg > 0 else "🔴" if avg < -3 else "🟡"
            msg += f"{emoji} *{sector}*: {avg:+.2f}%\n"
    return msg + "\n_Built on BNB Smart Chain_"

# ================= TAVILY AI =================
async def get_tavily_analysis(symbol: str) -> Tuple[str, str]:
    news_summary = ""
    sentiment = "Neutral"

    if tavily:
        try:
            response = tavily.search(
                query=f"{symbol} crypto news sentiment",
                search_depth="advanced",
                include_answer=True,
                max_results=3
            )

            answer = response.get("answer", "")
            if answer:
                news_summary = summarize_tavily(answer)

                content_lower = answer.lower()
                if any(w in content_lower for w in ["bullish", "surge", "rally", "gain", "up", "breakout", "positive"]):
                    sentiment = "Bullish"
                elif any(w in content_lower for w in ["bearish", "drop", "decline", "down", "fall", "crash", "negative"]):
                    sentiment = "Bearish"
                else:
                    sentiment = "Mixed"

                analytics["tavily_used"] += 1
                logging.info(f"✅ Tavily: {symbol} - {sentiment} - {news_summary}")

        except Exception as e:
            logging.error(f"Tavily error: {e}")

    return news_summary, sentiment

# ================= AI INTEL =================
async def get_ai_intel() -> str:
    if not tavily:
        return "*AI Intel*\n\nTavily API not configured.\n\n_Built on BNB Smart Chain_"

    try:
        response = tavily.search(
            query="BNB Chain cryptocurrency market news",
            search_depth="advanced",
            include_answer=True,
            max_results=5
        )

        msg = "*AI Market Intelligence*\n\n"
        answer = response.get("answer", "")

        if answer:
            clean_answer = clean_tavily_text(answer)
            sentences = re.split(r'[.!?]', clean_answer)
            count = 0
            for s in sentences:
                s = s.strip()
                if 20 < len(s) < 100 and count < 3:
                    msg += f"• {s}\n\n"
                    count += 1
            if count == 0:
                msg += "No recent news found.\n\n"
        else:
            msg += "No recent news found.\n\n"

        timestamp = datetime.now().strftime("%H:%M UTC")
        return msg + f"_Powered by Tavily AI_ | {timestamp}"
    except Exception as e:
        logging.error(f"AI Intel error: {e}")
        return f"*AI Intel*\n\nError loading news.\n\n_Built on BNB Smart Chain_"

# ================= SIGNAL GENERATION =================
async def generate_signal(session, symbol: str) -> Optional:
    price_data = await fetch_price(session, symbol)
    if not price_data: return None

    klines = await fetch_klines(session, symbol)
    current_price = price_data["price"]
    change = price_data["change"]

    rsi = 50
    atr = current_price * 0.02
    support = current_price * 0.97
    resistance = current_price * 1.03

    if klines and len(klines["closes"]) > 20:
        closes = klines["closes"]
        highs = klines["highs"]
        lows = klines["lows"]
        rsi = calculate_rsi(closes)
        atr = calculate_atr(highs, lows, closes)
        support, resistance = calculate_support_resistance(closes, highs, lows)

    news_summary, sentiment = await get_tavily_analysis(symbol)
    gas = await get_bnb_gas_price()

    score = 0
    if change > 2: score += 3
    elif change > 0.5: score += 1.5
    elif change > -0.5: score += 0
    elif change > -2: score -= 1.5
    else: score -= 3

    if rsi < 30: score += 2
    elif rsi < 40: score += 1
    elif rsi > 70: score -= 2
    elif rsi > 60: score -= 1

    if sentiment == "Bullish": score += 3
    elif sentiment == "Bearish": score -= 3

    if gas["gwei"] < 5: score += 1.5
    elif gas["gwei"] > 10: score -= 1.5

    if score >= 3:
        signal, confidence, direction = "STRONG BUY", "85%", "LONG"
    elif score >= 1.5:
        signal, confidence, direction = "BUY", "70%", "LONG"
    elif score >= -0.5:
        signal, confidence, direction = "HOLD", "60%", "NEUTRAL"
    elif score >= -2:
        signal, confidence, direction = "SELL", "70%", "SHORT"
    else:
        signal, confidence, direction = "STRONG SELL", "85%", "SHORT"

    if direction == "LONG":
        entry = current_price * 0.995
        stop = entry - (atr * 1.5)
        target = entry + (atr * 2.5)
    elif direction == "SHORT":
        entry = current_price * 1.005
        stop = entry + (atr * 1.5)
        target = entry - (atr * 2.5)
    else:
        entry = current_price
        stop = current_price * 0.95
        target = current_price * 1.05

    risk = abs(entry - stop)
    reward = abs(target - entry)
    risk_reward = (reward / risk) if risk > 0 else 0

    reasoning = f"{change:+.2f}% move, RSI {rsi:.0f}, {sentiment.lower()} sentiment"
    if news_summary:
        reasoning += f". {news_summary}"
    if len(reasoning) > 150:
        reasoning = reasoning[:147] + "..."

    # NEW: Calculate risk score
    risk_score, risk_label = calculate_risk_score(rsi, atr, current_price, sentiment, gas["gwei"], change)

    analytics["signals"] += 1

    return {
        "symbol": symbol.upper(),
        "name": COIN_NAMES[symbol],
        "price": current_price,
        "change": change,
        "volume": price_data.get("volume", 0),
        "market_cap": price_data.get("market_cap", 0),
        "cmc_rank": price_data.get("cmc_rank", 0),
        "signal": signal,
        "confidence": confidence,
        "score": round(score, 1),
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": round(risk_reward, 2),
        "support": round(support, 4),
        "resistance": round(resistance, 4),
        "risk_score": risk_score, # NEW
        "risk_label": risk_label, # NEW
        "reasoning": reasoning,
        "source": price_data.get("source", "CMC"),
        "gas": gas,
        "sentiment": sentiment,
        "tavily_used": bool(news_summary),
        "rsi": round(rsi, 1),
        "atr": round(atr, 4),
        "timestamp": datetime.now().strftime("%H:%M UTC")
    }

# ================= AUTO-SCANNER =================
async def auto_scan_market(session, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """NEW: Autonomous scanner - finds best opportunity"""
    analytics["auto_scans"] += 1
    signals = []

    for coin in COINS:
        signal = await generate_signal(session, coin)
        if signal and signal["direction"]!= "NEUTRAL":
            signals.append(signal)

    if not signals:
        return None

    # Sort by score, pick best
    best_signal = max(signals, key=lambda x: abs(x["score"]))

    # Only alert if strong signal
    if abs(best_signal["score"]) >= 2.0:
        emoji = "🚀" if "BUY" in best_signal['signal'] else "📉"
        msg = (
            f"🤖 *Auto-Scan Alert*\n\n"
            f"{emoji} *{best_signal['symbol']} ({best_signal['name']})*\n\n"
            f"📌 *{best_signal['signal']}* | {best_signal['confidence']}\n"
            f"📊 Score: {best_signal['score']:+.1f}/10\n"
            f"⚠️ Risk: {best_signal['risk_score']}/10 ({best_signal['risk_label']})\n\n"
            f"*Price*: {format_price(best_signal['price'])}\n"
            f"*Entry*: {format_price(best_signal['entry'])}\n"
            f"*Stop*: {format_price(best_signal['stop'])}\n"
            f"*Target*: {format_price(best_signal['target'])}\n\n"
            f"*AI Analysis*\n"
            f"{best_signal['reasoning']}\n\n"
            f"🕐 {best_signal['timestamp']}\n"
            f"_Autonomous scan powered by Tavily AI_"
        )

        kb = [[InlineKeyboardButton("🔥 Trade on Trust Wallet", url=TRUST_REFERRAL)]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return best_signal
    return None

# ================= WHALE RADAR =================
async def get_whale_radar(session) -> str:
    msg = "*Whale Radar*\n\n"
    moves = []
    for symbol in COINS:
        data = await fetch_price(session, symbol)
        if data: moves.append((symbol.upper(), data["change"]))

    if not moves: return "No data available.\n\n_Built on BNB Smart Chain_"

    moves.sort(key=lambda x: abs(x[1]), reverse=True)
    for sym, change in moves[:5]:
        emoji = "🚨" if abs(change) >= 5 else "📈" if change > 0 else "📉"
        msg += f"{emoji} *{sym}*: {change:+.2f}%\n"
    return msg + "\n_Built on BNB Smart Chain_"

# ================= STATS =================
async def get_stats() -> str:
    uptime = str(datetime.now() - start_time).split(".")[0]
    return f"""*Bot Statistics*

⏱️ *Uptime*: {uptime}
📈 *Signals*: {analytics['signals']}
🤖 *Auto-Scans*: {analytics['auto_scans']}
⛽ *Gas Checks*: {analytics['gas_checks']}
🧠 *Tavily Calls*: {analytics['tavily_used']}
🔗 *On-Chain*: {analytics['onchain_checks']}

*System Status*
🔌 Web3: {'✅ Connected' if w3 and w3.is_connected() else '⚠️ Fallback'}
🧠 Tavily: {'✅ Active' if tavily else '❌ Disabled'}
💹 CMC: {'✅ Active' if CMC_API_KEY else '❌ Disabled'}

🚀 *BNB Hack 2026*"""

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = f"""🚀 *Agentic Finance BNB*

Welcome {user.first_name}!

*Three-Layer AI Signals:*
📊 Market Data → CoinMarketCap
🧠 News Intel → Tavily AI
⛓️ On-Chain → BNB Smart Chain

🤖 *NEW: Auto-Scanner* - Bot finds trades for you

Get real-time signals with Entry/Stop/Target.

⚠️ *Not financial advice.*

Select an asset:"""
    await update.message.reply_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    session = await get_session(context.application)
    user_id = query.from_user.id

    try:
        if action.startswith("sig_"):
            symbol = action.split("_")[1]
            await query.edit_message_text(f"🔄 *Analyzing {symbol.upper()}...*\n\nGathering market + AI news + on-chain data...")

            signal = await generate_signal(session, symbol)
            if not signal:
                await query.edit_message_text("⚠️ Data unavailable. Please try again.", reply_markup=build_menu())
                return

            emoji = "🚀" if "BUY" in signal['signal'] else "📉" if "SELL" in signal['signal'] else "⚡"

            kb = [
                [InlineKeyboardButton("🔥 Trade on Trust Wallet", url=TRUST_REFERRAL)],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
            ]

            rank_text = f" | #{signal['cmc_rank']}" if signal['cmc_rank'] > 0 else ""

            msg = (
                f"{emoji} *{signal['symbol']} ({signal['name']})*{rank_text}\n\n"
                f"📌 *{signal['signal']}* | {signal['confidence']}\n"
                f"📊 Score: {signal['score']:+.1f}/10\n"
                f"⚠️ Risk: {signal['risk_score']}/10 ({signal['risk_label']})\n\n"
                f"*Price*: {format_price(signal['price'])}\n"
                f"*24h*: {signal['change']:+.2f}%\n"
                f"*Volume*: {format_large_num(signal.get('volume', 0))}\n"
                f"*Mkt Cap*: {format_large_num(signal.get('market_cap', 0))}\n"
                f"*RSI*: {signal.get('rsi', 'N/A')}\n\n"
                f"*Entry*: {format_price(signal['entry'])}\n"
                f"*Stop Loss*: {format_price(signal['stop'])}\n"
                f"*Take Profit*: {format_price(signal['target'])}\n"
                f"*R/R*: 1:{signal.get('risk_reward', 0):.2f}\n\n"
                f"*S/R*: {format_price(signal['support'])} / {format_price(signal['resistance'])}\n\n"
                f"*AI Analysis*\n"
                f"{signal['reasoning']}\n\n"
                f"*Data Sources*\n"
                f"✅ {signal['source']}\n"
                f"{'✅' if signal.get('tavily_used') else '⚠️'} Tavily ({signal['sentiment']})\n"
                f"✅ BNB Chain ({signal['gas']['gwei']} Gwei)\n\n"
                f"🕐 {signal['timestamp']}\n"
                f"_Built on BNB Smart Chain_"
            )

            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

        elif action == "news":
            msg = await get_ai_intel()
            await query.edit_message_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

        elif action == "whale":
            msg = await get_whale_radar(session)
            await query.edit_message_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

        elif action == "sectors":
            msg = await get_sector_map(session)
            await query.edit_message_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

        elif action == "autoscantoggle": # NEW
            if user_id in auto_scan_enabled:
                auto_scan_enabled[user_id] = not auto_scan_enabled[user_id]
            else:
                auto_scan_enabled[user_id] = True

            status = "ON ✅" if auto_scan_enabled[user_id] else "OFF ❌"
            msg = (
                f"🤖 *Auto-Scanner {status}*\n\n"
                f"When ON, the bot autonomously scans all 5 coins every 5 minutes and alerts you to STRONG BUY/SELL opportunities.\n\n"
                f"*Current Status*: {status}\n\n"
                f"_Autonomous trading agents powered by Tavily AI_"
            )

            # Start auto-scan task if enabled
            if auto_scan_enabled[user_id]:
                asyncio.create_task(run_auto_scan(user_id, context))

            await query.edit_message_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

        elif action == "gas":
            gas = await get_bnb_gas_price()
            await query.edit_message_text(
                f"*BNB Chain Gas Price*\n\n"
                f"*Current*: {gas['gwei']} Gwei\n"
                f"*Source*: {gas['source']}\n\n"
                f"_Lower gas = cheaper transactions_\n\n"
                f"⚡ *BNB Hack 2026*",
                reply_markup=build_menu(),
                parse_mode=ParseMode.MARKDOWN
            )

        elif action == "stats":
            msg = await get_stats()
            await query.edit_message_text(msg, reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

        elif action == "back":
            await query.edit_message_text("*Main Menu*\n\nSelect an asset to analyze:", reply_markup=build_menu(), parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"Error: {e}")
        await query.edit_message_text("⚠️ Error occurred. Please try again.", reply_markup=build_menu())

async def run_auto_scan(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """NEW: Autonomous scanner runs every 5 minutes"""
    session = await get_session(context.application)
    while auto_scan_enabled.get(user_id, False):
        try:
            await auto_scan_market(session, user_id, context)
            await asyncio.sleep(300) # 5 minutes
        except Exception as e:
            logging.error(f"Auto-scan error: {e}")
            await asyncio.sleep(300)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

# ================= MAIN =================
def main():
    logging.info("🚀 Starting Agentic Finance BNB v4.0...")
    logging.info(f"Web3: {'✅' if w3 and w3.is_connected() else '⚠️ Fallback'}")
    logging.info(f"Tavily: {'✅' if tavily else '❌ Disabled'}")
    logging.info(f"CMC: {'✅' if CMC_API_KEY else '❌ Disabled'}")

    application = (
        ApplicationBuilder()
     .token(TOKEN)
     .post_init(init_app)
     .post_shutdown(close_session)
     .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    logging.info("✅ Bot is LIVE! Built for BNB Hack 2026")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
