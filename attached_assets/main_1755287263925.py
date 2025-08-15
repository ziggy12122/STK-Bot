import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import sqlite3
from datetime import datetime
import os
from typing import Optional, List, Dict, Any
from load_env import load_environment, get_required_env, get_optional_env

# Bot configuration
CONFIG = {
    'prefix': '!',
    'admin_role_id': None,  # Set this to your admin role ID
    'shop_channel_id': None,  # Set this to your shop channel ID
    'ticket_channel_id': None,  # Set this to your ticket channel ID
    'customer_role_id': None,  # Set this to the role given after purchase
}

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=CONFIG['prefix'], intents=intents)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('shop.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                image_url TEXT,
                category TEXT DEFAULT 'uncategorized',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Carts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

        # Order items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')

        self.conn.commit()

    def add_product(self, name: str, description: str, price: float, stock: int, image_url: str = None, category: str = 'uncategorized'):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, stock, image_url, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, stock, image_url, category))
        self.conn.commit()
        return cursor.lastrowid

    def get_product(self, product_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()

    def get_all_products(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE stock > 0 ORDER BY name')
        return cursor.fetchall()

    def get_products_by_category(self, category: str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE category = ? AND stock > 0 ORDER BY name', (category,))
        return cursor.fetchall()

    def update_stock(self, product_id: int, new_stock: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, product_id))
        self.conn.commit()

    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO carts (user_id, product_id, quantity)
            VALUES (?, ?, COALESCE((SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?), 0) + ?)
        ''', (user_id, product_id, user_id, product_id, quantity))
        self.conn.commit()

    def get_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.id, p.name, p.price, c.quantity, p.stock
            FROM carts c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        ''', (user_id,))
        return cursor.fetchall()

    def clear_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def create_order(self, user_id: int, cart_items: List, total_amount: float):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO orders (user_id, total_amount) VALUES (?, ?)', (user_id, total_amount))
        order_id = cursor.lastrowid

        for item in cart_items:
            product_id, name, price, quantity, stock = item
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, product_id, quantity, price))

            # Update stock
            new_stock = stock - quantity
            cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, product_id))

        self.conn.commit()
        return order_id

# Initialize database
db = Database()

