#!/usr/bin/env python3
"""
Alert Manager Module
Manages price alerts, target alerts, and stop-loss alerts with desktop notifications
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger
import pandas as pd
import config

# Desktop notification imports
try:
    if config.PLATFORM == 'darwin':  # macOS
        import subprocess
    elif config.PLATFORM == 'win32':  # Windows
        from win10toast import ToastNotifier
    else:  # Linux
        import subprocess
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("Desktop notifications may not be available on this platform")


class AlertManager:
    """Manages portfolio alerts and notifications"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize alert manager
        
        Args:
            db_path: Path to SQLite database file
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
        
        logger.info(f"Alert Manager initialized: {self.db_path}")
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return self.conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def add_alert_rule(self, scrip_code: str, scrip_name: str, alert_type: str,
                       condition: str, threshold_value: float, notes: str = "") -> int:
        """
        Add a new alert rule
        
        Args:
            scrip_code: BSE scrip code
            scrip_name: Company name
            alert_type: 'PRICE_CHANGE', 'TARGET_PRICE', or 'STOP_LOSS'
            condition: 'ABOVE', 'BELOW', 'CHANGE_UP', or 'CHANGE_DOWN'
            threshold_value: Threshold value (price or percentage)
            notes: Additional notes
        
        Returns:
            Alert rule ID
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO alert_rules 
                (scrip_code, scrip_name, alert_type, condition, threshold_value, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scrip_code, scrip_name, alert_type, condition, threshold_value, notes))
            
            self.conn.commit()
            alert_id = cursor.lastrowid
            
            logger.info(f"Alert rule added: {alert_type} for {scrip_code} @ {threshold_value}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Error adding alert rule: {e}")
            raise
        finally:
            self.close()
    
    def get_active_alerts(self, scrip_code: Optional[str] = None) -> pd.DataFrame:
        """
        Get all active alert rules
        
        Args:
            scrip_code: Optional scrip code to filter
        
        Returns:
            DataFrame with active alerts
        """
        try:
            self.connect()
            
            if scrip_code:
                query = """
                    SELECT * FROM alert_rules 
                    WHERE is_active = 1 AND scrip_code = ?
                    ORDER BY created_at DESC
                """
                df = pd.read_sql_query(query, self.conn, params=[scrip_code])
            else:
                query = """
                    SELECT * FROM alert_rules 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """
                df = pd.read_sql_query(query, self.conn)
            
            logger.info(f"Retrieved {len(df)} active alert rules")
            return df
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return pd.DataFrame()
        finally:
            self.close()
    
    def deactivate_alert(self, alert_id: int):
        """
        Deactivate an alert rule
        
        Args:
            alert_id: Alert rule ID
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                UPDATE alert_rules 
                SET is_active = 0
                WHERE id = ?
            """, (alert_id,))
            
            self.conn.commit()
            logger.info(f"Alert rule {alert_id} deactivated")
            
        except Exception as e:
            logger.error(f"Error deactivating alert: {e}")
            raise
        finally:
            self.close()
    
    def delete_alert(self, alert_id: int):
        """
        Delete an alert rule
        
        Args:
            alert_id: Alert rule ID
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
            
            self.conn.commit()
            logger.info(f"Alert rule {alert_id} deleted")
            
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            raise
        finally:
            self.close()
    
    def check_price_alerts(self, scrip_code: str, current_price: float, 
                          previous_price: Optional[float] = None):
        """
        Check if any alerts should be triggered for a stock
        
        Args:
            scrip_code: BSE scrip code
            current_price: Current stock price
            previous_price: Previous price (for change calculation)
        """
        try:
            # Get active alerts for this scrip
            alerts_df = self.get_active_alerts(scrip_code)
            
            if alerts_df.empty:
                return
            
            for _, alert in alerts_df.iterrows():
                triggered = False
                message = ""
                
                alert_type = alert['alert_type']
                condition = alert['condition']
                threshold = alert['threshold_value']
                scrip_name = alert['scrip_name']
                
                # Check TARGET_PRICE alerts
                if alert_type == 'TARGET_PRICE':
                    if condition == 'ABOVE' and current_price >= threshold:
                        triggered = True
                        message = f"🎯 Target Price Reached!\n{scrip_name} ({scrip_code})\nPrice: ₹{current_price:.2f} (Target: ₹{threshold:.2f})"
                    elif condition == 'BELOW' and current_price <= threshold:
                        triggered = True
                        message = f"🎯 Target Price Reached!\n{scrip_name} ({scrip_code})\nPrice: ₹{current_price:.2f} (Target: ₹{threshold:.2f})"
                
                # Check STOP_LOSS alerts
                elif alert_type == 'STOP_LOSS':
                    if condition == 'BELOW' and current_price <= threshold:
                        triggered = True
                        message = f"🛑 Stop Loss Triggered!\n{scrip_name} ({scrip_code})\nPrice: ₹{current_price:.2f} (Stop Loss: ₹{threshold:.2f})"
                
                # Check PRICE_CHANGE alerts
                elif alert_type == 'PRICE_CHANGE' and previous_price:
                    change_percent = ((current_price - previous_price) / previous_price) * 100
                    
                    if condition == 'CHANGE_UP' and change_percent >= threshold:
                        triggered = True
                        message = f"📈 Price Surge Alert!\n{scrip_name} ({scrip_code})\nUp {change_percent:.2f}% to ₹{current_price:.2f}"
                    elif condition == 'CHANGE_DOWN' and change_percent <= -threshold:
                        triggered = True
                        message = f"📉 Price Drop Alert!\n{scrip_name} ({scrip_code})\nDown {abs(change_percent):.2f}% to ₹{current_price:.2f}"
                
                # Trigger alert if conditions met
                if triggered:
                    self._trigger_alert(
                        alert['id'],
                        scrip_code,
                        scrip_name,
                        alert_type,
                        current_price,
                        threshold,
                        message
                    )
        
        except Exception as e:
            logger.error(f"Error checking price alerts: {e}")
    
    def _trigger_alert(self, alert_rule_id: int, scrip_code: str, scrip_name: str,
                       alert_type: str, trigger_price: float, threshold_value: float,
                       message: str):
        """
        Trigger an alert and send notification
        
        Args:
            alert_rule_id: Alert rule ID
            scrip_code: BSE scrip code
            scrip_name: Company name
            alert_type: Type of alert
            trigger_price: Price that triggered the alert
            threshold_value: Threshold value
            message: Alert message
        """
        try:
            # Log to alert history
            self.connect()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO alert_history 
                (alert_rule_id, scrip_code, scrip_name, alert_type, 
                 trigger_price, threshold_value, message, notification_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (alert_rule_id, scrip_code, scrip_name, alert_type,
                  trigger_price, threshold_value, message))
            
            # Update last triggered time
            cursor.execute("""
                UPDATE alert_rules 
                SET last_triggered = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (alert_rule_id,))
            
            self.conn.commit()
            
            # Send desktop notification
            self._send_desktop_notification("Portfolio Alert", message)
            
            logger.info(f"Alert triggered: {alert_type} for {scrip_code}")
            
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
        finally:
            self.close()
    
    def _send_desktop_notification(self, title: str, message: str):
        """
        Send desktop notification
        
        Args:
            title: Notification title
            message: Notification message
        """
        try:
            if not NOTIFICATIONS_AVAILABLE:
                logger.warning("Desktop notifications not available")
                print(f"\n{'='*60}")
                print(f"🔔 {title}")
                print(f"{'-'*60}")
                print(message)
                print(f"{'='*60}\n")
                return
            
            if config.PLATFORM == 'darwin':  # macOS
                # Use osascript for macOS notifications
                script = f'display notification "{message}" with title "{title}" sound name "default"'
                subprocess.run(['osascript', '-e', script], check=True)
                logger.info("Desktop notification sent (macOS)")
                
            elif config.PLATFORM == 'win32':  # Windows
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10, threaded=True)
                logger.info("Desktop notification sent (Windows)")
                
            else:  # Linux
                subprocess.run(['notify-send', title, message], check=True)
                logger.info("Desktop notification sent (Linux)")
        
        except Exception as e:
            logger.error(f"Error sending desktop notification: {e}")
            # Fallback to console output
            print(f"\n{'='*60}")
            print(f"🔔 {title}")
            print(f"{'-'*60}")
            print(message)
            print(f"{'='*60}\n")
    
    def get_alert_history(self, scrip_code: Optional[str] = None, 
                         days: int = 7) -> pd.DataFrame:
        """
        Get alert history
        
        Args:
            scrip_code: Optional scrip code to filter
            days: Number of days to look back
        
        Returns:
            DataFrame with alert history
        """
        try:
            self.connect()
            
            if scrip_code:
                query = """
                    SELECT * FROM alert_history 
                    WHERE scrip_code = ? 
                    AND triggered_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY triggered_at DESC
                """
                df = pd.read_sql_query(query, self.conn, params=[scrip_code, days])
            else:
                query = """
                    SELECT * FROM alert_history 
                    WHERE triggered_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY triggered_at DESC
                """
                df = pd.read_sql_query(query, self.conn, params=[days])
            
            logger.info(f"Retrieved {len(df)} alert history records")
            return df
            
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return pd.DataFrame()
        finally:
            self.close()


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Manage portfolio alerts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add target price alert
  python alert_manager.py --add --scrip 500325 --name "Reliance" --type TARGET_PRICE --condition ABOVE --value 2500
  
  # Add stop-loss alert
  python alert_manager.py --add --scrip 500325 --name "Reliance" --type STOP_LOSS --condition BELOW --value 2200
  
  # Add price change alert (5% up)
  python alert_manager.py --add --scrip 500325 --name "Reliance" --type PRICE_CHANGE --condition CHANGE_UP --value 5
  
  # List all active alerts
  python alert_manager.py --list
  
  # View alert history
  python alert_manager.py --history
  
  # Deactivate alert
  python alert_manager.py --deactivate --id 1
  
  # Delete alert
  python alert_manager.py --delete --id 1
        """
    )
    
    parser.add_argument('--add', action='store_true', help='Add new alert rule')
    parser.add_argument('--list', action='store_true', help='List active alerts')
    parser.add_argument('--history', action='store_true', help='View alert history')
    parser.add_argument('--deactivate', action='store_true', help='Deactivate alert')
    parser.add_argument('--delete', action='store_true', help='Delete alert')
    
    parser.add_argument('--scrip', help='Scrip code')
    parser.add_argument('--name', help='Company name')
    parser.add_argument('--type', choices=['PRICE_CHANGE', 'TARGET_PRICE', 'STOP_LOSS'],
                       help='Alert type')
    parser.add_argument('--condition', choices=['ABOVE', 'BELOW', 'CHANGE_UP', 'CHANGE_DOWN'],
                       help='Alert condition')
    parser.add_argument('--value', type=float, help='Threshold value')
    parser.add_argument('--id', type=int, help='Alert ID')
    parser.add_argument('--notes', default='', help='Additional notes')
    parser.add_argument('--days', type=int, default=7, help='Days for history (default: 7)')
    
    args = parser.parse_args()
    
    manager = AlertManager()
    
    if args.add:
        if not all([args.scrip, args.name, args.type, args.condition, args.value]):
            print("❌ Error: --scrip, --name, --type, --condition, and --value are required for adding alerts")
            return
        
        alert_id = manager.add_alert_rule(
            args.scrip, args.name, args.type, args.condition, args.value, args.notes
        )
        print(f"\n✅ Alert rule added successfully (ID: {alert_id})")
        print(f"   {args.type}: {args.name} ({args.scrip})")
        print(f"   Condition: {args.condition} {args.value}")
    
    elif args.list:
        df = manager.get_active_alerts()
        if df.empty:
            print("\n📭 No active alerts")
        else:
            print(f"\n📋 Active Alerts ({len(df)}):")
            print("="*80)
            for _, alert in df.iterrows():
                print(f"\nID: {alert['id']}")
                print(f"Stock: {alert['scrip_name']} ({alert['scrip_code']})")
                print(f"Type: {alert['alert_type']}")
                print(f"Condition: {alert['condition']} {alert['threshold_value']}")
                if alert['last_triggered']:
                    print(f"Last Triggered: {alert['last_triggered']}")
                if alert['notes']:
                    print(f"Notes: {alert['notes']}")
    
    elif args.history:
        df = manager.get_alert_history(days=args.days)
        if df.empty:
            print(f"\n📭 No alert history in the last {args.days} days")
        else:
            print(f"\n📜 Alert History (Last {args.days} days):")
            print("="*80)
            for _, alert in df.iterrows():
                print(f"\n{alert['triggered_at']}")
                print(f"Stock: {alert['scrip_name']} ({alert['scrip_code']})")
                print(f"Type: {alert['alert_type']}")
                print(f"Trigger Price: ₹{alert['trigger_price']:.2f}")
                print(f"Message: {alert['message']}")
    
    elif args.deactivate:
        if not args.id:
            print("❌ Error: --id is required for deactivating alerts")
            return
        
        manager.deactivate_alert(args.id)
        print(f"\n✅ Alert {args.id} deactivated")
    
    elif args.delete:
        if not args.id:
            print("❌ Error: --id is required for deleting alerts")
            return
        
        manager.delete_alert(args.id)
        print(f"\n✅ Alert {args.id} deleted")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()


