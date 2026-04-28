import json
from datetime import datetime, timedelta
from typing import Any, Literal

import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from requests import Session
from yfinance import Ticker

from mcp_yahoo_finance.utils import generate_tool, validate_date, validate_symbol


class YahooFinance:
    def __init__(self, session: Session | None = None, verify: bool = True) -> None:
        self.session = session

        if self.session:
            self.session.verify = verify

    def get_current_stock_price(self, symbol: str) -> str:
        """Get the current stock price based on stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session).info
            current_price = stock.get("regularMarketPrice") or stock.get("currentPrice")
            if current_price is None:
                return f"Couldn't fetch {symbol} current price"
            return f"{current_price:.4f}"
        except Exception as e:
            return f"Error fetching {symbol}: {str(e)}"

    def get_stock_price_by_date(self, symbol: str, date: str) -> str:
        """Get the stock price for a given stock symbol on a specific date.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            date (str): The date in YYYY-MM-DD format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=date, param_name="date")
            stock = Ticker(ticker=symbol, session=self.session)
            price = stock.history(start=date, period="1d")
            if price.empty:
                return f"Error: No trading data found for {symbol} on {date}"
            return f"{price.iloc[0]['Close']:.4f}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_stock_price_date_range(
        self, symbol: str, start_date: str, end_date: str
    ) -> str:
        """Get the stock prices for a given date range for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            start_date (str): The start date in YYYY-MM-DD format.
            end_date (str): The end date in YYYY-MM-DD format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=start_date, param_name="start_date")
            validate_date(date_str=end_date, param_name="end_date")

            stock = Ticker(ticker=symbol, session=self.session)
            end = (
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")
            prices = stock.history(start=start_date, end=end)
            if prices.empty:
                return f"Error: No trading data found for {symbol} between {start_date} and {end_date}"
            prices.index = prices.index.astype(str)
            return f"{prices['Close'].to_json(orient='index')}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_historical_stock_prices(
        self,
        symbol: str,
        period: Literal[
            "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
        ] = "1mo",
        interval: Literal["1d", "5d", "1wk", "1mo", "3mo"] = "1d",
    ) -> str:
        """Get historical stock prices for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            period (str): The period for historical data. Defaults to "1mo".
                    Valid periods: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
            interval (str): The interval beween data points. Defaults to "1d".
                    Valid intervals: "1d", "5d", "1wk", "1mo", "3mo"
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            prices = stock.history(period=period, interval=interval)
            if prices.empty:
                return f"Error: No historical data found for {symbol}"

            if hasattr(prices.index, "date"):
                prices.index = prices.index.date.astype(str)  # type: ignore
            return f"{prices['Close'].to_json(orient='index')}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_dividends(self, symbol: str) -> str:
        """Get dividends for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            dividends = stock.dividends

            if dividends.empty:
                return f"Error: No dividend data found for {symbol}"

            if hasattr(dividends.index, "date"):
                dividends.index = dividends.index.date.astype(str)  # type: ignore
            return f"{dividends.to_json(orient='index')}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_income_statement(
        self, symbol: str, freq: Literal["yearly", "quarterly", "trailing"] = "yearly"
    ) -> str:
        """Get income statement for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            freq (str): At what frequency to get cashflow statements. Defaults to "yearly".
                    Valid freqencies: "yearly", "quarterly", "trainling"
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            income_statement = stock.get_income_stmt(freq=freq, pretty=True)

            if isinstance(income_statement, pd.DataFrame):
                income_statement.columns = [
                    str(col.date()) for col in income_statement.columns
                ]
                return f"{income_statement.to_json()}"
            return f"{income_statement}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_cashflow(
        self, symbol: str, freq: Literal["yearly", "quarterly", "trailing"] = "yearly"
    ) -> str:
        """Get cashflow for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            freq (str): At what frequency to get cashflow statements. Defaults to "yearly".
                    Valid freqencies: "yearly", "quarterly", "trainling"
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            cashflow = stock.get_cashflow(freq=freq, pretty=True)

            if isinstance(cashflow, pd.DataFrame):
                cashflow.columns = [str(col.date()) for col in cashflow.columns]
                return f"{cashflow.to_json(indent=2)}"
            return f"{cashflow}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_earning_dates(self, symbol: str, limit: int = 12) -> str:
        """Get earning dates.


        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            limit (int): max amount of upcoming and recent earnings dates to return. Default value 12 should return next 4 quarters and last 8 quarters. Increase if more history is needed.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            if limit < 1 or limit > 100:
                return "Error: limit must be between 1 and 100"
            stock = Ticker(ticker=symbol, session=self.session)
            earning_dates = stock.get_earnings_dates(limit=limit)

            if isinstance(earning_dates, pd.DataFrame):
                earning_dates.index = earning_dates.index.date.astype(str)  # type: ignore
                return f"{earning_dates.to_json(indent=2)}"
            return f"{earning_dates}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_news(self, symbol: str) -> str:
        """Get news for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            if not stock.news:
                return f"Error: No news found for {symbol}"
            return json.dumps(stock.news, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_recommendations(self, symbol: str) -> str:
        """Get analyst recommendations for a given symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            recommendations = stock.get_recommendations()
            if isinstance(recommendations, pd.DataFrame):
                return f"{recommendations.to_json(orient='records', indent=2)}"
            return f"{recommendations}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _filter_options_df(
        self,
        df: pd.DataFrame,
        min_strike: float = 0,
        max_strike: float = 0,
        min_volume: int = 0,
        min_open_interest: int = 0,
        in_the_money_only: bool = False,
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        f = df.copy()
        if min_strike > 0:
            f = f[f["strike"] >= min_strike]
        if max_strike > 0:
            f = f[f["strike"] <= max_strike]
        if min_volume > 0:
            f = f[f["volume"].fillna(0) >= min_volume]
        if min_open_interest > 0:
            f = f[f["openInterest"].fillna(0) >= min_open_interest]
        if in_the_money_only:
            f = f[f["inTheMoney"] == True]  # noqa: E712
        return f

    def _serialize_options_df(self, df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        df = df.copy()
        if "lastTradeDate" in df.columns:
            df["lastTradeDate"] = df["lastTradeDate"].astype(str)
        return df.to_dict(orient="records")

    def get_option_expiration_dates(self, symbol: str) -> str:
        """Get available options expiration dates for a given stock symbol.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            expiration_dates = stock.options
            if not expiration_dates:
                return f"Error: No options data found for {symbol}"
            return json.dumps(list(expiration_dates), indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_option_chain(self, symbol: str, expiration_date: str) -> str:
        """Get options chain for a specific expiration date.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            expiration_date (str): Options expiration date in YYYY-MM-DD format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=expiration_date, param_name="expiration_date")
            stock = Ticker(ticker=symbol, session=self.session)
            option_chain = stock.option_chain(expiration_date)

            def _convert_dates(df: pd.DataFrame) -> pd.DataFrame:
                if df is None or "lastTradeDate" not in df.columns:
                    return df
                df = df.copy()
                df["lastTradeDate"] = df["lastTradeDate"].astype(str)
                return df

            result = {
                "calls": None,
                "puts": None,
                "underlying": option_chain.underlying,
            }

            if option_chain.calls is not None:
                result["calls"] = _convert_dates(option_chain.calls).to_dict(
                    orient="records"
                )

            if option_chain.puts is not None:
                result["puts"] = _convert_dates(option_chain.puts).to_dict(
                    orient="records"
                )

            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"


    def get_calls(
        self,
        symbol: str,
        expiration_date: str,
        min_strike: float = 0,
        max_strike: float = 0,
        min_volume: int = 0,
        min_open_interest: int = 0,
        in_the_money_only: bool = False,
    ) -> str:
        """Get call options for a specific expiration date with optional filters.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            expiration_date (str): Options expiration date in YYYY-MM-DD format.
            min_strike (float): Minimum strike price filter. 0 means no filter.
            max_strike (float): Maximum strike price filter. 0 means no filter.
            min_volume (int): Minimum volume filter. 0 means no filter.
            min_open_interest (int): Minimum open interest filter. 0 means no filter.
            in_the_money_only (bool): If true, only return in-the-money options.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=expiration_date, param_name="expiration_date")
            stock = Ticker(ticker=symbol, session=self.session)
            chain = stock.option_chain(expiration_date)
            calls = self._filter_options_df(
                chain.calls,
                min_strike,
                max_strike,
                min_volume,
                min_open_interest,
                in_the_money_only,
            )
            result = self._serialize_options_df(calls)
            if not result:
                return f"No call options found for {symbol} at {expiration_date} with given filters"
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_puts(
        self,
        symbol: str,
        expiration_date: str,
        min_strike: float = 0,
        max_strike: float = 0,
        min_volume: int = 0,
        min_open_interest: int = 0,
        in_the_money_only: bool = False,
    ) -> str:
        """Get put options for a specific expiration date with optional filters.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            expiration_date (str): Options expiration date in YYYY-MM-DD format.
            min_strike (float): Minimum strike price filter. 0 means no filter.
            max_strike (float): Maximum strike price filter. 0 means no filter.
            min_volume (int): Minimum volume filter. 0 means no filter.
            min_open_interest (int): Minimum open interest filter. 0 means no filter.
            in_the_money_only (bool): If true, only return in-the-money options.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=expiration_date, param_name="expiration_date")
            stock = Ticker(ticker=symbol, session=self.session)
            chain = stock.option_chain(expiration_date)
            puts = self._filter_options_df(
                chain.puts,
                min_strike,
                max_strike,
                min_volume,
                min_open_interest,
                in_the_money_only,
            )
            result = self._serialize_options_df(puts)
            if not result:
                return f"No put options found for {symbol} at {expiration_date} with given filters"
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_options_multi_expiry(self, symbol: str, num_expirations: int = 3) -> str:
        """Get options chains across the next N expiration dates.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            num_expirations (int): Number of upcoming expiration dates to include. Defaults to 3.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)
            dates = stock.options
            if not dates:
                return f"Error: No options data found for {symbol}"

            dates = list(dates)[:num_expirations]
            result = {}
            for date in dates:
                chain = stock.option_chain(date)
                result[date] = {
                    "calls": self._serialize_options_df(chain.calls),
                    "puts": self._serialize_options_df(chain.puts),
                }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_options_summary(self, symbol: str, expiration_date: str) -> str:
        """Get summary statistics for options at a specific expiration date. Includes volume, open interest, put/call ratios, implied volatility stats, and max pain strike.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            expiration_date (str): Options expiration date in YYYY-MM-DD format.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            validate_date(date_str=expiration_date, param_name="expiration_date")
            stock = Ticker(ticker=symbol, session=self.session)
            chain = stock.option_chain(expiration_date)

            calls = chain.calls
            puts = chain.puts

            call_vol = int(calls["volume"].fillna(0).sum())
            put_vol = int(puts["volume"].fillna(0).sum())
            call_oi = int(calls["openInterest"].fillna(0).sum())
            put_oi = int(puts["openInterest"].fillna(0).sum())

            call_iv = calls["impliedVolatility"].dropna()
            put_iv = puts["impliedVolatility"].dropna()

            strikes = sorted(
                set(calls["strike"].tolist() + puts["strike"].tolist())
            )
            call_strikes = calls[["strike", "openInterest"]].fillna(0).values.tolist()
            put_strikes = puts[["strike", "openInterest"]].fillna(0).values.tolist()

            max_pain_strike = strikes[0] if strikes else 0
            min_pain = float("inf")
            for s in strikes:
                pain = sum(max(0, s - k) * oi for k, oi in call_strikes) + sum(
                    max(0, k - s) * oi for k, oi in put_strikes
                )
                if pain < min_pain:
                    min_pain = pain
                    max_pain_strike = s

            summary = {
                "symbol": symbol,
                "expiration_date": expiration_date,
                "call_volume": call_vol,
                "put_volume": put_vol,
                "total_volume": call_vol + put_vol,
                "put_call_volume_ratio": round(put_vol / call_vol, 4)
                if call_vol > 0
                else None,
                "call_open_interest": call_oi,
                "put_open_interest": put_oi,
                "total_open_interest": call_oi + put_oi,
                "put_call_oi_ratio": round(put_oi / call_oi, 4)
                if call_oi > 0
                else None,
                "call_iv": {
                    "mean": round(float(call_iv.mean()), 4)
                    if not call_iv.empty
                    else None,
                    "min": round(float(call_iv.min()), 4)
                    if not call_iv.empty
                    else None,
                    "max": round(float(call_iv.max()), 4)
                    if not call_iv.empty
                    else None,
                },
                "put_iv": {
                    "mean": round(float(put_iv.mean()), 4)
                    if not put_iv.empty
                    else None,
                    "min": round(float(put_iv.min()), 4)
                    if not put_iv.empty
                    else None,
                    "max": round(float(put_iv.max()), 4)
                    if not put_iv.empty
                    else None,
                },
                "max_pain_strike": max_pain_strike,
                "num_call_strikes": len(calls),
                "num_put_strikes": len(puts),
            }
            return json.dumps(summary, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_unusual_options_activity(
        self,
        symbol: str,
        expiration_date: str = "",
        min_volume: int = 100,
        min_vol_oi_ratio: float = 2.0,
    ) -> str:
        """Find options with unusual activity based on volume and volume/open-interest ratio. Scans all expiration dates if none specified.

        Args:
            symbol (str): Stock symbol in Yahoo Finance format.
            expiration_date (str): Options expiration date in YYYY-MM-DD format. Empty string scans all dates.
            min_volume (int): Minimum volume threshold. Defaults to 100.
            min_vol_oi_ratio (float): Minimum volume to open interest ratio. Defaults to 2.0.
        """
        try:
            symbol = validate_symbol(symbol=symbol)
            stock = Ticker(ticker=symbol, session=self.session)

            if expiration_date:
                validate_date(
                    date_str=expiration_date, param_name="expiration_date"
                )
                dates = [expiration_date]
            else:
                dates = list(stock.options) if stock.options else []

            if not dates:
                return f"Error: No options data found for {symbol}"

            unusual: list[dict] = []
            for date in dates:
                chain = stock.option_chain(date)
                for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
                    if df is None or df.empty:
                        continue
                    df = df.copy()
                    df["volume"] = df["volume"].fillna(0)
                    df["openInterest"] = df["openInterest"].fillna(0)
                    df = df[df["volume"] >= min_volume]
                    if df.empty:
                        continue
                    for _, row in df.iterrows():
                        vol = row["volume"]
                        oi = row["openInterest"]
                        ratio = round(vol / oi, 2) if oi > 0 else 999999.0
                        if ratio < min_vol_oi_ratio:
                            continue
                        unusual.append(
                            {
                                "expiration": date,
                                "type": opt_type,
                                "strike": row["strike"],
                                "lastPrice": row["lastPrice"],
                                "bid": row.get("bid"),
                                "ask": row.get("ask"),
                                "volume": int(vol),
                                "openInterest": int(oi),
                                "vol_oi_ratio": ratio,
                                "impliedVolatility": round(
                                    row["impliedVolatility"], 4
                                )
                                if pd.notna(row["impliedVolatility"])
                                else None,
                                "inTheMoney": bool(row["inTheMoney"]),
                            }
                        )

            unusual.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)
            if not unusual:
                return f"No unusual options activity found for {symbol} with given filters"
            return json.dumps(unusual, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    def get_options_pnl(
        self,
        option_type: Literal["call", "put"],
        action: Literal["buy", "sell"],
        strike: float,
        premium: float,
        contracts: int = 1,
        min_underlying: float = 0,
        max_underlying: float = 0,
        step: float = 0,
    ) -> str:
        """Calculate P&L at expiry for a single-leg option position across a range of underlying prices.

        Args:
            option_type (str): Option type - "call" or "put".
            action (str): Position direction - "buy" or "sell".
            strike (float): Strike price of the option.
            premium (float): Premium paid or received per share.
            contracts (int): Number of contracts (each = 100 shares). Defaults to 1.
            min_underlying (float): Start of underlying price range. 0 = auto (strike * 0.7).
            max_underlying (float): End of underlying price range. 0 = auto (strike * 1.3).
            step (float): Price step between calculations. 0 = auto.
        """
        try:
            if option_type not in ("call", "put"):
                return "Error: option_type must be 'call' or 'put'"
            if action not in ("buy", "sell"):
                return "Error: action must be 'buy' or 'sell'"
            if strike <= 0:
                return "Error: strike must be positive"
            if premium < 0:
                return "Error: premium must be non-negative"
            if contracts < 1:
                return "Error: contracts must be at least 1"

            multiplier = 100 * contracts
            sign = 1 if action == "buy" else -1

            if min_underlying <= 0:
                min_underlying = round(strike * 0.7, 2)
            if max_underlying <= 0:
                max_underlying = round(strike * 1.3, 2)
            if step <= 0:
                step = round((max_underlying - min_underlying) / 20, 2)
                if step <= 0:
                    step = 0.5

            if option_type == "call":
                breakeven = strike + premium
            else:
                breakeven = strike - premium

            pnl_table = []
            price = min_underlying
            while price <= max_underlying + step / 2:
                if option_type == "call":
                    intrinsic = max(0, price - strike)
                else:
                    intrinsic = max(0, strike - price)

                pnl_per_share = sign * (intrinsic - premium)
                pnl_table.append(
                    {
                        "underlying_price": round(price, 2),
                        "pnl": round(pnl_per_share * multiplier, 2),
                        "pnl_per_share": round(pnl_per_share, 2),
                    }
                )
                price += step

            if action == "buy":
                max_loss = round(-premium * multiplier, 2)
                max_profit = (
                    "unlimited"
                    if option_type == "call"
                    else round((strike - premium) * multiplier, 2)
                )
            else:
                max_profit = round(premium * multiplier, 2)
                max_loss = (
                    "unlimited"
                    if option_type == "call"
                    else round(-(strike - premium) * multiplier, 2)
                )

            output = {
                "option_type": option_type,
                "action": action,
                "strike": strike,
                "premium": premium,
                "contracts": contracts,
                "breakeven": round(breakeven, 2),
                "max_profit": max_profit,
                "max_loss": max_loss,
                "pnl_table": pnl_table,
            }
            return json.dumps(output, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"


TOOL_REGISTRY: dict[str, callable] = {}


def register_tools(yf: YahooFinance) -> None:
    TOOL_REGISTRY.update(
        {
            "get_current_stock_price": yf.get_current_stock_price,
            "get_stock_price_by_date": yf.get_stock_price_by_date,
            "get_stock_price_date_range": yf.get_stock_price_date_range,
            "get_historical_stock_prices": yf.get_historical_stock_prices,
            "get_dividends": yf.get_dividends,
            "get_income_statement": yf.get_income_statement,
            "get_cashflow": yf.get_cashflow,
            "get_earning_dates": yf.get_earning_dates,
            "get_news": yf.get_news,
            "get_recommendations": yf.get_recommendations,
            "get_option_expiration_dates": yf.get_option_expiration_dates,
            "get_option_chain": yf.get_option_chain,
            "get_calls": yf.get_calls,
            "get_puts": yf.get_puts,
            "get_options_multi_expiry": yf.get_options_multi_expiry,
            "get_options_summary": yf.get_options_summary,
            "get_unusual_options_activity": yf.get_unusual_options_activity,
            "get_options_pnl": yf.get_options_pnl,
        }
    )


async def serve() -> None:
    server = Server("mcp-yahoo-finance")
    yf = YahooFinance()
    register_tools(yf)

    tools = [generate_tool(method) for method in TOOL_REGISTRY.values()]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def call_tool(name: str, args: dict[str, Any]) -> list[TextContent]:
        if name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {name}")
        result = TOOL_REGISTRY[name](**args)
        return [TextContent(type="text", text=result)]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