class ProductView(discord.ui.View):
    def __init__(self, products: List):
        super().__init__(timeout=300)
        self.products = products
        self.current_page = 0
        self.max_page = len(products) - 1 if products else 0

    def create_embed(self):
        if not self.products:
            embed = discord.Embed(
                title="ðª Shop",
                description="No products available at the moment.",
                color=0xff6b6b
            )
            return embed

        product = self.products[self.current_page]
        product_id, name, description, price, stock, image_url, category, created_at = product

        embed = discord.Embed(
            title=f"ðï¸ {name}",
            description=description or "No description available.",
            color=0x4ecdc4
        )

        embed.add_field(name="ð° Price", value=f"${price:.2f}", inline=True)
        embed.add_field(name="ð¦ Stock", value=f"{stock} available", inline=True)
        embed.add_field(name="ð Product ID", value=f"{product_id}", inline=True)
        embed.add_field(name="ð·ï¸ Category", value=category, inline=True)

        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_page + 1} | Made by Zpofe")

        return embed

    @discord.ui.button(label="âï¸ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("You're already on the first page!", ephemeral=True)

    @discord.ui.button(label="ð Add to Cart", style=discord.ButtonStyle.primary)
    async def add_to_cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.products:
            await interaction.response.send_message("No products available!", ephemeral=True)
            return

        product = self.products[self.current_page]
        product_id, name, description, price, stock, image_url, category, created_at = product

        if stock <= 0:
            await interaction.response.send_message("This product is out of stock!", ephemeral=True)
            return

        db.add_to_cart(interaction.user.id, product_id, 1)

        embed = discord.Embed(
            title="â Added to Cart",
            description=f"**{name}** has been added to your cart!",
            color=0x2ecc71
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="â¶ï¸ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_page:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("You're already on the last page!", ephemeral=True)

class CheckoutView(discord.ui.View):
    def __init__(self, user_id: int, cart_items: List, total: float):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.cart_items = cart_items
        self.total = total

    @discord.ui.button(label="â Confirm Purchase", style=discord.ButtonStyle.success)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if all items are still in stock
        for item in self.cart_items:
            product_id, name, price, quantity, stock = item
            current_product = db.get_product(product_id)
            if not current_product or current_product[4] < quantity:  # stock is index 4
                await interaction.response.send_message(
                    f"Sorry, **{name}** is no longer available in the requested quantity.",
                    ephemeral=True
                )
                return

        # Create order
        order_id = db.create_order(self.user_id, self.cart_items, self.total)

        # Clear cart
        db.clear_cart(self.user_id)

        # Create ticket
        await self.create_ticket(interaction, order_id)

        # Give customer role
        if CONFIG['customer_role_id']:
            try:
                role = interaction.guild.get_role(CONFIG['customer_role_id'])
                if role:
                    await interaction.user.add_roles(role)
            except:
                pass

        embed = discord.Embed(
            title="ð Purchase Successful!",
            description=f"Your order (ID: {order_id}) has been placed successfully!\nA support ticket has been created for you.",
            color=0x2ecc71
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="â Cancel", style=discord.ButtonStyle.danger)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="â Purchase Cancelled",
            description="Your purchase has been cancelled. Your cart items are still saved.",
            color=0xe74c3c
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def create_ticket(self, interaction: discord.Interaction, order_id: int):
        if not CONFIG['ticket_channel_id']:
            return

        ticket_channel = bot.get_channel(CONFIG['ticket_channel_id'])
        if not ticket_channel:
            return

        embed = discord.Embed(
            title=f"ð« New Order - #{order_id}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="ð¤ Customer", value=f"{interaction.user.mention}\n({interaction.user.id})", inline=False)
        embed.add_field(name="ð° Total", value=f"${self.total:.2f}", inline=True)
        embed.add_field(name="ð Order ID", value=f"{order_id}", inline=True)

        items_text = ""
        for item in self.cart_items:
            product_id, name, price, quantity, stock = item
            items_text += f"â¢ {name} x{quantity} - ${price * quantity:.2f}\n"

        embed.add_field(name="ðï¸ Items", value=items_text, inline=False)
        embed.set_footer(text="Made by Zpofe")

        await ticket_channel.send(embed=embed)

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_guild_join(guild):
    """Send welcome message when bot joins a guild"""
    # Find the first text channel the bot can send messages to
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="ðï¸ Welcome to STK Shop Bot!",
                description="Thank you for adding me to your server!",
                color=0x4ecdc4
            )

            embed.add_field(
                name="ð About",
                value="I'm a comprehensive Discord shop bot that allows you to manage products, process orders, and handle customer interactions seamlessly.",
                inline=False
            )

            embed.add_field(
                name="ð Getting Started",
                value="Use `/shop` to browse products\nUse `/cart` to view your cart\nUse `/checkout` to purchase items",
                inline=True
            )

            embed.add_field(
                name="âï¸ Admin Commands",
                value="Use `/addproduct` to add products\nUse `/updatestock` to manage inventory\nUse `/products` to view all products",
                inline=True
            )

            embed.add_field(
                name="ð¡ Created by",
                value="**Zpofe** - Professional Discord Bot Developer",
                inline=False
            )

            embed.set_footer(text="Configure your role and channel IDs in environment variables for full functionality!")

            try:
                await channel.send(embed=embed)
                break
            except:
                continue

# Shop commands
@bot.tree.command(name='shop', description='Browse all available products in the shop')
async def show_shop(interaction: discord.Interaction):
    """Display the shop with all available products"""
    products = db.get_all_products()
    view = ProductView(products)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='cart', description='View your shopping cart contents')
async def show_cart(interaction: discord.Interaction):
    """Show user's cart contents"""
    cart_items = db.get_cart(interaction.user.id)

    if not cart_items:
        embed = discord.Embed(
            title="ð Your Cart",
            description="Your cart is empty! Use `/shop` to browse products.",
            color=0x95a5a6
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="ð Your Cart",
        color=0x3498db
    )

    total = 0
    cart_text = ""

    for item in cart_items:
        product_id, name, price, quantity, stock = item
        item_total = price * quantity
        total += item_total
        cart_text += f"â¢ **{name}** x{quantity} - ${item_total:.2f}\n"

    embed.add_field(name="ð Items", value=cart_text, inline=False)
    embed.add_field(name="ð° Total", value=f"${total:.2f}", inline=True)
    embed.set_footer(text="Use /checkout to purchase these items | Made by Zpofe")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='checkout', description='Checkout and purchase your cart items')
