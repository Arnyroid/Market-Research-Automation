#!/usr/bin/env python3
"""
Quick Trade Entry Tool
Add BUY/SELL trades directly from command line without creating CSV files.
"""

import argparse
import sys
from datetime import datetime
from loguru import logger
from portfolio_db import PortfolioDB


class QuickTradeEntry:
    """Quick command-line trade entry"""
    
    def __init__(self):
        """Initialize trade entry tool"""
        self.db = PortfolioDB()
        logger.info("Quick Trade Entry initialized")
    
    def add_trade(self, trade_date, scrip_code, scrip_name, quantity, price, trade_type):
        """
        Add a single trade directly to database
        
        Args:
            trade_date: Trade date (YYYY-MM-DD)
            scrip_code: BSE scrip code
            scrip_name: Company name
            quantity: Number of shares
            price: Price per share
            trade_type: BUY or SELL
        
        Returns:
            bool: Success status
        """
        try:
            # Validate inputs
            if not self._validate_inputs(trade_date, scrip_code, quantity, price, trade_type):
                return False
            
            # Add trade to database
            self.db.connect()
            self.db.add_trade(
                trade_date=trade_date,
                scrip_code=scrip_code,
                scrip_name=scrip_name,
                quantity=quantity,
                price=price,
                trade_type=trade_type
            )
            self.db.close()
            
            # Calculate total amount
            total = quantity * price
            
            # Display success message
            print("\n" + "="*80)
            print("✅ TRADE ADDED SUCCESSFULLY!")
            print("="*80)
            print(f"📅 Date:        {trade_date}")
            print(f"🏢 Company:     {scrip_name} ({scrip_code})")
            print(f"📊 Type:        {trade_type}")
            print(f"📦 Quantity:    {quantity} shares")
            print(f"💰 Price:       ₹{price:,.2f} per share")
            print(f"💵 Total:       ₹{total:,.2f}")
            print("="*80)
            print("\n💡 Next steps:")
            print("   1. Update prices: python price_updater.py --all")
            print("   2. View portfolio: python portfolio_dashboard.py --all")
            print()
            
            logger.info(f"Trade added: {trade_type} {quantity} {scrip_code} @ ₹{price}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            print(f"\n❌ Error adding trade: {e}")
            return False
    
    def _validate_inputs(self, trade_date, scrip_code, quantity, price, trade_type):
        """Validate input parameters"""
        
        # Validate date format
        try:
            datetime.strptime(trade_date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {trade_date}")
            print("   Use YYYY-MM-DD format (e.g., 2025-01-15)")
            return False
        
        # Validate scrip code
        if not scrip_code.isdigit() or len(scrip_code) != 6:
            print(f"❌ Invalid scrip code: {scrip_code}")
            print("   Must be 6-digit BSE scrip code (e.g., 500325)")
            return False
        
        # Validate quantity
        if quantity <= 0:
            print(f"❌ Invalid quantity: {quantity}")
            print("   Must be positive number")
            return False
        
        # Validate price
        if price <= 0:
            print(f"❌ Invalid price: {price}")
            print("   Must be positive number")
            return False
        
        # Validate trade type
        if trade_type not in ['BUY', 'SELL']:
            print(f"❌ Invalid trade type: {trade_type}")
            print("   Must be BUY or SELL")
            return False
        
        return True
    
    def interactive_mode(self):
        """Interactive mode for adding trades"""
        print("\n" + "="*80)
        print("📝 INTERACTIVE TRADE ENTRY")
        print("="*80)
        print("Enter trade details (or 'q' to quit)\n")
        
        try:
            # Get trade date
            trade_date = input("📅 Trade Date (YYYY-MM-DD) [today]: ").strip()
            if trade_date.lower() == 'q':
                return
            if not trade_date:
                trade_date = datetime.now().strftime('%Y-%m-%d')
            
            # Get scrip code
            scrip_code = input("🔢 Scrip Code (6 digits): ").strip()
            if scrip_code.lower() == 'q':
                return
            
            # Get company name
            scrip_name = input("🏢 Company Name: ").strip()
            if scrip_name.lower() == 'q':
                return
            
            # Get trade type
            trade_type = input("📊 Trade Type (BUY/SELL): ").strip().upper()
            if trade_type.lower() == 'q':
                return
            
            # Get quantity
            quantity_str = input("📦 Quantity: ").strip()
            if quantity_str.lower() == 'q':
                return
            quantity = int(quantity_str)
            
            # Get price
            price_str = input("💰 Price per share: ").strip()
            if price_str.lower() == 'q':
                return
            price = float(price_str)
            
            # Confirm before adding
            total = quantity * price
            print("\n" + "-"*80)
            print("📋 CONFIRM TRADE DETAILS:")
            print("-"*80)
            print(f"Date:     {trade_date}")
            print(f"Company:  {scrip_name} ({scrip_code})")
            print(f"Type:     {trade_type}")
            print(f"Quantity: {quantity} shares")
            print(f"Price:    ₹{price:,.2f} per share")
            print(f"Total:    ₹{total:,.2f}")
            print("-"*80)
            
            confirm = input("\n✅ Add this trade? (y/n): ").strip().lower()
            if confirm == 'y':
                self.add_trade(trade_date, scrip_code, scrip_name, quantity, price, trade_type)
            else:
                print("❌ Trade cancelled")
        
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user")
        except ValueError as e:
            print(f"\n❌ Invalid input: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Quick Trade Entry - Add trades directly from command line',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a BUY trade
  python add_trade.py --date 2025-01-15 --code 500325 --name "Reliance Industries Ltd" --qty 10 --price 1450.00 --type BUY
  
  # Add a SELL trade
  python add_trade.py --date 2025-12-27 --code 500325 --name "Reliance Industries Ltd" --qty 5 --price 1600.00 --type SELL
  
  # Interactive mode
  python add_trade.py --interactive
  
  # Quick BUY (uses today's date)
  python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 10 -p 1450.00
  
  # Quick SELL
  python add_trade.py -c 500325 -n "Reliance Industries Ltd" -q 5 -p 1600.00 -t SELL

Common Scrip Codes:
  500325 - Reliance Industries Ltd
  532540 - TCS Ltd
  500180 - HDFC Bank Ltd
  500112 - State Bank of India
  500209 - Infosys Ltd
  532174 - ICICI Bank Ltd
        """
    )
    
    parser.add_argument('--date', '-d', 
                       help='Trade date (YYYY-MM-DD, default: today)',
                       default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--code', '-c', 
                       help='BSE scrip code (6 digits)')
    parser.add_argument('--name', '-n', 
                       help='Company name')
    parser.add_argument('--quantity', '-q', type=int,
                       help='Number of shares')
    parser.add_argument('--price', '-p', type=float,
                       help='Price per share')
    parser.add_argument('--type', '-t', 
                       help='Trade type (BUY or SELL, default: BUY)',
                       default='BUY',
                       choices=['BUY', 'SELL'])
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode - prompts for all inputs')
    
    args = parser.parse_args()
    
    # Create trade entry instance
    entry = QuickTradeEntry()
    
    # Interactive mode
    if args.interactive:
        entry.interactive_mode()
        return
    
    # Check if all required arguments are provided
    if not all([args.code, args.name, args.quantity, args.price]):
        parser.print_help()
        print("\n❌ Error: Missing required arguments")
        print("   Use --interactive for guided entry or provide all arguments")
        sys.exit(1)
    
    # Add trade
    success = entry.add_trade(
        trade_date=args.date,
        scrip_code=args.code,
        scrip_name=args.name,
        quantity=args.quantity,
        price=args.price,
        trade_type=args.type
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
