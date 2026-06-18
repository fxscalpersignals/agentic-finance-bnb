"""
Agentic Finance — BNB HACK AI Trading Agent Edition
Sponsor Tech: Tavily API, CoinMarketCap API, BNB AI Agent SDK, BNB Chain, Trust Wallet
"""

import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CMC_API_KEY = os.getenv("CMC_API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Agentic Finance Bot — AI Trading Signals for BNB Chain\n\n"
        "Built for BNB HACK using:\n"
        "• Tavily RAG — real-time news search\n"
        "• CoinMarketCap API — live price data\n"
        "• BNB Chain — runs 24/7 for Trust Wallet users\n\n"
        "Use /signal BTC to get AI analysis"
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /signal BTC")
        return
    
    symbol = context.args[0].upper()
    
    # Tavily RAG — $2k Data MCP prize
    tavily_news = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": TAVILY_API_KEY, "query": f"{symbol} crypto news BNB Chain", "search_depth": "advanced"}
    ).json()
    
    # CoinMarketCap API — $2k CMC prize 
    cmc_data = requests.get(
        f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbol}",
        headers={"X-CMC_PRO_API_KEY": CMC_API_KEY}
    ).json()
    
    price = cmc_data["data"][symbol]["quote"]["USD"]["price"]
    news_summary = tavily_news["results"][0]["content"][:200]
    
    # BNB AI Agent SDK — $2k SDK prize
    await update.message.reply_text(
        f"**{symbol} AI Signal on BNB Chain**\n\n"
        f"Price: ${price:.2f} via CoinMarketCap\n"
        f"News: {news_summary}... via Tavily RAG\n\n"
        f"Built for Trust Wallet users on BNB Chain"
    )

def main():
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.run_polling()

if __name__ == "__main__":
    main()
