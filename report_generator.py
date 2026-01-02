#!/usr/bin/env python3
"""
Portfolio Report Generator
Generate comprehensive portfolio reports in CSV and PDF formats.
"""

import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger
from portfolio_db import PortfolioDB
from portfolio_analyzer import PortfolioAnalyzer

# PDF generation imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("reportlab not installed. PDF generation will not be available.")


class ReportGenerator:
    """Generate portfolio reports in various formats"""
    
    def __init__(self, output_dir='reports'):
        """
        Initialize report generator
        
        Args:
            output_dir: Directory to save reports
        """
        self.db = PortfolioDB()
        self.analyzer = PortfolioAnalyzer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Report Generator initialized. Output directory: {self.output_dir}")
    
    def generate_csv_report(self, filename=None):
        """
        Generate CSV reports (separate files for summary, holdings, trades)
        
        Args:
            filename: Base filename (default: portfolio_report_YYYYMMDD)
        
        Returns:
            list: Paths to generated reports
        """
        try:
            # Generate base filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_filename = f'portfolio_report_{timestamp}'
            else:
                base_filename = filename.replace('.csv', '')
            
            logger.info(f"Generating CSV reports: {base_filename}")
            
            generated_files = []
            
            # Get data
            performance = self.analyzer.get_portfolio_performance()
            
            self.db.connect()
            portfolio_df = self.db.get_portfolio()
            self.db.close()
            
            self.db.connect()
            trades_df = self.db.get_all_trades()
            self.db.close()
            
            # 1. Summary CSV
            summary_file = self.output_dir / f'{base_filename}_summary.csv'
            summary_data = {
                'Metric': [
                    'Report Generated',
                    'Total Stocks',
                    'Total Invested',
                    'Current Value',
                    'Total P&L',
                    'Total P&L %',
                    'Realized P&L',
                    'Unrealized P&L',
                    'Gainers',
                    'Losers'
                ],
                'Value': [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    performance.get('total_stocks', 0),
                    f"{performance.get('total_invested', 0):.2f}",
                    f"{performance.get('current_value', 0):.2f}",
                    f"{performance.get('total_pnl', 0):.2f}",
                    f"{performance.get('total_pnl_percentage', 0):.2f}",
                    f"{performance.get('realized_pnl', 0):.2f}",
                    f"{performance.get('unrealized_pnl', 0):.2f}",
                    performance.get('gainers', 0),
                    performance.get('losers', 0)
                ]
            }
            pd.DataFrame(summary_data).to_csv(summary_file, index=False)
            generated_files.append(str(summary_file))
            logger.info(f"Summary CSV generated: {summary_file}")
            
            # 2. Holdings CSV
            if not portfolio_df.empty:
                holdings_file = self.output_dir / f'{base_filename}_holdings.csv'
                holdings_df = portfolio_df[['scrip_code', 'scrip_name', 'total_quantity', 
                                           'avg_buy_price', 'total_invested', 'current_price', 
                                           'current_value', 'profit_loss', 'profit_loss_percent']].copy()
                holdings_df.columns = ['Scrip Code', 'Company Name', 'Quantity', 'Avg Price',
                                      'Total Invested', 'Current Price', 'Current Value',
                                      'P&L', 'P&L %']
                holdings_df.to_csv(holdings_file, index=False)
                generated_files.append(str(holdings_file))
                logger.info(f"Holdings CSV generated: {holdings_file}")
            
            # 3. Trades CSV
            if not trades_df.empty:
                trades_file = self.output_dir / f'{base_filename}_trades.csv'
                trades_df_export = trades_df[['trade_date', 'scrip_code', 'scrip_name', 
                                             'trade_type', 'quantity', 'price']].copy()
                trades_df_export.columns = ['Date', 'Scrip Code', 'Company Name', 
                                           'Type', 'Quantity', 'Price']
                trades_df_export = trades_df_export.sort_values('Date', ascending=False)
                trades_df_export.to_csv(trades_file, index=False)
                generated_files.append(str(trades_file))
                logger.info(f"Trades CSV generated: {trades_file}")
            
            logger.info(f"CSV reports generated successfully: {len(generated_files)} files")
            return generated_files
            
        except Exception as e:
            logger.error(f"Error generating CSV reports: {e}")
            raise
    
    def generate_pdf_report(self, filename=None):
        """
        Generate comprehensive PDF report
        
        Args:
            filename: Output filename (default: portfolio_report_YYYYMMDD.pdf)
        
        Returns:
            str: Path to generated report
        """
        if not PDF_AVAILABLE:
            raise ImportError("reportlab is not installed. Install it with: pip install reportlab")
        
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'portfolio_report_{timestamp}.pdf'
            
            filepath = self.output_dir / filename
            
            logger.info(f"Generating PDF report: {filepath}")
            
            # Create PDF document
            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
            
            # Container for PDF elements
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=12,
                spaceBefore=12
            )
            
            # Title
            elements.append(Paragraph("Portfolio Report", title_style))
            elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                    styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Get data
            performance = self.analyzer.get_portfolio_performance()
            
            self.db.connect()
            portfolio_df = self.db.get_portfolio()
            self.db.close()
            
            self.db.connect()
            trades_df = self.db.get_all_trades()
            self.db.close()
            
            # Section 1: Portfolio Summary
            elements.append(Paragraph("Portfolio Summary", heading_style))
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Stocks', str(performance.get('total_stocks', 0))],
                ['Total Invested', f"₹{performance.get('total_invested', 0):,.2f}"],
                ['Current Value', f"₹{performance.get('current_value', 0):,.2f}"],
                ['Total P&L', f"₹{performance.get('total_pnl', 0):,.2f}"],
                ['Total P&L %', f"{performance.get('total_pnl_percentage', 0):.2f}%"],
                ['Realized P&L', f"₹{performance.get('realized_pnl', 0):,.2f}"],
                ['Unrealized P&L', f"₹{performance.get('unrealized_pnl', 0):,.2f}"],
                ['Gainers', str(performance.get('gainers', 0))],
                ['Losers', str(performance.get('losers', 0))]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Section 2: Current Holdings
            if not portfolio_df.empty:
                elements.append(Paragraph("Current Holdings", heading_style))
                
                holdings_data = [['Code', 'Company', 'Qty', 'Avg Price', 'Current', 'P&L', 'P&L %']]
                
                for _, row in portfolio_df.iterrows():
                    holdings_data.append([
                        str(row['scrip_code']),
                        str(row['scrip_name'])[:20],  # Truncate long names
                        str(int(row['total_quantity'])),
                        f"₹{row['avg_buy_price']:,.0f}",
                        f"₹{row['current_price']:,.0f}" if pd.notna(row['current_price']) else 'N/A',
                        f"₹{row['profit_loss']:,.0f}" if pd.notna(row['profit_loss']) else 'N/A',
                        f"{row['profit_loss_percent']:.1f}%" if pd.notna(row['profit_loss_percent']) else 'N/A'
                    ])
                
                holdings_table = Table(holdings_data, colWidths=[0.7*inch, 1.8*inch, 0.5*inch, 
                                                                 0.9*inch, 0.9*inch, 0.9*inch, 0.7*inch])
                holdings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(holdings_table)
                elements.append(Spacer(1, 0.3*inch))
            
            # Section 3: Recent Trades (last 10)
            if not trades_df.empty:
                elements.append(Paragraph("Recent Trades (Last 10)", heading_style))
                
                trades_data = [['Date', 'Code', 'Company', 'Type', 'Qty', 'Price']]
                
                recent_trades = trades_df.sort_values('trade_date', ascending=False).head(10)
                for _, row in recent_trades.iterrows():
                    trades_data.append([
                        str(row['trade_date']),
                        str(row['scrip_code']),
                        str(row['scrip_name'])[:20],
                        str(row['trade_type']),
                        str(int(row['quantity'])),
                        f"₹{row['price']:,.0f}"
                    ])
                
                trades_table = Table(trades_data, colWidths=[0.9*inch, 0.7*inch, 1.8*inch, 
                                                             0.6*inch, 0.5*inch, 0.9*inch])
                trades_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(trades_table)
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated successfully: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate portfolio reports in CSV or PDF format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate CSV reports
  python report_generator.py --csv
  
  # Generate PDF report
  python report_generator.py --pdf
  
  # Generate with custom filename
  python report_generator.py --csv --output my_portfolio
  python report_generator.py --pdf --output my_portfolio.pdf
  
  # Generate both formats
  python report_generator.py --csv --pdf
  
  # Custom output directory
  python report_generator.py --csv --dir monthly_reports
        """
    )
    
    parser.add_argument('--csv', '-c', action='store_true',
                       help='Generate CSV reports (summary, holdings, trades)')
    parser.add_argument('--pdf', '-p', action='store_true',
                       help='Generate PDF report')
    parser.add_argument('--output', '-o',
                       help='Output filename (base name for CSV, full name for PDF)')
    parser.add_argument('--dir', '-d', default='reports',
                       help='Output directory (default: reports)')
    
    args = parser.parse_args()
    
    # Create report generator
    generator = ReportGenerator(output_dir=args.dir)
    
    # Generate reports
    if args.csv:
        files = generator.generate_csv_report(filename=args.output)
        print(f"\n✅ CSV reports generated:")
        for file in files:
            print(f"   - {file}")
    
    if args.pdf:
        if not PDF_AVAILABLE:
            print("\n❌ Error: reportlab is not installed")
            print("   Install it with: pip install reportlab")
            return
        
        filepath = generator.generate_pdf_report(filename=args.output)
        print(f"\n✅ PDF report generated: {filepath}")
    
    if not args.csv and not args.pdf:
        # Default: generate CSV reports
        files = generator.generate_csv_report(filename=args.output)
        print(f"\n✅ CSV reports generated:")
        for file in files:
            print(f"   - {file}")
    
    print(f"\n📁 Reports saved in: {generator.output_dir}")
    print("\n💡 Tip: CSV files can be opened in Excel, Google Sheets, or any spreadsheet software")
    if args.pdf or (not args.csv and not args.pdf):
        print("💡 Tip: PDF report provides a professional, shareable format")


if __name__ == '__main__':
    main()
