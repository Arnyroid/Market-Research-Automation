#!/usr/bin/env python3
"""
Corporate Actions Module
Handle dividends, bonus shares, stock splits, and rights issues
"""

import argparse
import sys
from datetime import datetime
from typing import Optional
from loguru import logger
import pandas as pd
from portfolio_db import PortfolioDB
import config


class CorporateActionsManager:
    """Manage corporate actions for portfolio"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize corporate actions manager
        
        Args:
            db_path: Path to database file
        """
        self.db = PortfolioDB(db_path)
        logger.add(
            config.LOG_FILE,
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
        logger.info("Corporate Actions Manager initialized")
    
    def add_dividend(self, action_date: str, scrip_code: str, scrip_name: str,
                    amount_per_share: float, notes: str = "") -> bool:
        """
        Record dividend received
        
        Args:
            action_date: Dividend payment date (YYYY-MM-DD)
            scrip_code: BSE scrip code
            scrip_name: Company name
            amount_per_share: Dividend amount per share
            notes: Additional notes
        
        Returns:
            bool: Success status
        """
        try:
            # Get current holding quantity
            self.db.connect()
            portfolio = self.db.get_portfolio()
            self.db.close()
            
            if portfolio.empty:
                print(f"❌ No holdings found for {scrip_code}")
                return False
            
            stock = portfolio[portfolio['scrip_code'] == scrip_code]
            if stock.empty:
                print(f"❌ Stock {scrip_code} not found in portfolio")
                return False
            
            quantity = int(stock.iloc[0]['total_quantity'])
            total_dividend = quantity * amount_per_share
            
            # Add to corporate actions table
            self.db.connect()
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                INSERT INTO corporate_actions 
                (action_date, scrip_code, scrip_name, action_type, 
                 quantity, amount, notes)
                VALUES (?, ?, ?, 'DIVIDEND', ?, ?, ?)
            """, (action_date, scrip_code, scrip_name, quantity, 
                  total_dividend, notes))
            
            self.db.conn.commit()
            action_id = cursor.lastrowid
            self.db.close()
            
            # Display success message
            print("\n" + "="*80)
            print("💰 DIVIDEND RECORDED SUCCESSFULLY!")
            print("="*80)
            print(f"📅 Date:              {action_date}")
            print(f"🏢 Company:           {scrip_name} ({scrip_code})")
            print(f"📦 Shares Held:       {quantity}")
            print(f"💵 Per Share:         ₹{amount_per_share:.2f}")
            print(f"💰 Total Dividend:    ₹{total_dividend:,.2f}")
            if notes:
                print(f"📝 Notes:             {notes}")
            print("="*80)
            
            logger.info(f"Dividend recorded: {scrip_code} - ₹{total_dividend:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording dividend: {e}")
            print(f"\n❌ Error recording dividend: {e}")
            return False
    
    def add_bonus(self, action_date: str, scrip_code: str, scrip_name: str,
                  ratio: str, notes: str = "") -> bool:
        """
        Record bonus shares received
        
        Args:
            action_date: Bonus issue date (YYYY-MM-DD)
            scrip_code: BSE scrip code
            scrip_name: Company name
            ratio: Bonus ratio (e.g., "1:2" means 1 bonus for every 2 held)
            notes: Additional notes
        
        Returns:
            bool: Success status
        """
        try:
            # Parse ratio
            if ':' not in ratio:
                print(f"❌ Invalid ratio format: {ratio}")
                print("   Use format like '1:2' (1 bonus for every 2 held)")
                return False
            
            bonus_shares, held_shares = map(int, ratio.split(':'))
            
            # Get current holding quantity
            self.db.connect()
            portfolio = self.db.get_portfolio()
            self.db.close()
            
            if portfolio.empty:
                print(f"❌ No holdings found for {scrip_code}")
                return False
            
            stock = portfolio[portfolio['scrip_code'] == scrip_code]
            if stock.empty:
                print(f"❌ Stock {scrip_code} not found in portfolio")
                return False
            
            current_quantity = int(stock.iloc[0]['total_quantity'])
            avg_price = float(stock.iloc[0]['avg_buy_price'])
            
            # Calculate bonus shares
            bonus_quantity = (current_quantity // held_shares) * bonus_shares
            new_total_quantity = current_quantity + bonus_quantity
            
            # Calculate new average price (cost basis remains same, spread over more shares)
            total_invested = current_quantity * avg_price
            new_avg_price = total_invested / new_total_quantity if new_total_quantity > 0 else avg_price
            
            # Add to corporate actions table
            self.db.connect()
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                INSERT INTO corporate_actions 
                (action_date, scrip_code, scrip_name, action_type, 
                 quantity, ratio, notes)
                VALUES (?, ?, ?, 'BONUS', ?, ?, ?)
            """, (action_date, scrip_code, scrip_name, bonus_quantity, 
                  ratio, notes))
            
            self.db.conn.commit()
            self.db.close()
            
            # Update portfolio with new quantity and average price
            self.db.connect()
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                UPDATE portfolio 
                SET total_quantity = ?,
                    avg_buy_price = ?,
                    total_invested = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE scrip_code = ?
            """, (new_total_quantity, new_avg_price, total_invested, scrip_code))
            
            self.db.conn.commit()
            self.db.close()
            
            # Display success message
            print("\n" + "="*80)
            print("🎁 BONUS SHARES RECORDED SUCCESSFULLY!")
            print("="*80)
            print(f"📅 Date:              {action_date}")
            print(f"🏢 Company:           {scrip_name} ({scrip_code})")
            print(f"📊 Bonus Ratio:       {ratio}")
            print(f"📦 Shares Held:       {current_quantity}")
            print(f"🎁 Bonus Received:    {bonus_quantity} shares")
            print(f"📈 New Total:         {new_total_quantity} shares")
            print(f"💰 Old Avg Price:     ₹{avg_price:.2f}")
            print(f"💰 New Avg Price:     ₹{new_avg_price:.2f}")
            if notes:
                print(f"📝 Notes:             {notes}")
            print("="*80)
            print("\n💡 Portfolio updated with bonus shares!")
            
            logger.info(f"Bonus recorded: {scrip_code} - {bonus_quantity} shares ({ratio})")
            return True
            
        except Exception as e:
            logger.error(f"Error recording bonus: {e}")
            print(f"\n❌ Error recording bonus: {e}")
            return False
    
    def add_stock_split(self, action_date: str, scrip_code: str, scrip_name: str,
                       ratio: str, notes: str = "") -> bool:
        """
        Record stock split
        
        Args:
            action_date: Split date (YYYY-MM-DD)
            scrip_code: BSE scrip code
            scrip_name: Company name
            ratio: Split ratio (e.g., "1:2" means 1 share becomes 2)
            notes: Additional notes
        
        Returns:
            bool: Success status
        """
        try:
            # Parse ratio
            if ':' not in ratio:
                print(f"❌ Invalid ratio format: {ratio}")
                print("   Use format like '1:2' (1 share becomes 2)")
                return False
            
            old_shares, new_shares = map(int, ratio.split(':'))
            multiplier = new_shares / old_shares
            
            # Get current holding
            self.db.connect()
            portfolio = self.db.get_portfolio()
            self.db.close()
            
            if portfolio.empty:
                print(f"❌ No holdings found for {scrip_code}")
                return False
            
            stock = portfolio[portfolio['scrip_code'] == scrip_code]
            if stock.empty:
                print(f"❌ Stock {scrip_code} not found in portfolio")
                return False
            
            current_quantity = int(stock.iloc[0]['total_quantity'])
            avg_price = float(stock.iloc[0]['avg_buy_price'])
            
            # Calculate new values
            new_quantity = int(current_quantity * multiplier)
            new_avg_price = avg_price / multiplier
            
            # Add to corporate actions table
            self.db.connect()
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                INSERT INTO corporate_actions 
                (action_date, scrip_code, scrip_name, action_type, 
                 quantity, ratio, notes)
                VALUES (?, ?, ?, 'SPLIT', ?, ?, ?)
            """, (action_date, scrip_code, scrip_name, new_quantity - current_quantity, 
                  ratio, notes))
            
            self.db.conn.commit()
            self.db.close()
            
            # Update portfolio
            self.db.connect()
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                UPDATE portfolio 
                SET total_quantity = ?,
                    avg_buy_price = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE scrip_code = ?
            """, (new_quantity, new_avg_price, scrip_code))
            
            self.db.conn.commit()
            self.db.close()
            
            # Display success message
            print("\n" + "="*80)
            print("✂️  STOCK SPLIT RECORDED SUCCESSFULLY!")
            print("="*80)
            print(f"📅 Date:              {action_date}")
            print(f"🏢 Company:           {scrip_name} ({scrip_code})")
            print(f"📊 Split Ratio:       {ratio}")
            print(f"📦 Old Quantity:      {current_quantity}")
            print(f"📈 New Quantity:      {new_quantity}")
            print(f"💰 Old Avg Price:     ₹{avg_price:.2f}")
            print(f"💰 New Avg Price:     ₹{new_avg_price:.2f}")
            if notes:
                print(f"📝 Notes:             {notes}")
            print("="*80)
            
            logger.info(f"Stock split recorded: {scrip_code} - {ratio}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording stock split: {e}")
            print(f"\n❌ Error recording stock split: {e}")
            return False
    
    def get_corporate_actions(self, scrip_code: Optional[str] = None, 
                             action_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get corporate actions history
        
        Args:
            scrip_code: Optional scrip code filter
            action_type: Optional action type filter (DIVIDEND, BONUS, SPLIT)
        
        Returns:
            DataFrame with corporate actions
        """
        try:
            self.db.connect()
            
            query = "SELECT * FROM corporate_actions WHERE 1=1"
            params = []
            
            if scrip_code:
                query += " AND scrip_code = ?"
                params.append(scrip_code)
            
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type.upper())
            
            query += " ORDER BY action_date DESC"
            
            if params:
                df = pd.read_sql_query(query, self.db.conn, params=params)
            else:
                df = pd.read_sql_query(query, self.db.conn)
            
            self.db.close()
            
            logger.info(f"Retrieved {len(df)} corporate actions")
            return df
            
        except Exception as e:
            logger.error(f"Error getting corporate actions: {e}")
            return pd.DataFrame()


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Manage corporate actions (dividends, bonus, splits)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record dividend
  python3 corporate_actions.py --dividend --date 2025-03-15 --code 500325 \
    --name "Reliance Industries" --amount 10.50 --notes "Interim dividend"
  
  # Record bonus shares (1:2 ratio = 1 bonus for every 2 held)
  python3 corporate_actions.py --bonus --date 2025-06-01 --code 500325 \
    --name "Reliance Industries" --ratio "1:2" --notes "Bonus issue"
  
  # Record stock split (1:2 ratio = 1 share becomes 2)
  python3 corporate_actions.py --split --date 2025-09-01 --code 500325 \
    --name "Reliance Industries" --ratio "1:2" --notes "Stock split"
  
  # View all corporate actions
  python3 corporate_actions.py --list
  
  # View dividends only
  python3 corporate_actions.py --list --type DIVIDEND
  
  # View actions for specific stock
  python3 corporate_actions.py --list --code 500325
        """
    )
    
    parser.add_argument('--dividend', action='store_true', help='Record dividend')
    parser.add_argument('--bonus', action='store_true', help='Record bonus shares')
    parser.add_argument('--split', action='store_true', help='Record stock split')
    parser.add_argument('--list', action='store_true', help='List corporate actions')
    
    parser.add_argument('--date', '-d', help='Action date (YYYY-MM-DD)')
    parser.add_argument('--code', '-c', help='BSE scrip code')
    parser.add_argument('--name', '-n', help='Company name')
    parser.add_argument('--amount', '-a', type=float, help='Dividend amount per share')
    parser.add_argument('--ratio', '-r', help='Bonus/Split ratio (e.g., 1:2)')
    parser.add_argument('--type', '-t', choices=['DIVIDEND', 'BONUS', 'SPLIT'],
                       help='Filter by action type')
    parser.add_argument('--notes', default='', help='Additional notes')
    
    args = parser.parse_args()
    
    manager = CorporateActionsManager()
    
    if args.dividend:
        if not all([args.date, args.code, args.name, args.amount]):
            print("❌ Error: --date, --code, --name, and --amount are required for dividend")
            sys.exit(1)
        
        success = manager.add_dividend(
            args.date, args.code, args.name, args.amount, args.notes
        )
        sys.exit(0 if success else 1)
    
    elif args.bonus:
        if not all([args.date, args.code, args.name, args.ratio]):
            print("❌ Error: --date, --code, --name, and --ratio are required for bonus")
            sys.exit(1)
        
        success = manager.add_bonus(
            args.date, args.code, args.name, args.ratio, args.notes
        )
        sys.exit(0 if success else 1)
    
    elif args.split:
        if not all([args.date, args.code, args.name, args.ratio]):
            print("❌ Error: --date, --code, --name, and --ratio are required for split")
            sys.exit(1)
        
        success = manager.add_stock_split(
            args.date, args.code, args.name, args.ratio, args.notes
        )
        sys.exit(0 if success else 1)
    
    elif args.list:
        df = manager.get_corporate_actions(args.code, args.type)
        
        if df.empty:
            print("\n📭 No corporate actions found")
        else:
            print(f"\n📋 Corporate Actions ({len(df)}):")
            print("="*100)
            
            for _, action in df.iterrows():
                print(f"\n{action['action_date']} - {action['action_type']}")
                print(f"Company: {action['scrip_name']} ({action['scrip_code']})")
                
                if action['action_type'] == 'DIVIDEND':
                    print(f"Shares: {action['quantity']}")
                    print(f"Total Dividend: ₹{action['amount']:,.2f}")
                elif action['action_type'] in ['BONUS', 'SPLIT']:
                    print(f"Ratio: {action['ratio']}")
                    print(f"Shares: {action['quantity']}")
                
                if action['notes']:
                    print(f"Notes: {action['notes']}")
                print("-"*100)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

