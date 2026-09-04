#!/usr/bin/env python3
"""
Database Reset Utility
Clear all data from the portfolio database for a fresh start
"""

import sqlite3
from pathlib import Path
from loguru import logger
import config


def reset_database(confirm: bool = False):
    """
    Reset the portfolio database by clearing all data
    
    Args:
        confirm: Must be True to proceed with reset
    """
    db_path = config.DATA_DIR / "portfolio.db"
    
    if not confirm:
        print("\n⚠️  WARNING: This will delete ALL data from the database!")
        print("   - All trades")
        print("   - Portfolio holdings")
        print("   - Price history")
        print("   - Alert rules")
        print("   - Alert history")
        print("\nThis action CANNOT be undone!")
        
        response = input("\nType 'YES' to confirm: ")
        if response != 'YES':
            print("\n❌ Reset cancelled")
            return False
    
    try:
        print(f"\n🔄 Resetting database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear all tables
        tables = ['trades', 'portfolio', 'price_history', 'alert_rules', 'alert_history', 'corporate_actions']
        
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
                count = cursor.rowcount
                print(f"   ✓ Cleared {table}: {count} rows deleted")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️  Table {table} not found or already empty")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence")
        print(f"   ✓ Reset auto-increment counters")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database reset complete! You now have a clean slate.")
        print("\n💡 Next steps:")
        print("   1. Import your trades: python3 trade_importer.py --file your_trades.xlsx")
        print("   2. Update prices: python3 price_updater.py --all")
        print("   3. Set up alerts: python3 alert_manager.py --add ...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error resetting database: {e}")
        logger.error(f"Database reset error: {e}")
        return False


def reset_specific_table(table_name: str, confirm: bool = False):
    """
    Reset a specific table only
    
    Args:
        table_name: Name of table to reset
        confirm: Must be True to proceed
    """
    db_path = config.DATA_DIR / "portfolio.db"
    
    valid_tables = ['trades', 'portfolio', 'price_history', 'alert_rules', 'alert_history', 'corporate_actions']
    
    if table_name not in valid_tables:
        print(f"\n❌ Invalid table name: {table_name}")
        print(f"   Valid tables: {', '.join(valid_tables)}")
        return False
    
    if not confirm:
        print(f"\n⚠️  WARNING: This will delete ALL data from the '{table_name}' table!")
        print("\nThis action CANNOT be undone!")
        
        response = input("\nType 'YES' to confirm: ")
        if response != 'YES':
            print("\n❌ Reset cancelled")
            return False
    
    try:
        print(f"\n🔄 Resetting table: {table_name}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"DELETE FROM {table_name}")
        count = cursor.rowcount
        print(f"   ✓ Cleared {table_name}: {count} rows deleted")
        
        # Reset auto-increment for this table
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Table '{table_name}' reset complete!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error resetting table: {e}")
        logger.error(f"Table reset error: {e}")
        return False


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reset portfolio database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset entire database (interactive confirmation)
  python3 reset_database.py --all
  
  # Reset entire database (skip confirmation - USE WITH CAUTION!)
  python3 reset_database.py --all --force
  
  # Reset specific table only
  python3 reset_database.py --table trades
  python3 reset_database.py --table portfolio
  python3 reset_database.py --table price_history
  python3 reset_database.py --table alert_rules
  python3 reset_database.py --table alert_history
  
  # Reset specific table without confirmation
  python3 reset_database.py --table trades --force

⚠️  WARNING: These operations are IRREVERSIBLE!
   Always backup your database before resetting.
   
Backup command:
  cp data/portfolio.db data/portfolio_backup_$(date +%Y%m%d_%H%M%S).db
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Reset entire database (all tables)')
    parser.add_argument('--table', choices=['trades', 'portfolio', 'price_history', 
                                           'alert_rules', 'alert_history'],
                       help='Reset specific table only')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt (USE WITH CAUTION!)')
    
    args = parser.parse_args()
    
    if args.all:
        reset_database(confirm=args.force)
    elif args.table:
        reset_specific_table(args.table, confirm=args.force)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

