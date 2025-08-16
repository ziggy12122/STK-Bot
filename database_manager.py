
import sqlite3
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class ShopDatabase:
    def __init__(self, db_path: str = "shop.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Products table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price REAL NOT NULL,
                        stock INTEGER DEFAULT 0,
                        image_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Cart table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cart (
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER DEFAULT 1,
                        PRIMARY KEY (user_id, product_id),
                        FOREIGN KEY (product_id) REFERENCES products (id)
                    )
                ''')
                
                # Orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        total_amount REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def get_all_products(self) -> List[Tuple]:
        """Get all products from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
    
    def add_product(self, name: str, description: str, price: float, stock: int = 0, image_url: str = None) -> bool:
        """Add a new product to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO products (name, description, price, stock, image_url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, description, price, stock, image_url))
                conn.commit()
                logger.info(f"Added product: {name}")
                return True
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return False
    
    def get_cart(self, user_id: int) -> List[Tuple]:
        """Get user's cart items"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.name, p.price, c.quantity, p.stock
                    FROM cart c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.user_id = ?
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting cart for user {user_id}: {e}")
            return []
    
    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> bool:
        """Add item to user's cart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cart (user_id, product_id, quantity)
                    VALUES (?, ?, COALESCE((SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?), 0) + ?)
                ''', (user_id, product_id, user_id, product_id, quantity))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return False
    
    def clear_cart(self, user_id: int) -> bool:
        """Clear user's cart"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False