async def checkout(interaction: discord.Interaction):
    """Checkout and purchase cart items"""
    cart_items = db.get_cart(interaction.user.id)

    if not cart_items:
        embed = discord.Embed(
            title="â Empty Cart",
            description="Your cart is empty! Add some items first.",
            color=0xe74c3c
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed)
        return

    total = sum(price * quantity for _, _, price, quantity, _ in cart_items)

    embed = discord.Embed(
        title="ð§¾ Checkout",
        description="Please review your order:",
        color=0xf39c12
    )

    items_text = ""
    for item in cart_items:
        product_id, name, price, quantity, stock = item
        item_total = price * quantity
        items_text += f"â¢ **{name}** x{quantity} - ${item_total:.2f}\n"

    embed.add_field(name="ð Items", value=items_text, inline=False)
    embed.add_field(name="ð° Total", value=f"${total:.2f}", inline=True)
    embed.set_footer(text="Click confirm to complete your purchase | Made by Zpofe")

    view = CheckoutView(interaction.user.id, cart_items, total)
    await interaction.response.send_message(embed=embed, view=view)

# Admin commands
def is_admin_interaction(interaction: discord.Interaction) -> bool:
    """Check if user has admin permissions"""
    if CONFIG['admin_role_id']:
        return any(role.id == CONFIG['admin_role_id'] for role in interaction.user.roles)
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name='addproduct', description='Add a new product to the shop (Admin only)')
@app_commands.describe(
    name='Product name',
    price='Product price',
    stock='Stock quantity',
    description='Product description (optional)',
    image='Product image (optional)',
    category='Product category (optional)'
)
async def add_product(interaction: discord.Interaction, name: str, price: float, stock: int, description: str = None, image: discord.Attachment = None, category: str = 'uncategorized'):
    """Add a new product to the shop"""
    if not is_admin_interaction(interaction):
        embed = discord.Embed(
            title="â Permission Denied",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    image_url = None
    if image:
        image_url = image.url

    product_id = db.add_product(name, description, price, stock, image_url, category)

    embed = discord.Embed(
        title="â Product Added",
        description=f"**{name}** has been added to the shop!",
        color=0x2ecc71
    )
    embed.add_field(name="ð° Price", value=f"${price:.2f}", inline=True)
    embed.add_field(name="ð¦ Stock", value=f"{stock}", inline=True)
    embed.add_field(name="ð Product ID", value=f"{product_id}", inline=True)
    embed.add_field(name="ð·ï¸ Category", value=category, inline=True)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text="Made by Zpofe")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='updatestock', description='Update product stock level (Admin only)')
@app_commands.describe(
    product_id='Product ID to update',
    new_stock='New stock quantity'
)
async def update_stock(interaction: discord.Interaction, product_id: int, new_stock: int):
    """Update product stock level"""
    if not is_admin_interaction(interaction):
        embed = discord.Embed(
            title="â Permission Denied",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    product = db.get_product(product_id)
    if not product:
        embed = discord.Embed(title="â Product not found!", color=0xe74c3c)
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed)
        return

    db.update_stock(product_id, new_stock)

    embed = discord.Embed(
        title="ð¦ Stock Updated",
        description=f"Stock for **{product[1]}** updated to {new_stock}",
        color=0x3498db
    )
    embed.set_footer(text="Made by Zpofe")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='products', description='List all products for admin management (Admin only)')
async def list_products(interaction: discord.Interaction):
    """List all products for admin management"""
    if not is_admin_interaction(interaction):
        embed = discord.Embed(
            title="â Permission Denied",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY name')
    products = cursor.fetchall()

    if not products:
        embed = discord.Embed(title="No products found!", color=0xe74c3c)
        embed.set_footer(text="Made by Zpofe")
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="ð All Products",
        color=0x9b59b6
    )

    for product in products:
        product_id, name, description, price, stock, image_url, category, created_at = product
        embed.add_field(
            name=f"{name} (ID: {product_id})",
            value=f"Price: ${price:.2f} | Stock: {stock} | Category: {category}",
            inline=False
        )

    embed.set_footer(text="Made by Zpofe")
    await interaction.response.send_message(embed=embed)

