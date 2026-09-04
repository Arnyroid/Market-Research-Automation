"""
Trade Importer Module
Import trades from Excel/CSV files into portfolio database
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
import config
from portfolio_db import PortfolioDB


class TradeImporter:
    """Import trades from Excel/CSV files"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize trade importer
        
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
        logger.info("Trade Importer initialized")
    
    def import_from_excel(self, file_path: str, sheet_name: str = 0) -> int:
        """
        Import trades from Excel file
        
        Expected columns:
        - trade_date or date: Trade date (YYYY-MM-DD or DD-MM-YYYY)
        - scrip_code or script: BSE scrip code
        - scrip_name or name or company: Company name
        - quantity or qty: Number of shares
        - price or rate: Price per share
        - trade_type or type or action: 'BUY' or 'SELL'
        - brokerage (optional): Brokerage charges
        - notes (optional): Additional notes
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: 0)
        
        Returns:
            Number of trades imported
        """
        try:
            logger.info(f"Reading Excel file: {file_path}")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            return self._import_dataframe(df, source="Excel")
            
        except Exception as e:
            logger.error(f"Error importing from Excel: {e}")
            raise
    
    def import_from_csv(self, file_path: str) -> int:
        """
        Import trades from CSV file
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Number of trades imported
        """
        try:
            logger.info(f"Reading CSV file: {file_path}")
            df = pd.read_csv(file_path)
            
            return self._import_dataframe(df, source="CSV")
            
        except Exception as e:
            logger.error(f"Error importing from CSV: {e}")
            raise
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to standard format
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with normalized columns
        """
        # Column mapping (various possible names -> standard name)
        column_mapping = {
            # Date columns
            'date': 'trade_date',
            'trade date': 'trade_date',
            'transaction date': 'trade_date',
            
            # Scrip code columns
            'script': 'scrip_code',
            'scrip': 'scrip_code',
            'stock code': 'scrip_code',
            'symbol': 'scrip_code',
            'code': 'scrip_code',
            
            # Company name columns
            'name': 'scrip_name',
            'company': 'scrip_name',
            'company name': 'scrip_name',
            'stock name': 'scrip_name',
            
            # Quantity columns
            'qty': 'quantity',
            'shares': 'quantity',
            'no of shares': 'quantity',
            
            # Price columns
            'rate': 'price',
            'buy price': 'price',
            'sell price': 'price',
            'avg price': 'price',
            'average price': 'price',
            
            # Trade type columns
            'type': 'trade_type',
            'action': 'trade_type',
            'transaction type': 'trade_type',
            'buy/sell': 'trade_type',
        }
        
        # Convert column names to lowercase for matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        logger.info(f"Normalized columns: {df.columns.tolist()}")
        return df
    
    def _validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required columns
        
        Args:
            df: DataFrame to validate
        
        Returns:
            True if valid, raises exception otherwise
        """
        required_columns = ['trade_date', 'scrip_code', 'quantity', 'price', 'trade_type']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"Missing required columns: {missing_columns}"
            logger.error(error_msg)
            logger.info(f"Available columns: {df.columns.tolist()}")
            raise ValueError(error_msg)
        
        logger.info("DataFrame validation passed")
        return True
    
    def _parse_date(self, date_value) -> str:
        """
        Parse date to YYYY-MM-DD format
        
        Args:
            date_value: Date in various formats
        
        Returns:
            Date string in YYYY-MM-DD format
        """
        try:
            # If already datetime
            if isinstance(date_value, pd.Timestamp):
                return date_value.strftime('%Y-%m-%d')
            
            # Try parsing string
            if isinstance(date_value, str):
                # Try common formats
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                    try:
                        dt = datetime.strptime(date_value, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            
            # If all else fails, use pandas
            return pd.to_datetime(date_value).strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_value}': {e}")
            raise
    
    def _import_dataframe(self, df: pd.DataFrame, source: str = "Unknown") -> int:
        """
        Import trades from DataFrame
        
        Args:
            df: DataFrame with trade data
            source: Source description
        
        Returns:
            Number of trades imported
        """
        try:
            logger.info(f"Importing {len(df)} trades from {source}")
            
            # Normalize columns
            df = self._normalize_columns(df)
            
            # Validate
            self._validate_dataframe(df)
            
            # Add optional columns if missing
            if 'scrip_name' not in df.columns:
                df['scrip_name'] = ''
            if 'brokerage' not in df.columns:
                df['brokerage'] = 0
            if 'notes' not in df.columns:
                df['notes'] = ''
            
            # Import each trade
            imported_count = 0
            failed_count = 0
            
            for idx, row in df.iterrows():
                try:
                    # Parse date
                    trade_date = self._parse_date(row['trade_date'])
                    
                    # Normalize trade type
                    trade_type = str(row['trade_type']).upper().strip()
                    if trade_type not in ['BUY', 'SELL']:
                        # Try to infer
                        if trade_type in ['B', 'BOUGHT', 'PURCHASE']:
                            trade_type = 'BUY'
                        elif trade_type in ['S', 'SOLD', 'SALE']:
                            trade_type = 'SELL'
                        else:
                            logger.warning(f"Row {idx}: Invalid trade type '{trade_type}', skipping")
                            failed_count += 1
                            continue
                    
                    # Add trade to database
                    self.db.add_trade(
                        trade_date=trade_date,
                        scrip_code=str(row['scrip_code']).strip(),
                        scrip_name=str(row.get('scrip_name', '')).strip(),
                        quantity=int(row['quantity']),
                        price=float(row['price']),
                        trade_type=trade_type,
                        brokerage=float(row.get('brokerage', 0)),
                        notes=str(row.get('notes', '')).strip()
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing row {idx}: {e}")
                    logger.error(f"Row data: {row.to_dict()}")
                    failed_count += 1
                    continue
            
            logger.info(f"Import complete: {imported_count} successful, {failed_count} failed")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error in _import_dataframe: {e}")
            raise
    
    def create_sample_template(self, output_path: str = "trade_template.xlsx"):
        """
        Create a sample Excel template for trade import
        
        Args:
            output_path: Path for output file
        """
        try:
            # Sample data
            sample_data = {
                'trade_date': ['2025-01-15', '2025-01-20', '2025-02-10'],
                'scrip_code': ['500325', '532540', '500180'],
                'scrip_name': ['Reliance Industries Ltd', 'TCS Ltd', 'HDFC Bank Ltd'],
                'quantity': [10, 5, 20],
                'price': [1450.00, 3320.00, 997.00],
                'trade_type': ['BUY', 'BUY', 'BUY'],
                'brokerage': [50.00, 30.00, 40.00],
                'notes': ['First purchase', 'IT sector', 'Banking sector']
            }
            
            df = pd.DataFrame(sample_data)
            df.to_excel(output_path, index=False)
            
            logger.info(f"Sample template created: {output_path}")
            print(f"\n✅ Sample template created: {output_path}")
            print("\nTemplate columns:")
            print("  - trade_date: Date in YYYY-MM-DD format")
            print("  - scrip_code: BSE scrip code")
            print("  - scrip_name: Company name (optional)")
            print("  - quantity: Number of shares")
            print("  - price: Price per share")
            print("  - trade_type: BUY or SELL")
            print("  - brokerage: Brokerage charges (optional)")
            print("  - notes: Additional notes (optional)")
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise


def main():
    """Main function for command-line usage"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Import trades from Excel/CSV')
    parser.add_argument('--file', '-f', help='Path to Excel/CSV file')
    parser.add_argument('--sheet', '-s', default=0, help='Sheet name or index (for Excel)')
    parser.add_argument('--template', '-t', action='store_true', help='Create sample template')
    parser.add_argument('--template-path', default='trade_template.xlsx', help='Template output path')
    
    args = parser.parse_args()
    
    importer = TradeImporter()
    
    if args.template:
        # Create template
        importer.create_sample_template(args.template_path)
    elif args.file:
        # Import file
        file_path = Path(args.file)
        
        if not file_path.exists():
            print(f"❌ Error: File not found: {file_path}")
            sys.exit(1)
        
        try:
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                count = importer.import_from_excel(str(file_path), args.sheet)
            elif file_path.suffix.lower() == '.csv':
                count = importer.import_from_csv(str(file_path))
            else:
                print(f"❌ Error: Unsupported file format: {file_path.suffix}")
                sys.exit(1)
            
            print(f"\n✅ Successfully imported {count} trades!")
            print(f"📊 Database: {importer.db.db_path}")
            
        except Exception as e:
            print(f"\n❌ Error importing trades: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
