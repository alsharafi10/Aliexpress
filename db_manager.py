import sqlite3
import json
import os
import shutil
from datetime import datetime
import pandas as pd

DB_FILE = "data.db"
LEGACY_JSON = "transactions.json"
BACKUP_DIR = "backups"
MAX_BACKUPS = 30

class DatabaseManager:
    def __init__(self):
        self.init_db()
        self.auto_backup()
        self.migrate_from_json()

    def get_connection(self):
        return sqlite3.connect(DB_FILE)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    date TEXT,
                    buyer TEXT,
                    order_id TEXT,
                    product_id TEXT,
                    gross REAL,
                    funding_percent REAL,
                    funding REAL,
                    cogs_usd REAL,
                    shipping_usd REAL,
                    packaging_usd REAL,
                    tax_usd REAL,
                    total_costs_usd REAL,
                    commission_cny REAL,
                    service_cny REAL,
                    affiliate_cny REAL,
                    total_fees_cny REAL,
                    commission_usd REAL,
                    service_usd REAL,
                    affiliate_usd REAL,
                    total_fees_usd REAL,
                    payout REAL,
                    net_profit REAL,
                    profit_margin REAL,
                    comm_percent REAL,
                    serv_percent REAL,
                    aff_percent REAL
                )
            ''')
            conn.commit()

    def auto_backup(self):
        if not os.path.exists(DB_FILE):
            return
            
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            
        # Create a backup for today
        today_str = datetime.now().strftime("%Y%m%d")
        backup_path = os.path.join(BACKUP_DIR, f"data_{today_str}.db")
        
        # Only backup once per day roughly (or overwrite if multiple times today)
        try:
            shutil.copy2(DB_FILE, backup_path)
            self._cleanup_old_backups()
        except Exception as e:
            print(f"Error creating backup: {e}")

    def _cleanup_old_backups(self):
        try:
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("data_") and f.endswith(".db")]
            if len(backups) > MAX_BACKUPS:
                # Sort by filename (which includes date), delete oldest
                backups.sort()
                for old_file in backups[:-MAX_BACKUPS]:
                    os.remove(os.path.join(BACKUP_DIR, old_file))
        except Exception as e:
            print(f"Error cleaning backups: {e}")

    def migrate_from_json(self):
        """Migrate existing data from transactions.json if DB is empty."""
        if not os.path.exists(LEGACY_JSON):
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("Migrating legacy JSON data to SQLite...")
                try:
                    with open(LEGACY_JSON, 'r', encoding='utf-8') as f:
                        transactions = json.load(f)
                        
                    for t in transactions:
                        self.insert_transaction(t)
                        
                    print(f"Successfully migrated {len(transactions)} records.")
                    
                    # Rename legacy file to indicate it's been migrated
                    migrated_name = f"{LEGACY_JSON}.migrated"
                    if not os.path.exists(migrated_name):
                        os.rename(LEGACY_JSON, migrated_name)
                        
                except Exception as e:
                    print(f"Migration error: {e}")

    def insert_transaction(self, t):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (
                    username, date, buyer, order_id, product_id,
                    gross, funding_percent, funding,
                    cogs_usd, shipping_usd, packaging_usd, tax_usd, total_costs_usd,
                    commission_cny, service_cny, affiliate_cny, total_fees_cny,
                    commission_usd, service_usd, affiliate_usd, total_fees_usd,
                    payout, net_profit, profit_margin,
                    comm_percent, serv_percent, aff_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                t.get('username', 'admin'),
                t.get('date', ''),
                t.get('buyer', ''),
                t.get('order_id', ''),
                t.get('product_id', ''),
                t.get('gross', 0.0),
                t.get('funding_percent', 0.0),
                t.get('funding', 0.0),
                t.get('cogs_usd', 0.0),
                t.get('shipping_usd', 0.0),
                t.get('packaging_usd', 0.0),
                t.get('tax_usd', 0.0),
                t.get('total_costs_usd', 0.0),
                t.get('commission_cny', 0.0),
                t.get('service_cny', 0.0),
                t.get('affiliate_cny', 0.0),
                t.get('total_fees_cny', 0.0),
                t.get('commission_usd', 0.0),
                t.get('service_usd', 0.0),
                t.get('affiliate_usd', 0.0),
                t.get('total_fees_usd', 0.0),
                t.get('payout', 0.0),
                t.get('net_profit', 0.0),
                t.get('profit_margin', 0.0),
                t.get('comm_percent', 0.0),
                t.get('serv_percent', 0.0),
                t.get('aff_percent', 0.0)
            ))
            conn.commit()

    def update_transaction(self, t, trans_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE transactions SET
                    username=?, date=?, buyer=?, order_id=?, product_id=?,
                    gross=?, funding_percent=?, funding=?,
                    cogs_usd=?, shipping_usd=?, packaging_usd=?, tax_usd=?, total_costs_usd=?,
                    commission_cny=?, service_cny=?, affiliate_cny=?, total_fees_cny=?,
                    commission_usd=?, service_usd=?, affiliate_usd=?, total_fees_usd=?,
                    payout=?, net_profit=?, profit_margin=?,
                    comm_percent=?, serv_percent=?, aff_percent=?
                WHERE id=?
            ''', (
                t.get('username', 'admin'),
                t.get('date', ''),
                t.get('buyer', ''),
                t.get('order_id', ''),
                t.get('product_id', ''),
                t.get('gross', 0.0),
                t.get('funding_percent', 0.0),
                t.get('funding', 0.0),
                t.get('cogs_usd', 0.0),
                t.get('shipping_usd', 0.0),
                t.get('packaging_usd', 0.0),
                t.get('tax_usd', 0.0),
                t.get('total_costs_usd', 0.0),
                t.get('commission_cny', 0.0),
                t.get('service_cny', 0.0),
                t.get('affiliate_cny', 0.0),
                t.get('total_fees_cny', 0.0),
                t.get('commission_usd', 0.0),
                t.get('service_usd', 0.0),
                t.get('affiliate_usd', 0.0),
                t.get('total_fees_usd', 0.0),
                t.get('payout', 0.0),
                t.get('net_profit', 0.0),
                t.get('profit_margin', 0.0),
                t.get('comm_percent', 0.0),
                t.get('serv_percent', 0.0),
                t.get('aff_percent', 0.0),
                trans_id
            ))
            conn.commit()

    def get_all_transactions(self, username_filter=None):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if username_filter:
                cursor.execute("SELECT * FROM transactions WHERE username = ?", (username_filter,))
            else:
                cursor.execute("SELECT * FROM transactions")
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_transaction(self, t):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Attempt to delete by matching identifying fields since we might not have ID from UI
            cursor.execute('''
                DELETE FROM transactions 
                WHERE date = ? AND buyer = ? AND order_id = ? AND CAST(gross AS TEXT) = ?
            ''', (
                t.get('date', ''),
                t.get('buyer', ''),
                t.get('order_id', ''),
                str(t.get('gross', 0.0))
            ))
            conn.commit()

    def get_low_profit_transactions(self, margin_threshold=10.0):
        """Returns transactions with margin strictly less than the threshold (default 10%)"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE profit_margin < ? ORDER BY profit_margin ASC", (margin_threshold,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_dataframe(self):
        """Returns a Pandas DataFrame of all transactions for Analytics Engine"""
        with self.get_connection() as conn:
            query = "SELECT * FROM transactions"
            df = pd.read_sql_query(query, conn)
            return df
