"""
Portfolio Manager - handles user portfolio, alerts, trade journal
"""
import json
import os
from datetime import datetime
from pathlib import Path


def get_data_dir():
    """Get platform-appropriate data directory."""
    home = Path.home()
    data_dir = home / ".nexustrade"
    data_dir.mkdir(exist_ok=True)
    return data_dir


class PortfolioManager:
    """Manages portfolio holdings, alerts, and trade journal."""

    def __init__(self):
        self.data_dir = get_data_dir()
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.alerts_file = self.data_dir / "alerts.json"
        self.journal_file = self.data_dir / "journal.json"
        self.watchlist_file = self.data_dir / "watchlist.json"

        self.portfolio = self._load(self.portfolio_file, {"holdings": [], "cash": 10000.0})
        self.alerts = self._load(self.alerts_file, {"alerts": []})
        self.journal = self._load(self.journal_file, {"trades": []})
        self.watchlist = self._load(self.watchlist_file, {"tickers": ["AAPL", "TSLA", "NVDA", "SPY", "MSFT"]})

    def _load(self, path, default):
        try:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save(self, path, data):
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Save error: {e}")

    # ─── Portfolio ──────────────────────────────────────────────────────────────

    def get_holdings(self):
        return self.portfolio.get("holdings", [])

    def get_cash(self):
        return self.portfolio.get("cash", 0)

    def add_holding(self, ticker, shares, avg_cost, date=None):
        holdings = self.get_holdings()
        # Check if exists
        for h in holdings:
            if h["ticker"] == ticker.upper():
                # Average in
                total_shares = h["shares"] + shares
                h["avg_cost"] = (h["avg_cost"] * h["shares"] + avg_cost * shares) / total_shares
                h["shares"] = total_shares
                self._save(self.portfolio_file, self.portfolio)
                return
        holdings.append({
            "ticker": ticker.upper(),
            "shares": shares,
            "avg_cost": avg_cost,
            "date_added": date or datetime.now().isoformat(),
        })
        self.portfolio["holdings"] = holdings
        self._save(self.portfolio_file, self.portfolio)

    def remove_holding(self, ticker, shares=None):
        holdings = self.get_holdings()
        if shares is None:
            holdings = [h for h in holdings if h["ticker"] != ticker.upper()]
        else:
            for h in holdings:
                if h["ticker"] == ticker.upper():
                    h["shares"] -= shares
                    if h["shares"] <= 0:
                        holdings.remove(h)
                    break
        self.portfolio["holdings"] = holdings
        self._save(self.portfolio_file, self.portfolio)

    def update_cash(self, amount):
        self.portfolio["cash"] = amount
        self._save(self.portfolio_file, self.portfolio)

    # ─── Alerts ─────────────────────────────────────────────────────────────────

    def get_alerts(self):
        return self.alerts.get("alerts", [])

    def add_alert(self, ticker, alert_type, value, condition="above"):
        """
        alert_type: 'price', 'rsi', 'volume'
        condition: 'above', 'below'
        """
        self.alerts["alerts"].append({
            "id": datetime.now().timestamp(),
            "ticker": ticker.upper(),
            "type": alert_type,
            "value": value,
            "condition": condition,
            "active": True,
            "created": datetime.now().isoformat(),
        })
        self._save(self.alerts_file, self.alerts)

    def remove_alert(self, alert_id):
        self.alerts["alerts"] = [a for a in self.alerts["alerts"] if a["id"] != alert_id]
        self._save(self.alerts_file, self.alerts)

    def check_alerts(self, price_data: dict) -> list:
        """Check which alerts are triggered. price_data: {ticker: {price, rsi, volume}}"""
        triggered = []
        for alert in self.get_alerts():
            if not alert.get("active"):
                continue
            ticker = alert["ticker"]
            if ticker not in price_data:
                continue
            data = price_data[ticker]
            val = None
            if alert["type"] == "price":
                val = data.get("price")
            elif alert["type"] == "rsi":
                val = data.get("rsi")
            elif alert["type"] == "volume":
                val = data.get("volume")

            if val is None:
                continue
            if alert["condition"] == "above" and val >= alert["value"]:
                triggered.append(alert)
            elif alert["condition"] == "below" and val <= alert["value"]:
                triggered.append(alert)

        return triggered

    # ─── Trade Journal ──────────────────────────────────────────────────────────

    def get_journal_entries(self):
        return self.journal.get("trades", [])

    def add_journal_entry(self, ticker, action, shares, price, notes="", tags=None):
        self.journal["trades"].append({
            "id": datetime.now().timestamp(),
            "date": datetime.now().isoformat(),
            "ticker": ticker.upper(),
            "action": action,  # BUY/SELL
            "shares": shares,
            "price": price,
            "total": shares * price,
            "notes": notes,
            "tags": tags or [],
            "pnl": None,  # filled in on sell
        })
        self._save(self.journal_file, self.journal)

    # ─── Watchlist ──────────────────────────────────────────────────────────────

    def get_watchlist(self):
        return self.watchlist.get("tickers", [])

    def add_to_watchlist(self, ticker):
        tickers = self.get_watchlist()
        if ticker.upper() not in tickers:
            tickers.append(ticker.upper())
            self.watchlist["tickers"] = tickers
            self._save(self.watchlist_file, self.watchlist)

    def remove_from_watchlist(self, ticker):
        tickers = [t for t in self.get_watchlist() if t != ticker.upper()]
        self.watchlist["tickers"] = tickers
        self._save(self.watchlist_file, self.watchlist)

    # ─── Analytics ──────────────────────────────────────────────────────────────

    def get_portfolio_stats(self, holdings_with_prices: list) -> dict:
        """Calculate portfolio statistics."""
        if not holdings_with_prices:
            return {}

        total_value = sum(h.get("total_value", 0) for h in holdings_with_prices)
        total_cost = sum(h.get("total_cost", 0) for h in holdings_with_prices)
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        # Winners / Losers
        winners = [h for h in holdings_with_prices if h.get("pnl", 0) > 0]
        losers = [h for h in holdings_with_prices if h.get("pnl", 0) < 0]

        # Risk metrics (simplified)
        returns = [h.get("pnl_pct", 0) for h in holdings_with_prices]
        avg_return = sum(returns) / len(returns) if returns else 0
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns) if returns else 0
        std_dev = variance ** 0.5

        return {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "cash": self.get_cash(),
            "grand_total": total_value + self.get_cash(),
            "winner_count": len(winners),
            "loser_count": len(losers),
            "win_rate": len(winners) / len(holdings_with_prices) * 100 if holdings_with_prices else 0,
            "portfolio_std": std_dev,
            "best_performer": max(holdings_with_prices, key=lambda x: x.get("pnl_pct", 0))["ticker"] if holdings_with_prices else "N/A",
            "worst_performer": min(holdings_with_prices, key=lambda x: x.get("pnl_pct", 0))["ticker"] if holdings_with_prices else "N/A",
        }


# Global instance
portfolio_manager = PortfolioManager()
