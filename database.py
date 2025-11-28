import logging
from typing import Dict, List, Optional
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: str):
        if not db_url:
            raise ValueError("DATABASE_URL is required")
        self.db_url = db_url
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            with psycopg.connect(self.db_url, row_factory=dict_row, autocommit=True) as conn:
                yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def init_database(self):
        """Initialize database tables"""
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS wallets (
                id SERIAL PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                added_at TIMESTAMPTZ DEFAULT NOW(),
                last_processed_block BIGINT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE (wallet_address, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
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
                block_number BIGINT,
                gas_used BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS balance_history (
                id SERIAL PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                token_address TEXT,
                balance TEXT NOT NULL,
                balance_eth DOUBLE PRECISION,
                block_number BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_wallets_address ON wallets(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_wallets_user ON wallets(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(tx_hash)",
            "CREATE INDEX IF NOT EXISTS idx_balance_wallet ON balance_history(wallet_address)"
        ]
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in ddl_statements:
                    cursor.execute(statement)
        logger.info("Database initialized successfully")
    
    def add_user(self, user_id: int, chat_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Add or update user"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (user_id, chat_id, username, first_name, last_name, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        chat_id = EXCLUDED.chat_id,
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = NOW()
                """, (user_id, chat_id, username, first_name, last_name))
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def add_wallet(self, wallet_address: str, user_id: int, current_block: int = 0) -> bool:
        """Add wallet to tracking list"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO wallets (wallet_address, user_id, last_processed_block, is_active)
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (wallet_address, user_id)
                    DO UPDATE SET
                        last_processed_block = EXCLUDED.last_processed_block,
                        is_active = TRUE,
                        added_at = NOW()
                """, (wallet_address.lower(), user_id, current_block))
                return True
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return False
    
    def remove_wallet(self, wallet_address: str, user_id: int) -> bool:
        """Remove wallet from tracking list"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallets 
                    SET is_active = FALSE 
                    WHERE wallet_address = %s AND user_id = %s
                """, (wallet_address.lower(), user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            return False
    
    def get_user_wallets(self, user_id: int) -> List[Dict]:
        """Get all active wallets for a user"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    SELECT wallet_address, added_at, last_processed_block
                    FROM wallets
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY added_at DESC
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user wallets: {e}")
            return []
    
    def get_all_tracked_wallets(self) -> List[Dict]:
        """Get all active tracked wallets with user info"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    SELECT w.wallet_address, w.user_id, w.last_processed_block, u.username, u.chat_id
                    FROM wallets w
                    JOIN users u ON w.user_id = u.user_id
                    WHERE w.is_active = TRUE
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all wallets: {e}")
            return []
    
    def update_last_processed_block(self, wallet_address: str, block_number: int):
        """Update last processed block for a wallet"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallets
                    SET last_processed_block = %s
                    WHERE wallet_address = %s AND is_active = TRUE
                """, (block_number, wallet_address.lower()))
        except Exception as e:
            logger.error(f"Error updating last processed block: {e}")
    
    def get_last_processed_block(self, wallet_address: str) -> int:
        """Get last processed block for a wallet"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    SELECT last_processed_block
                    FROM wallets
                    WHERE wallet_address = %s AND is_active = TRUE
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
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transactions (
                        wallet_address, tx_hash, tx_type, from_address, to_address,
                        value, token_address, token_symbol, token_name, token_id,
                        function_name, block_number, gas_used
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tx_hash) DO NOTHING
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
                    tx_data.get('function_name'),
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
            with self.get_connection() as conn, conn.cursor() as cursor:
                if token_address:
                    cursor.execute("""
                        SELECT balance FROM balance_history
                        WHERE wallet_address = %s AND token_address = %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (wallet_address.lower(), token_address.lower()))
                else:
                    cursor.execute("""
                        SELECT balance FROM balance_history
                        WHERE wallet_address = %s AND token_address IS NULL
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
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO balance_history (
                        wallet_address, token_address, balance, balance_eth, block_number
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (wallet_address.lower(), token_address, balance, balance_eth, block_number))
                return True
        except Exception as e:
            logger.error(f"Error saving balance: {e}")
            return False
    
    def get_transaction_count(self, wallet_address: str) -> int:
        """Get total transaction count for a wallet"""
        try:
            with self.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM transactions
                    WHERE wallet_address = %s
                """, (wallet_address.lower(),))
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting transaction count: {e}")
            return 0

