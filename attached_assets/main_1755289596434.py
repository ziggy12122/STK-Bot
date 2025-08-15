import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from config import BotConfig
from database_manager import ShopDatabase
from load_env import load_environment

# Load environment variables
load_environment()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = ShopDatabase()

class ShopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(
            command_prefix=BotConfig.PREFIX,
            intents=intents,
            help_command=None
        )

        self.db = db

    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # Test database connection
        try:
            # Test if database is working
            test_products = self.db.get_all_products()
            logger.info(f'Database connected successfully. Found {len(test_products)} products.')
        except Exception as e:
            logger.error(f'Database connection issue: {e}')

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} command(s)')
        except Exception as e:
            logger.error(f'Failed to sync commands: {e}')

# Create bot instance
bot = ShopBot()

class ShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.current_tab = "weapons"

    def get_products_by_tab(self, tab):
        """Get products for the selected tab"""
        if tab == "weapons":
            return db.get_all_products("weapons")
        elif tab == "money":
            return db.get_all_products("money")
        elif tab == "other":
            # Get all products that aren't weapons or money
            all_products = db.get_all_products()
            return [p for p in all_products if p['category'] not in ['weapons', 'money']]
        return []

    def create_shop_embed(self):
        """Create the shop embed for current tab"""
        products = self.get_products_by_tab(self.current_tab)

        # Tab emojis
        tab_emojis = {
            "weapons": "🔫",
            "money": "💰", 
            "other": "📦"
        }

        embed = discord.Embed(
            title=f"🛍️ Zpofe Shop - {tab_emojis[self.current_tab]} {self.current_tab.title()}",
            description=f"Browse our {self.current_tab} products:",
            color=BotConfig.COLORS['shop']
        )

        if not products:
            embed.add_field(
                name="No Products",
                value=f"No {self.current_tab} products available at the moment.",
                inline=False
            )
        else:
            for product in products[:8]:  # Show up to 8 products
                stock_text = f"✅ In Stock: {product['stock']}" if product['stock'] > 0 else "❌ Out of Stock"
                embed.add_field(
                    name=f"{product['name']} - ${product['price']:.2f}",
                    value=f"{product['description'] or 'No description'}\n{stock_text}\n`ID: {product['id']}`",
                    inline=True
                )

        embed.set_footer(text="Click the buttons below to browse different categories or add items to cart")
        return embed

    @discord.ui.button(label="🔫 Weapons", style=discord.ButtonStyle.primary, custom_id="weapons")
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.current_tab = "weapons"
        embed = self.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💰 Money", style=discord.ButtonStyle.success, custom_id="money")
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.current_tab = "money"
        embed = self.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📦 Other", style=discord.ButtonStyle.secondary, custom_id="other")
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.current_tab = "other"
        embed = self.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class CartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="🛒 Checkout", style=discord.ButtonStyle.success, emoji="💳")
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your cart!", ephemeral=True)
            return

        cart_items = db.get_cart(self.user_id)
        if not cart_items:
            await interaction.response.send_message("❌ Your cart is empty!", ephemeral=True)
            return

        # Create order
        order_id = db.create_order(self.user_id, str(interaction.user))

        if not order_id:
            await interaction.response.send_message("❌ Failed to create order. Please check stock availability.", ephemeral=True)
            return

        order = db.get_order(order_id)

        embed = discord.Embed(
            title="✅ Order Successful!",
            description=f"Order #{order_id} has been created!",
            color=BotConfig.COLORS['success']
        )

        embed.add_field(name="Total Amount", value=f"${order['total_amount']:.2f}", inline=True)
        embed.add_field(name="Status", value="Pending", inline=True)
        embed.set_footer(text="Thank you for your purchase! Your order is being processed.")

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Clear Cart", style=discord.ButtonStyle.danger)
    async def clear_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your cart!", ephemeral=True)
            return

        success = db.clear_cart(self.user_id)
        if success:
            embed = discord.Embed(
                title="🗑️ Cart Cleared",
                description="Your cart has been cleared!",
                color=BotConfig.COLORS['info']
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("❌ Failed to clear cart!", ephemeral=True)

# === THE 3 MAIN COMMANDS ===

@bot.tree.command(name='shop', description='Browse the complete shop with organized tabs')
async def shop_command(interaction: discord.Interaction):
    """Display the interactive shop with tabs"""
    view = ShopView(interaction.user.id)
    embed = view.create_shop_embed()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='cart', description='Add a product to your cart')
@app_commands.describe(product_id='The ID of the product', quantity='Quantity to add (default: 1)')
async def cart_command(interaction: discord.Interaction, product_id: int, quantity: int = 1):
    """Add a product to your cart"""
    if quantity <= 0:
        await interaction.response.send_message("❌ Quantity must be greater than 0!", ephemeral=True)
        return

    product = db.get_product(product_id)
    if not product:
        await interaction.response.send_message("❌ Product not found!", ephemeral=True)
        return

    if product['stock'] < quantity:
        await interaction.response.send_message(f"❌ Not enough stock! Only {product['stock']} available.", ephemeral=True)
        return

    success = db.add_to_cart(interaction.user.id, product_id, quantity)
    if success:
        embed = discord.Embed(
            title="✅ Added to Cart",
            description=f"Added {quantity}x **{product['name']}** to your cart!",
            color=BotConfig.COLORS['success']
        )
        embed.add_field(name="Product", value=product['name'], inline=True)
        embed.add_field(name="Price Each", value=f"${product['price']:.2f}", inline=True)
        embed.add_field(name="Total Cost", value=f"${product['price'] * quantity:.2f}", inline=True)
        embed.set_footer(text="Use /viewcart to see your full cart")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Failed to add to cart. Please try again.", ephemeral=True)