# Daily Deals and Categories commands
@bot.tree.command(name='deals', description='View today\'s special deals and offers')
async def daily_deals(interaction: discord.Interaction):
    """Show daily deals and special offers"""
    embed = discord.Embed(
        title="ð¯ Daily Deals & Special Offers",
        description="**Limited time offers - Don't miss out!**",
        color=0xf39c12
    )

    # Get products on sale (you can add a sale_price field to database later)
    products = db.get_all_products()
    if products:
        deal_products = products[:3]  # Show first 3 as deals for demo

        deals_text = ""
        for product in deal_products:
            product_id, name, description, price, stock, image_url, category, created_at = product
            original_price = price * 1.25  # Simulate original price
            savings = original_price - price
            deals_text += f"ð¥ **{name}**\n~~${original_price:.2f}~~ â **${price:.2f}** (Save ${savings:.2f}!)\n\n"

        embed.add_field(name="ð¥ Flash Sales", value=deals_text, inline=False)

    embed.add_field(
        name="ð Special Offers",
        value="â¢ Buy 2 Get 1 Free on selected items\nâ¢ First-time buyer 10% discount\nâ¢ Bulk purchase discounts available\nâ¢ Loyalty rewards program",
        inline=True
    )

    embed.add_field(
        name="â° Time Limited",
        value="â¢ Daily deals refresh at midnight\nâ¢ Flash sales last 24 hours\nâ¢ Premium member early access\nâ¢ Weekend bonus deals",
        inline=True
    )

    embed.set_footer(text="Made by Zpofe | Don't miss these amazing deals!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='categories', description='Browse products by category')
@app_commands.describe(category='Product category to filter by')
async def browse_categories(interaction: discord.Interaction, category: str = None):
    """Browse products by category"""
    if category:
        products = db.get_products_by_category(category.lower())

        if not products:
            embed = discord.Embed(
                title=f"ð·ï¸ {category.title()} Category",
                description=f"No products found in the **{category}** category.",
                color=0xe74c3c
            )
            embed.set_footer(text="Made by Zpofe")
            await interaction.response.send_message(embed=embed)
            return

        view = ProductView(products)
        embed = view.create_embed()
        embed.title = f"ð·ï¸ {category.title()} Category"
        await interaction.response.send_message(embed=embed, view=view)
    else:
        # Show available categories
        cursor = db.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM products WHERE stock > 0 ORDER BY category')
        categories = cursor.fetchall()

        embed = discord.Embed(
            title="ð·ï¸ Product Categories",
            description="**Browse our organized product categories**",
            color=0x9b59b6
        )

        if categories:
            category_text = ""
            for cat_tuple in categories:
                cat_name = cat_tuple[0]
                # Fetch count for this category
                cursor.execute('SELECT COUNT(*) FROM products WHERE category = ? AND stock > 0', (cat_name,))
                count = cursor.fetchone()[0]
                category_text += f"ð **{cat_name.title()}** ({count} items)\n"
            embed.add_field(name="Available Categories", value=category_text, inline=False)
            embed.add_field(name="Usage", value="Use `/categories <category_name>` to browse a specific category", inline=False)
        else:
            embed.description = "No categories available yet. Add some products first!"

        embed.set_footer(text="Made by Zpofe | Organized Shopping Experience")
        await interaction.response.send_message(embed=embed)


# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="â Permission Denied",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.CommandInvokeError):
        # Handle errors that occur during command execution
        original_error = error.original
        print(f"Error during command {interaction.command.name}: {original_error}")

        embed = discord.Embed(
            title="â An Error Occurred",
            description=f"An error occurred while processing your command: `{original_error.__class__.__name__}`",
            color=0xe74c3c
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"Unhandled slash command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

# Load configuration from environment variables
def load_config():
    load_environment()  # Load .env file if it exists

    # Load optional role/channel IDs
    admin_role = get_optional_env('ADMIN_ROLE_ID')
    CONFIG['admin_role_id'] = int(admin_role) if admin_role else None

    shop_channel = get_optional_env('SHOP_CHANNEL_ID')
    CONFIG['shop_channel_id'] = int(shop_channel) if shop_channel else None

    ticket_channel = get_optional_env('TICKET_CHANNEL_ID')
    CONFIG['ticket_channel_id'] = int(ticket_channel) if ticket_channel else None

    customer_role = get_optional_env('CUSTOMER_ROLE_ID')
    CONFIG['customer_role_id'] = int(customer_role) if customer_role else None

if __name__ == '__main__':
    load_config()

    # Get bot token from environment
    try:
        token = get_required_env('DISCORD_BOT_TOKEN')
        
        # Add HTTP server for Koyeb compatibility
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Discord Bot is running')
                
            def log_message(self, format, *args):
                pass  # Suppress HTTP server logs
        
        # Start HTTP server for health checks
        port = int(os.getenv('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Health check server running on port {port}")
        
        bot.run(token)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your Discord bot token!")
