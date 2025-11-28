import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Wallets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_address TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_processed_block INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(wallet_address, user_id)
                )
            """)
            
            # Transactions table (for history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_address TEXT NOT NULL,
                    tx_hash TEXT NOT NULL UNIQUE,
                    tx_type TEXT NOT NULL,
                    from_address TEXT,
                    to_address TEXT,
                    value TEXT,
                    token_address TEXT,
                    token_symbol TEXT,
                    token_name TEXT,
                    token_id TEXT,
                    function_name TEXT,
                    block_number INTEGER,
                    gas_used INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Balance history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_address TEXT NOT NULL,
                    token_address TEXT,
                    balance TEXT NOT NULL,
                    balance_eth REAL,
                    block_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallets_address ON wallets(wallet_address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallets_user ON wallets(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(tx_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_balance_wallet ON balance_history(wallet_address)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def add_user(self, user_id: int, chat_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Add or update user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, chat_id, username, first_name, last_name, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, chat_id, username, first_name, last_name))
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user_chat_id(self, user_id: int) -> Optional[int]:
        """Get chat_id for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chat_id FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return row['chat_id'] if row else None
        except Exception as e:
            logger.error(f"Error getting user chat_id: {e}")
            return None
    
    def add_wallet(self, wallet_address: str, user_id: int, current_block: int = 0) -> bool:
        """Add wallet to tracking list"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO wallets (wallet_address, user_id, last_processed_block, is_active)
                    VALUES (?, ?, ?, 1)
                """, (wallet_address.lower(), user_id, current_block))
                return True
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return False
    
    def remove_wallet(self, wallet_address: str, user_id: int) -> bool:
        """Remove wallet from tracking list"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE wallets 
                    SET is_active = 0 
                    WHERE wallet_address = ? AND user_id = ?
                """, (wallet_address.lower(), user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            return False
    
    def get_user_wallets(self, user_id: int) -> List[Dict]:
        """Get all active wallets for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT wallet_address, added_at, last_processed_block
                    FROM wallets
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY added_at DESC
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting user wallets: {e}")
            return []
    
    def get_all_tracked_wallets(self) -> List[Dict]:
        """Get all active tracked wallets with user info"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT w.wallet_address, w.user_id, w.last_processed_block, u.username, u.chat_id
                    FROM wallets w
                    JOIN users u ON w.user_id = u.user_id
                    WHERE w.is_active = 1
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all wallets: {e}")
            return []
    
    def update_last_processed_block(self, wallet_address: str, block_number: int):
        """Update last processed block for a wallet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE wallets
                    SET last_processed_block = ?
                    WHERE wallet_address = ? AND is_active = 1
                """, (block_number, wallet_address.lower()))
        except Exception as e:
            logger.error(f"Error updating last processed block: {e}")
    
    def get_last_processed_block(self, wallet_address: str) -> int:
        """Get last processed block for a wallet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT last_processed_block
                    FROM wallets
                    WHERE wallet_address = ? AND is_active = 1
                """, (wallet_address.lower(),))
                row = cursor.fetchone()
                return row['last_processed_block'] if row else 0
        except Exception as e:
            logger.error(f"Error getting last processed block: {e}")
            return 0
    
    def save_transaction(self, wallet_address: str, tx_hash: str, tx_type: str, 
                        tx_data: Dict) -> bool:
        """Save transaction to history"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO transactions (
                        wallet_address, tx_hash, tx_type, from_address, to_address,
                        value, token_address, token_symbol, token_name, token_id,
                        function_name, block_number, gas_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wallet_address.lower(),
                    tx_hash,
                    tx_type,
                    tx_data.get('from'),
                    tx_data.get('to'),
                    str(tx_data.get('value', '0')),
                    tx_data.get('token_address'),
                    tx_data.get('token_symbol'),
                    tx_data.get('token_name'),
                    str(tx_data.get('token_id', '')),
                    tx_data.get('block_number'),
                    tx_data.get('gas_used')
                ))
                return True
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            return False
    
    def get_balance(self, wallet_address: str, token_address: Optional[str] = None) -> Optional[str]:
        """Get latest balance for a wallet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if token_address:
                    cursor.execute("""
                        SELECT balance FROM balance_history
                        WHERE wallet_address = ? AND token_address = ?
                        ORDER BY created_at DESC LIMIT 1
                    """, (wallet_address.lower(), token_address.lower()))
                else:
                    cursor.execute("""
                        SELECT balance FROM balance_history
                        WHERE wallet_address = ? AND token_address IS NULL
                        ORDER BY created_at DESC LIMIT 1
                    """, (wallet_address.lower(),))
                row = cursor.fetchone()
                return row['balance'] if row else None
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    def save_balance(self, wallet_address: str, balance: str, balance_eth: float,
                    block_number: int, token_address: Optional[str] = None) -> bool:
        """Save balance snapshot"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO balance_history (
                        wallet_address, token_address, balance, balance_eth, block_number
                    ) VALUES (?, ?, ?, ?, ?)
                """, (wallet_address.lower(), token_address, balance, balance_eth, block_number))
                return True
        except Exception as e:
            logger.error(f"Error saving balance: {e}")
            return False
    
    def get_transaction_count(self, wallet_address: str) -> int:
        """Get total transaction count for a wallet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM transactions
                    WHERE wallet_address = ?
                """, (wallet_address.lower(),))
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting transaction count: {e}")
            return 0

