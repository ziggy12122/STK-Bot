import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ShopDatabase:
    """Enhanced database manager for the Discord shop bot"""

    def __init__(self, db_path: str = 'shop.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.create_tables()

    def create_tables(self):
        """Create all necessary database tables"""
        cursor = self.conn.cursor()

        # Products table with enhanced fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                image_url TEXT,
                category TEXT DEFAULT 'general',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Enhanced carts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        ''')

        # Orders table with status tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_method TEXT DEFAULT 'discord',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Order items with snapshot pricing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
            )
        ''')

        # User purchase history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                total_spent REAL DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                first_purchase TIMESTAMP,
                last_purchase TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()
        logger.info("Database tables created successfully")

    def add_product(self, name: str, description: str, price: float, stock: int, 
                   image_url: str = None, category: str = 'general') -> Optional[int]:
        """Add a new product"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO products (name, description, price, stock, image_url, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, price, stock, image_url, category))

            self.conn.commit()
            product_id = cursor.lastrowid
            logger.info(f"Added product: {name} (ID: {product_id})")
            return product_id
        except sqlite3.Error as e:
            logger.error(f"Error adding product: {e}")
            return None

    def get_product(self, product_id: int) -> Optional[sqlite3.Row]:
        """Get a single product by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()

    def get_all_products(self, active_only: bool = False) -> List[sqlite3.Row]:
        """Get all products from database"""
        try:
            cursor = self.conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC")
            else:
                cursor.execute("SELECT * FROM products ORDER BY created_at DESC")

            columns = [description[0] for description in cursor.description]
            products = []

            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                products.append(product)

            return products

        except sqlite3.Error as e:
            logger.error(f"Database error getting products: {e}")
            return []

    def get_products_by_category(self, category, active_only=True):
        """Get products by category"""
        try:
            cursor = self.conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM products WHERE category = ? AND is_active = 1 ORDER BY created_at DESC", (category,))
            else:
                cursor.execute("SELECT * FROM products WHERE category = ? ORDER BY created_at DESC", (category,))

            columns = [description[0] for description in cursor.description]
            products = []

            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                products.append(product)

            return products

        except sqlite3.Error as e:
            logger.error(f"Database error getting products by category: {e}")
            return []

    def update_product_stock(self, product_id: int, new_stock: int) -> bool:
        """Update product stock"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET stock = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_stock, product_id))

            self.conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Updated stock for product {product_id} to {new_stock}")
                return True
            return False
        except sqlite3.Error as e:
            logger.error(f"Error updating stock: {e}")
            return False

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product fields"""
        try:
            # Build dynamic update query
            set_clauses = []
            values = []

            for field, value in kwargs.items():
                if field in ['name', 'description', 'price', 'stock', 'image_url', 'category', 'is_active']:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)

            if not set_clauses:
                return False

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(product_id)

            cursor = self.conn.cursor()
            query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)

            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete a product"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> bool:
        """Add item to user's cart"""
        try:
            cursor = self.conn.cursor()

            # Check if product exists and has stock
            cursor.execute('SELECT stock FROM products WHERE id = ? AND is_active = 1', (product_id,))
            product = cursor.fetchone()

            if not product or product['stock'] < quantity:
                return False

            # Check if item already in cart
            cursor.execute('SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?', 
                          (user_id, product_id))
            existing = cursor.fetchone()

            if existing:
                # Update quantity
                new_quantity = existing['quantity'] + quantity
                if new_quantity > product['stock']:
                    return False

                cursor.execute('''
                    UPDATE carts SET quantity = ?, added_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ? AND product_id = ?
                ''', (new_quantity, user_id, product_id))
            else:
                # Add new item
                cursor.execute('''
                    INSERT INTO carts (user_id, product_id, quantity)
                    VALUES (?, ?, ?)
                ''', (user_id, product_id, quantity))

            self.conn.commit()
            logger.info(f"Added {quantity} of product {product_id} to cart for user {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding to cart: {e}")
            return False

    def get_cart_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all items in user's cart with product details"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                p.id, p.name, p.description, p.price, p.stock, p.image_url,
                c.quantity,
                (p.price * c.quantity) as total_price
            FROM carts c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ? AND p.is_active = 1
            ORDER BY c.added_at DESC
        ''', (user_id,))

        return [dict(row) for row in cursor.fetchall()]

    def remove_from_cart(self, user_id: int, product_id: int) -> bool:
        """Remove item from cart"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM carts WHERE user_id = ? AND product_id = ?', 
                          (user_id, product_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error removing from cart: {e}")
            return False

    def clear_cart(self, user_id: int) -> bool:
        """Clear user's cart"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
            self.conn.commit()
            logger.info(f"Cleared cart for user {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error clearing cart: {e}")
            return False

    def create_order(self, user_id: int, username: str, cart_items: List[Dict], total_amount: float) -> Optional[int]:
        """Create order from cart items"""
        try:
            cursor = self.conn.cursor()

            # Create order
            cursor.execute('''
                INSERT INTO orders (user_id, username, total_amount, status)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, total_amount, 'completed'))

            order_id = cursor.lastrowid

            # Add order items and update stock
            for item in cart_items:
                cursor.execute('''
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, item['id'], item['name'], item['quantity'], 
                      item['price'], item['total_price']))

                # Update product stock
                new_stock = item['stock'] - item['quantity']
                cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, item['id']))

            # Update user stats
            self.update_user_stats(user_id, username, total_amount)

            # Clear cart
            cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))

            self.conn.commit()
            logger.info(f"Created order {order_id} for user {user_id}")
            return order_id
        except sqlite3.Error as e:
            logger.error(f"Error creating order: {e}")
            self.conn.rollback()
            return None

    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        """Get order details"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        return cursor.fetchone()

    def get_order_items(self, order_id: int) -> List[sqlite3.Row]:
        """Get items in an order"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        return cursor.fetchall()

    def update_order_status(self, order_id: int, status: str, notes: str = None) -> bool:
        """Update order status"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (status, notes, order_id))

            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating order status: {e}")
            return False

    def get_user_orders(self, user_id: int) -> List[sqlite3.Row]:
        """Get all orders for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()

    def update_user_stats(self, user_id: int, username: str, amount: float) -> None:
        """Update or create user statistics"""
        try:
            cursor = self.conn.cursor()

            # Check if user stats exist
            cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing stats
                cursor.execute('''
                    UPDATE user_stats 
                    SET username = ?, 
                        total_spent = total_spent + ?, 
                        total_orders = total_orders + 1,
                        last_purchase = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (username, amount, user_id))
            else:
                # Create new stats
                cursor.execute('''
                    INSERT INTO user_stats (user_id, username, total_spent, total_orders, first_purchase, last_purchase)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, username, amount))

            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating user stats: {e}")

    def get_user_stats(self, user_id: int) -> Optional[sqlite3.Row]:
        """Get user statistics"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def get_sales_analytics(self) -> Dict[str, Any]:
        """Get sales analytics"""
        cursor = self.conn.cursor()

        # Total sales
        cursor.execute('SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status = "completed"')
        total_orders, total_revenue = cursor.fetchone()

        # Top products
        cursor.execute('''
            SELECT product_name, SUM(quantity) as total_sold, SUM(total_price) as revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = "completed"
            GROUP BY product_name
            ORDER BY total_sold DESC
            LIMIT 5
        ''')
        top_products = cursor.fetchall()

        # Recent orders
        cursor.execute('''
            SELECT id, username, total_amount, created_at
            FROM orders
            WHERE status = "completed"
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        recent_orders = cursor.fetchall()

        return {
            'total_orders': total_orders or 0,
            'total_revenue': total_revenue or 0.0,
            'top_products': [dict(row) for row in top_products],
            'recent_orders': [dict(row) for row in recent_orders]
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()