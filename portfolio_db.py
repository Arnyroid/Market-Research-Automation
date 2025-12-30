"""
Portfolio Database Module
Manages SQLite database for portfolio tracking
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from loguru import logger
import pandas as pd
import config


class PortfolioDB:
    """Manages portfolio database operations"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize portfolio database
        
        Args:
            db_path: Path to SQLite database file (default: portfolio.db)
        """
        if db_path is None:
            db_path = config.DATA_DIR / "portfolio.db"
        
        self.db_path = Path(db_path)
        self.conn = None
        
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        
        logger.info(f"Portfolio database initialized: {self.db_path}")
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info("Database connection established")
            return self.conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def create_tables(self):
        """Create all required tables"""
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            # Table 1: Trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE NOT NULL,
                    scrip_code VARCHAR(10) NOT NULL,
                    scrip_name VARCHAR(100),
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    trade_type VARCHAR(4) NOT NULL CHECK(trade_type IN ('BUY', 'SELL')),
                    total_value DECIMAL(15, 2),
                    brokerage DECIMAL(10, 2) DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table 2: Portfolio (Current Holdings)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    scrip_code VARCHAR(10) PRIMARY KEY,
                    scrip_name VARCHAR(100),
                    total_quantity INTEGER NOT NULL DEFAULT 0,
                    avg_buy_price DECIMAL(10, 2) NOT NULL,
                    total_invested DECIMAL(15, 2) NOT NULL,
                    current_price DECIMAL(10, 2),
                    current_value DECIMAL(15, 2),
                    profit_loss DECIMAL(15, 2),
                    profit_loss_percent DECIMAL(10, 2),
                    last_updated TIMESTAMP
                )
            """)
            
            # Table 3: Price History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scrip_code VARCHAR(10) NOT NULL,
                    price_date DATE NOT NULL,
                    open_price DECIMAL(10, 2),
                    high_price DECIMAL(10, 2),
                    low_price DECIMAL(10, 2),
                    close_price DECIMAL(10, 2),
                    volume INTEGER,
                    source VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(scrip_code, price_date)
                )
            """)
            
            # Table 4: Alert Rules
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scrip_code VARCHAR(10) NOT NULL,
                    scrip_name VARCHAR(100),
                    alert_type VARCHAR(20) NOT NULL CHECK(alert_type IN
                        ('PRICE_CHANGE', 'TARGET_PRICE', 'STOP_LOSS')),
                    condition VARCHAR(10) NOT NULL CHECK(condition IN
                        ('ABOVE', 'BELOW', 'CHANGE_UP', 'CHANGE_DOWN')),
                    threshold_value DECIMAL(10, 2) NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP,
                    notes TEXT
                )
            """)
            
            # Table 5: Alert History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_rule_id INTEGER NOT NULL,
                    scrip_code VARCHAR(10) NOT NULL,
                    scrip_name VARCHAR(100),
                    alert_type VARCHAR(20) NOT NULL,
                    trigger_price DECIMAL(10, 2) NOT NULL,
                    threshold_value DECIMAL(10, 2) NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notification_sent BOOLEAN DEFAULT 0,
                    FOREIGN KEY (alert_rule_id) REFERENCES alert_rules(id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_scrip 
                ON trades(scrip_code)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_date 
                ON trades(trade_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_scrip_date
                ON price_history(scrip_code, price_date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_rules_scrip
                ON alert_rules(scrip_code)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_rules_active
                ON alert_rules(is_active)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_history_scrip
                ON alert_history(scrip_code)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_history_triggered
                ON alert_history(triggered_at)
            """)
            
            self.conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            self.close()
    
    def add_trade(self, trade_date: str, scrip_code: str, scrip_name: str,
                  quantity: int, price: float, trade_type: str,
                  brokerage: float = 0, notes: str = "") -> int:
        """
        Add a new trade
        
        Args:
            trade_date: Trade date (YYYY-MM-DD)
            scrip_code: BSE scrip code
            scrip_name: Company name
            quantity: Number of shares
            price: Price per share
            trade_type: 'BUY' or 'SELL'
            brokerage: Brokerage charges
            notes: Additional notes
        
        Returns:
            Trade ID
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            total_value = quantity * price
            
            cursor.execute("""
                INSERT INTO trades 
                (trade_date, scrip_code, scrip_name, quantity, price, 
                 trade_type, total_value, brokerage, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trade_date, scrip_code, scrip_name, quantity, price,
                  trade_type.upper(), total_value, brokerage, notes))
            
            self.conn.commit()
            trade_id = cursor.lastrowid
            
            logger.info(f"Trade added: {trade_type} {quantity} {scrip_code} @ ₹{price}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            raise
        finally:
            self.close()
    
    def get_all_trades(self, scrip_code: Optional[str] = None) -> pd.DataFrame:
        """
        Get all trades or trades for specific scrip
        
        Args:
            scrip_code: Optional scrip code to filter
        
        Returns:
            DataFrame with trade data
        """
        try:
            self.connect()
            
            if scrip_code:
                query = """
                    SELECT * FROM trades 
                    WHERE scrip_code = ?
                    ORDER BY trade_date DESC
                """
                df = pd.read_sql_query(query, self.conn, params=(scrip_code,))
            else:
                query = "SELECT * FROM trades ORDER BY trade_date DESC"
                df = pd.read_sql_query(query, self.conn)
            
            logger.info(f"Retrieved {len(df)} trades")
            return df
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            raise
        finally:
            self.close()
    
    def update_portfolio(self, scrip_code: str, scrip_name: str,
                        total_quantity: int, avg_buy_price: float,
                        total_invested: float):
        """
        Update portfolio holdings
        
        Args:
            scrip_code: BSE scrip code
            scrip_name: Company name
            total_quantity: Total shares held
            avg_buy_price: Average purchase price
            total_invested: Total amount invested
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio 
                (scrip_code, scrip_name, total_quantity, avg_buy_price, 
                 total_invested, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scrip_code, scrip_name, total_quantity, avg_buy_price,
                  total_invested, datetime.now()))
            
            self.conn.commit()
            logger.info(f"Portfolio updated: {scrip_code} - {total_quantity} shares")
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            raise
        finally:
            self.close()
    
    def get_portfolio(self) -> pd.DataFrame:
        """
        Get current portfolio holdings
        
        Returns:
            DataFrame with portfolio data
        """
        try:
            self.connect()
            
            query = """
                SELECT * FROM portfolio 
                WHERE total_quantity > 0
                ORDER BY scrip_code
            """
            df = pd.read_sql_query(query, self.conn)
            
            logger.info(f"Retrieved portfolio: {len(df)} holdings")
            return df
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            raise
        finally:
            self.close()
    
    def update_current_prices(self, price_data: Dict[str, float]):
        """
        Update current prices for portfolio stocks
        
        Args:
            price_data: Dictionary of {scrip_code: current_price}
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            for scrip_code, price in price_data.items():
                # Get portfolio data
                cursor.execute("""
                    SELECT total_quantity, avg_buy_price, total_invested
                    FROM portfolio WHERE scrip_code = ?
                """, (scrip_code,))
                
                row = cursor.fetchone()
                if row:
                    quantity, avg_price, invested = row
                    
                    # Calculate values
                    current_value = quantity * price
                    profit_loss = current_value - invested
                    profit_loss_pct = (profit_loss / invested * 100) if invested > 0 else 0
                    
                    # Update portfolio
                    cursor.execute("""
                        UPDATE portfolio 
                        SET current_price = ?,
                            current_value = ?,
                            profit_loss = ?,
                            profit_loss_percent = ?,
                            last_updated = ?
                        WHERE scrip_code = ?
                    """, (price, current_value, profit_loss, profit_loss_pct,
                          datetime.now(), scrip_code))
            
            self.conn.commit()
            logger.info(f"Updated prices for {len(price_data)} stocks")
            
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
            raise
        finally:
            self.close()
    
    def add_price_history(self, scrip_code: str, price_date: str,
                         open_price: float, high_price: float,
                         low_price: float, close_price: float,
                         volume: int = 0, source: str = "BSE"):
        """
        Add price history record
        
        Args:
            scrip_code: BSE scrip code
            price_date: Date (YYYY-MM-DD)
            open_price: Opening price
            high_price: Day high
            low_price: Day low
            close_price: Closing price
            volume: Trading volume
            source: Data source
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO price_history 
                (scrip_code, price_date, open_price, high_price, 
                 low_price, close_price, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (scrip_code, price_date, open_price, high_price,
                  low_price, close_price, volume, source))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error adding price history: {e}")
            raise
        finally:
            self.close()
    
    def get_price_history(self, scrip_code: str, days: int = 30) -> pd.DataFrame:
        """
        Get price history for a scrip
        
        Args:
            scrip_code: BSE scrip code
            days: Number of days of history
        
        Returns:
            DataFrame with price history
        """
        try:
            self.connect()
            
            query = """
                SELECT * FROM price_history 
                WHERE scrip_code = ?
                ORDER BY price_date DESC
                LIMIT ?
            """
            df = pd.read_sql_query(query, self.conn, params=(scrip_code, days))
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            raise
        finally:
            self.close()
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get portfolio summary statistics
        
        Returns:
            Dictionary with summary data
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            # Get totals
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_stocks,
                    SUM(total_invested) as total_invested,
                    SUM(current_value) as current_value,
                    SUM(profit_loss) as total_profit_loss
                FROM portfolio
                WHERE total_quantity > 0
            """)
            
            row = cursor.fetchone()
            
            summary = {
                'total_stocks': row[0] or 0,
                'total_invested': row[1] or 0,
                'current_value': row[2] or 0,
                'total_profit_loss': row[3] or 0,
                'total_profit_loss_percent': 0
            }
            
            if summary['total_invested'] > 0:
                summary['total_profit_loss_percent'] = (
                    summary['total_profit_loss'] / summary['total_invested'] * 100
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            raise
        finally:
            self.close()


def main():
    """Test function"""
    db = PortfolioDB()
    
    # Create tables
    logger.info("Creating database tables...")
    db.create_tables()
    
    # Add sample trade
    logger.info("Adding sample trade...")
    db.add_trade(
        trade_date="2025-12-27",
        scrip_code="500325",
        scrip_name="Reliance Industries Ltd",
        quantity=10,
        price=1450.00,
        trade_type="BUY",
        brokerage=50.00,
        notes="First purchase"
    )
    
    # Get trades
    logger.info("Retrieving trades...")
    trades = db.get_all_trades()
    print("\nTrades:")
    print(trades)
    
    # Update portfolio
    logger.info("Updating portfolio...")
    db.update_portfolio(
        scrip_code="500325",
        scrip_name="Reliance Industries Ltd",
        total_quantity=10,
        avg_buy_price=1450.00,
        total_invested=14500.00
    )
    
    # Get portfolio
    logger.info("Retrieving portfolio...")
    portfolio = db.get_portfolio()
    print("\nPortfolio:")
    print(portfolio)
    
    logger.info("Database test completed successfully!")


if __name__ == "__main__":
    main()

