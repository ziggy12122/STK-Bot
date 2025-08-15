
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_active ON products (is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_carts_user ON carts (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status)')
        
        self.conn.commit()
    
    # Product management methods
    def add_product(self, name: str, description: str, price: float, stock: int, 
                   image_url: str = None, category: str = 'general') -> int:
        """Add a new product to the database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, stock, image_url, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, stock, image_url, category))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_product(self, product_id: int) -> Optional[sqlite3.Row]:
        """Get a single product by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,))
        return cursor.fetchone()
    
    def get_all_products(self, category: str = None) -> List[sqlite3.Row]:
        """Get all active products, optionally filtered by category"""
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY name', (category,))
        else:
            cursor.execute('SELECT * FROM products WHERE is_active = 1 ORDER BY name')
        return cursor.fetchall()
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product fields"""
        if not kwargs:
            return False
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        
        fields = ', '.join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [product_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f'UPDATE products SET {fields} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_stock(self, product_id: int, new_stock: int) -> bool:
        """Update product stock level"""
        return self.update_product(product_id, stock=new_stock)
    
    def deactivate_product(self, product_id: int) -> bool:
        """Soft delete a product (mark as inactive)"""
        return self.update_product(product_id, is_active=0)
    
    # Cart management methods
    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> bool:
        """Add item to user's cart"""
        # Check if product exists and has stock
        product = self.get_product(product_id)
        if not product or product['stock'] < quantity:
            return False
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO carts (user_id, product_id, quantity, added_at)
            VALUES (?, ?, 
                COALESCE((SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?), 0) + ?,
                CURRENT_TIMESTAMP)
        ''', (user_id, product_id, user_id, product_id, quantity))
        self.conn.commit()
        return True
    
    def remove_from_cart(self, user_id: int, product_id: int) -> bool:
        """Remove item from user's cart"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM carts WHERE user_id = ? AND product_id = ?', (user_id, product_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_cart(self, user_id: int) -> List[sqlite3.Row]:
        """Get user's cart with product details"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.id, p.name, p.price, p.image_url, c.quantity, p.stock,
                   (p.price * c.quantity) as total_price
            FROM carts c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ? AND p.is_active = 1
            ORDER BY c.added_at
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_cart_total(self, user_id: int) -> float:
        """Get total value of user's cart"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT SUM(p.price * c.quantity) as total
            FROM carts c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ? AND p.is_active = 1
        ''', (user_id,))
        result = cursor.fetchone()
        return result['total'] or 0.0
    
    def clear_cart(self, user_id: int) -> bool:
        """Clear user's cart"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # Order management methods
    def create_order(self, user_id: int, username: str) -> Optional[int]:
        """Create order from user's cart"""
        cart_items = self.get_cart(user_id)
        if not cart_items:
            return None
        
        # Verify stock availability
        for item in cart_items:
            if item['stock'] < item['quantity']:
                return None
        
        total_amount = sum(item['total_price'] for item in cart_items)
        
        cursor = self.conn.cursor()
        
        # Create order
        cursor.execute('''
            INSERT INTO orders (user_id, username, total_amount)
            VALUES (?, ?, ?)
        ''', (user_id, username, total_amount))
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
        return order_id
    
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
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE orders 
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, notes, order_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_user_orders(self, user_id: int) -> List[sqlite3.Row]:
        """Get all orders for a user"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        return cursor.fetchall()
    
    # User statistics methods
    def update_user_stats(self, user_id: int, username: str, amount: float):
        """Update user purchase statistics"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_stats 
            (user_id, username, total_spent, total_orders, first_purchase, last_purchase)
            VALUES (?, ?, 
                COALESCE((SELECT total_spent FROM user_stats WHERE user_id = ?), 0) + ?,
                COALESCE((SELECT total_orders FROM user_stats WHERE user_id = ?), 0) + 1,
                COALESCE((SELECT first_purchase FROM user_stats WHERE user_id = ?), CURRENT_TIMESTAMP),
                CURRENT_TIMESTAMP)
        ''', (user_id, username, user_id, amount, user_id, user_id))
        self.conn.commit()
    
    def get_user_stats(self, user_id: int) -> Optional[sqlite3.Row]:
        """Get user purchase statistics"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    # Admin/Analytics methods
    def get_sales_summary(self) -> Dict[str, Any]:
        """Get sales analytics summary"""
        cursor = self.conn.cursor()
        
        # Total sales
        cursor.execute('SELECT SUM(total_amount) as total_sales, COUNT(*) as total_orders FROM orders')
        sales_data = cursor.fetchone()
        
        # Top products
        cursor.execute('''
            SELECT product_name, SUM(quantity) as total_sold, SUM(total_price) as revenue
            FROM order_items 
            GROUP BY product_name 
            ORDER BY total_sold DESC 
            LIMIT 5
        ''')
        top_products = cursor.fetchall()
        
        # Recent orders
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 10')
        recent_orders = cursor.fetchall()
        
        return {
            'total_sales': sales_data['total_sales'] or 0,
            'total_orders': sales_data['total_orders'] or 0,
            'top_products': [dict(p) for p in top_products],
            'recent_orders': [dict(o) for o in recent_orders]
        }
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the database"""
        if not backup_path:
            backup_path = f"shop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        backup_conn = sqlite3.connect(backup_path)
        self.conn.backup(backup_conn)
        backup_conn.close()
        
        return backup_path
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.close()
