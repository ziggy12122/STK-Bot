
import discord
from discord.ext import commands
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
    
    def add_product(self, name: str, description: str, price: float, stock: int, image_url: str = None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, stock, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, price, stock, image_url))
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
                title="🏪 Shop",
                description="No products available at the moment.",
                color=0xff6b6b
            )
            return embed
        
        product = self.products[self.current_page]
        product_id, name, description, price, stock, image_url, created_at = product
        
        embed = discord.Embed(
            title=f"🛍️ {name}",
            description=description or "No description available.",
            color=0x4ecdc4
        )
        
        embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
        embed.add_field(name="📦 Stock", value=f"{stock} available", inline=True)
        embed.add_field(name="🆔 Product ID", value=f"{product_id}", inline=True)
        
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_page + 1}")
        
        return embed
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("You're already on the first page!", ephemeral=True)
    
    @discord.ui.button(label="🛒 Add to Cart", style=discord.ButtonStyle.primary)
    async def add_to_cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.products:
            await interaction.response.send_message("No products available!", ephemeral=True)
            return
        
        product = self.products[self.current_page]
        product_id, name, description, price, stock, image_url, created_at = product
        
        if stock <= 0:
            await interaction.response.send_message("This product is out of stock!", ephemeral=True)
            return
        
        db.add_to_cart(interaction.user.id, product_id, 1)
        
        embed = discord.Embed(
            title="✅ Added to Cart",
            description=f"**{name}** has been added to your cart!",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
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
    
    @discord.ui.button(label="✅ Confirm Purchase", style=discord.ButtonStyle.success)
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
            title="🎉 Purchase Successful!",
            description=f"Your order (ID: {order_id}) has been placed successfully!\nA support ticket has been created for you.",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Purchase Cancelled",
            description="Your purchase has been cancelled. Your cart items are still saved.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def create_ticket(self, interaction: discord.Interaction, order_id: int):
        if not CONFIG['ticket_channel_id']:
            return
        
        ticket_channel = bot.get_channel(CONFIG['ticket_channel_id'])
        if not ticket_channel:
            return
        
        embed = discord.Embed(
            title=f"🎫 New Order - #{order_id}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="👤 Customer", value=f"{interaction.user.mention}\n({interaction.user.id})", inline=False)
        embed.add_field(name="💰 Total", value=f"${self.total:.2f}", inline=True)
        embed.add_field(name="📋 Order ID", value=f"{order_id}", inline=True)
        
        items_text = ""
        for item in self.cart_items:
            product_id, name, price, quantity, stock = item
            items_text += f"• {name} x{quantity} - ${price * quantity:.2f}\n"
        
        embed.add_field(name="🛍️ Items", value=items_text, inline=False)
        
        await ticket_channel.send(embed=embed)

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

# Shop commands
@bot.command(name='shop')
async def show_shop(ctx):
    """Display the shop with all available products"""
    products = db.get_all_products()
    view = ProductView(products)
    embed = view.create_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='cart')
async def show_cart(ctx):
    """Show user's cart contents"""
    cart_items = db.get_cart(ctx.author.id)
    
    if not cart_items:
        embed = discord.Embed(
            title="🛒 Your Cart",
            description="Your cart is empty! Use `!shop` to browse products.",
            color=0x95a5a6
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🛒 Your Cart",
        color=0x3498db
    )
    
    total = 0
    cart_text = ""
    
    for item in cart_items:
        product_id, name, price, quantity, stock = item
        item_total = price * quantity
        total += item_total
        cart_text += f"• **{name}** x{quantity} - ${item_total:.2f}\n"
    
    embed.add_field(name="📋 Items", value=cart_text, inline=False)
    embed.add_field(name="💰 Total", value=f"${total:.2f}", inline=True)
    embed.set_footer(text="Use !checkout to purchase these items")
    
    await ctx.send(embed=embed)

@bot.command(name='checkout')
async def checkout(ctx):
    """Checkout and purchase cart items"""
    cart_items = db.get_cart(ctx.author.id)
    
    if not cart_items:
        embed = discord.Embed(
            title="❌ Empty Cart",
            description="Your cart is empty! Add some items first.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
        return
    
    total = sum(price * quantity for _, _, price, quantity, _ in cart_items)
    
    embed = discord.Embed(
        title="🧾 Checkout",
        description="Please review your order:",
        color=0xf39c12
    )
    
    items_text = ""
    for item in cart_items:
        product_id, name, price, quantity, stock = item
        item_total = price * quantity
        items_text += f"• **{name}** x{quantity} - ${item_total:.2f}\n"
    
    embed.add_field(name="📋 Items", value=items_text, inline=False)
    embed.add_field(name="💰 Total", value=f"${total:.2f}", inline=True)
    embed.set_footer(text="Click confirm to complete your purchase")
    
    view = CheckoutView(ctx.author.id, cart_items, total)
    await ctx.send(embed=embed, view=view)

# Admin commands
def is_admin():
    def predicate(ctx):
        if CONFIG['admin_role_id']:
            return any(role.id == CONFIG['admin_role_id'] for role in ctx.author.roles)
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command(name='addproduct')
@is_admin()
async def add_product(ctx, name: str, price: float, stock: int, *, description: str = None):
    """Add a new product to the shop"""
    image_url = None
    if ctx.message.attachments:
        image_url = ctx.message.attachments[0].url
    
    product_id = db.add_product(name, description, price, stock, image_url)
    
    embed = discord.Embed(
        title="✅ Product Added",
        description=f"**{name}** has been added to the shop!",
        color=0x2ecc71
    )
    embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
    embed.add_field(name="📦 Stock", value=f"{stock}", inline=True)
    embed.add_field(name="🆔 Product ID", value=f"{product_id}", inline=True)
    
    if image_url:
        embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)

@bot.command(name='updatestock')
@is_admin()
async def update_stock(ctx, product_id: int, new_stock: int):
    """Update product stock level"""
    product = db.get_product(product_id)
    if not product:
        await ctx.send("❌ Product not found!")
        return
    
    db.update_stock(product_id, new_stock)
    
    embed = discord.Embed(
        title="📦 Stock Updated",
        description=f"Stock for **{product[1]}** updated to {new_stock}",
        color=0x3498db
    )
    await ctx.send(embed=embed)

@bot.command(name='products')
@is_admin()
async def list_products(ctx):
    """List all products for admin management"""
    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY name')
    products = cursor.fetchall()
    
    if not products:
        await ctx.send("No products found!")
        return
    
    embed = discord.Embed(
        title="📋 All Products",
        color=0x9b59b6
    )
    
    for product in products:
        product_id, name, description, price, stock, image_url, created_at = product
        embed.add_field(
            name=f"{name} (ID: {product_id})",
            value=f"Price: ${price:.2f} | Stock: {stock}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Required Argument",
            description=f"Please provide all required arguments.\nUse `{CONFIG['prefix']}help {ctx.command}` for more info.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        embed = discord.Embed(
            title="❌ Permission Denied", 
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
    else:
        print(f"Unexpected error: {error}")

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
        bot.run(token)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your Discord bot token!")
        exit(1)