@bot.tree.command(name='viewcart', description='View and manage your shopping cart')
async def view_cart_command(interaction: discord.Interaction):
    """View your shopping cart with management options"""
    cart_items = db.get_cart(interaction.user.id)

    if not cart_items:
        embed = discord.Embed(
            title="🛒 Your Cart",
            description="Your cart is empty! Use `/shop` to browse products.",
            color=BotConfig.COLORS['info']
        )
        embed.set_footer(text="Add items using /cart <product_id> <quantity>")
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="🛒 Your Shopping Cart",
        color=BotConfig.COLORS['cart']
    )

    total = 0
    items_text = ""

    for item in cart_items:
        total += item['total_price']
        items_text += f"• **{item['name']}** x{item['quantity']} - ${item['total_price']:.2f}\n"

    embed.add_field(name="📋 Cart Items", value=items_text, inline=False)
    embed.add_field(name="💰 Total Amount", value=f"**${total:.2f}**", inline=False)
    embed.set_footer(text="Use the buttons below to checkout or clear your cart")

    view = CartView(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

# Setup products command for admin (hidden from users)
@bot.tree.command(name='setup_shop', description='Setup the shop with default products (Admin only)')
async def setup_shop(interaction: discord.Interaction):
    """Setup shop with organized products"""
    try:
        # Basic admin check
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only command!", ephemeral=True)
            return

        # Respond immediately with a simple message
        await interaction.response.send_message("⏳ Setting up shop products...", ephemeral=True)

        # Weapons category
        weapons = [
            ("AK-47", "Powerful assault rifle", 15.00, 50),
            ("M4A1", "Tactical assault rifle", 18.00, 50),
            ("AWP Sniper", "High-damage sniper rifle", 25.00, 30),
            ("Desert Eagle", "Heavy pistol", 8.00, 75),
            ("MP5", "Submachine gun", 12.00, 60),
            ("Shotgun", "Close-range powerhouse", 10.00, 40)
        ]

        # Money category  
        money = [
            ("$100K Package", "Get 100,000 in-game money", 5.00, 999),
            ("$500K Package", "Get 500,000 in-game money", 20.00, 999),
            ("$1M Package", "Get 1,000,000 in-game money", 35.00, 999),
            ("Money Doubler", "Double your current money", 15.00, 50),
            ("Bank Heist", "Special money mission", 25.00, 20)
        ]

        # Other category
        other = [
            ("VIP Status", "Get VIP privileges", 30.00, 100),
            ("Custom Skin", "Personalized character skin", 12.00, 200),
            ("Rare Vehicle", "Exclusive vehicle access", 45.00, 25),
            ("Level Boost", "Instant level increase", 20.00, 75),
            ("Premium Bundle", "Complete starter pack", 60.00, 50)
        ]

        added_count = 0

        # Add weapons
        for name, desc, price, stock in weapons:
            if db.add_product(name, desc, price, stock, category="weapons"):
                added_count += 1

        # Add money packages
        for name, desc, price, stock in money:
            if db.add_product(name, desc, price, stock, category="money"):
                added_count += 1

        # Add other items
        for name, desc, price, stock in other:
            if db.add_product(name, desc, price, stock, category="other"):
                added_count += 1

        embed = discord.Embed(
            title="✅ Shop Setup Complete!",
            description=f"Successfully added {added_count} products to the shop!",
            color=BotConfig.COLORS['success']
        )

        embed.add_field(name="🔫 Weapons", value=f"{len(weapons)} items added", inline=True)
        embed.add_field(name="💰 Money", value=f"{len(money)} packages added", inline=True)
        embed.add_field(name="📦 Other", value=f"{len(other)} items added", inline=True)

        embed.set_footer(text="Shop is now ready for customers!")
        await interaction.edit_original_response(content=None, embed=embed)

    except discord.NotFound:
        logger.error("Interaction not found - this is a Discord API issue")
    except discord.HTTPException as e:
        logger.error(f"HTTP Exception in setup_shop: {e}")
    except Exception as e:
        logger.error(f"Error in setup_shop command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while setting up the shop.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ An error occurred while setting up the shop.")
        except:
            logger.error("Could not send error message")

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Slash command error: {error}")

    # Handle specific error types
    if isinstance(error, app_commands.CommandInvokeError):
        logger.error(f"Command {interaction.command.name if interaction.command else 'unknown'} failed: {error.original}")
        
        # Don't handle NotFound errors (Discord API issues)
        if isinstance(error.original, discord.NotFound):
            logger.error("Discord API NotFound error - interaction may have expired")
            return
    
    try:
        # Only respond if we haven't already responded and the interaction is still valid
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while processing your command.", ephemeral=True)
        else:
            # Use followup if we already responded (but don't use followup if interaction expired)
            try:
                await interaction.followup.send("❌ An error occurred while processing your command.", ephemeral=True)
            except discord.NotFound:
                logger.error("Could not send followup - interaction expired")
    except discord.NotFound:
        logger.error("Could not respond to interaction - it may have expired")
    except discord.HTTPException as e:
        logger.error(f"HTTP error when sending error message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when sending error message: {e}")

if __name__ == "__main__":
    try:
        bot.run(BotConfig.get_bot_token())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")