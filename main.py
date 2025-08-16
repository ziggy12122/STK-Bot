import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import datetime
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
        self.user_carts = {}  # Store user carts in memory

    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # Test database connection
        try:
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

# Payment methods data
PAYMENT_METHODS = {
    "zpofe": {
        "cashapp": "https://cash.app/$EthanCreel1",
        "qr_code": "https://i.imgur.com/ZQR7X8Y.png",  # You'll need to upload your QR code image
        "display_name": "Zpofe"
    },
    "drow": {
        "cashapp": None,  # Will be set by /setpayment command
        "qr_code": None,
        "display_name": "Drow"
    }
}

# Create bot instance
bot = ShopBot()

# Weapon data (removed THA BRONX GUNS as requested)
WEAPON_DATA = {
    "GoldenButton": {"name": "GoldenButton", "price": 0},
    "GreenSwitch": {"name": "GreenSwitch", "price": 0},
    "BlueTips/Switch": {"name": "BlueTips/Switch", "price": 0},
    "OrangeButton": {"name": "OrangeButton", "price": 0},
    "YellowButtonSwitch": {"name": "YellowButtonSwitch", "price": 0},
    "FullyARP": {"name": "FullyARP", "price": 0},
    "FullyDraco": {"name": "FullyDraco", "price": 0},
    "Fully-MicroAR": {"name": "Fully-MicroAR", "price": 0},
    "Cyanbutton": {"name": "Cyanbutton", "price": 0},
    "BinaryTrigger": {"name": "BinaryTrigger", "price": 0},
    "100RndTanG19": {"name": "100RndTanG19", "price": 0},
    "300ARG": {"name": "300ARG", "price": 0},
    "VP9Scope": {"name": "VP9Scope", "price": 0},
    "MasterPiece30": {"name": "MasterPiece30", "price": 0},
    "GSwitch": {"name": "GSwitch", "price": 0},
    "G17WittaButton": {"name": "G17WittaButton", "price": 0},
    "G19Switch": {"name": "G19Switch", "price": 0},
    "G20Switch": {"name": "G20Switch", "price": 0},
    "G21Switch": {"name": "G21Switch", "price": 0},
    "G22 Switch": {"name": "G22 Switch", "price": 0},
    "G23 Switch": {"name": "G23 Switch", "price": 0},
    "G40 Switch": {"name": "G40 Switch", "price": 0},
    "G42 Switch": {"name": "G42 Switch", "price": 0},
    "Fully-FN": {"name": "Fully-FN", "price": 0},
    "BinaryARP": {"name": "BinaryARP", "price": 0},
    "BinaryG17": {"name": "BinaryG17", "price": 0},
    "BinaryDraco": {"name": "BinaryDraco", "price": 0},
    "CustomAR9": {"name": "CustomAR9", "price": 0}
}

# Watch data
WATCH_DATA = {
    "Cartier": {"name": "Cartier", "price": 1},
    "BlueFaceCartier": {"name": "BlueFace Cartier", "price": 1},
    "WhiteRichardMillie": {"name": "White Richard Millie", "price": 1},
    "PinkRichard": {"name": "Pink Richard", "price": 1},
    "GreenRichard": {"name": "Green Richard", "price": 1},
    "RedRichard": {"name": "Red Richard", "price": 1},
    "BlueRichard": {"name": "Blue Richard", "price": 1},
    "BlackOutMillie": {"name": "BlackOut Millie", "price": 1},
    "Red AP": {"name": "Red AP", "price": 1},
    "AP Watch": {"name": "AP Watch", "price": 1},
    "Gold AP": {"name": "Gold AP", "price": 1},
    "Red AP Watch": {"name": "Red AP Watch", "price": 1},
    "CubanG AP": {"name": "CubanG AP", "price": 1},
    "CubanP AP": {"name": "CubanP AP", "price": 1},
    "CubanB AP": {"name": "CubanB AP", "price": 1},
    "Iced AP": {"name": "Iced AP", "price": 1}
}

# Multi-select dropdown for weapons
class WeaponSelect(discord.ui.Select):
    def __init__(self, selected_weapons=None):
        self.selected_weapons = selected_weapons or set()

        options = []
        for weapon_id, weapon_info in list(WEAPON_DATA.items())[:25]:  # Discord limit
            is_selected = weapon_id in self.selected_weapons
            label = f"✅ {weapon_info['name']}" if is_selected else weapon_info['name']
            options.append(discord.SelectOption(
                label=label,
                value=weapon_id,
                description="Selected" if is_selected else "Click to select"
            ))

        super().__init__(
            placeholder="Select weapons from our collection...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Toggle selection for each value
            for value in self.values:
                if value in self.selected_weapons:
                    self.selected_weapons.remove(value)
                else:
                    self.selected_weapons.add(value)

            # Update the view with new selections
            view = WeaponShopView(interaction.user.id, self.selected_weapons)
            embed = view.create_weapon_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in WeaponSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

# Watch select dropdown
class WatchSelect(discord.ui.Select):
    def __init__(self, selected_watch=None):
        self.selected_watch = selected_watch

        options = []
        for watch_id, watch_info in WATCH_DATA.items():
            is_selected = watch_id == self.selected_watch
            label = f"✅ {watch_info['name']}" if is_selected else watch_info['name']
            options.append(discord.SelectOption(
                label=label,
                value=watch_id,
                description=f"${watch_info['price']} - Selected" if is_selected else f"${watch_info['price']}"
            ))

        super().__init__(
            placeholder="Select a watch...",
            min_values=0,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            self.selected_watch = self.values[0] if self.values else None

            # Get the parent view and update cart
            view = interaction.message.view
            if hasattr(view, 'selected_watch'):
                view.selected_watch = self.selected_watch

            # Update embed and view
            embed = view.create_other_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in WatchSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

# Zpofe Hub select dropdown
class ZpofeHubSelect(discord.ui.Select):
    def __init__(self, selected_hub=None):
        self.selected_hub = selected_hub

        options = [
            discord.SelectOption(
                label="✅ 1 Month Key - $1" if selected_hub == "1month" else "1 Month Key - $1",
                value="1month",
                description="1 month access - Selected" if selected_hub == "1month" else "1 month access"
            ),
            discord.SelectOption(
                label="✅ 3 Month Key - $3" if selected_hub == "3month" else "3 Month Key - $3",
                value="3month",
                description="3 months access - Selected" if selected_hub == "3month" else "3 months access"
            ),
            discord.SelectOption(
                label="✅ Permanent Key - $5" if selected_hub == "perm" else "Permanent Key - $5",
                value="perm",
                description="Lifetime access - Selected" if selected_hub == "perm" else "Lifetime access"
            )
        ]

        super().__init__(
            placeholder="Select Zpofe Hub access...",
            min_values=0,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("🚧 **Zpofe Hub Coming Soon!** 🚧\nThis feature is not available for purchase yet, but you can preview the options.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in ZpofeHubSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

class WeaponShopView(discord.ui.View):
    def __init__(self, user_id, selected_weapons=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_weapons = selected_weapons or set()

        # Add the weapon select dropdown
        self.add_item(WeaponSelect(self.selected_weapons))

    def create_weapon_embed(self):
        embed = discord.Embed(
            title="🔫 STK WEAPONS",
            description="**STK ARMORY**\nSelect multiple weapons from our collection:\n**Fullys • Switches • Buttons • Binarys**",
            color=0x8B0000  # Dark red for STK branding
        )

        if self.selected_weapons:
            selected_list = []
            for weapon_id in self.selected_weapons:
                weapon_name = WEAPON_DATA[weapon_id]['name']
                selected_list.append(f"🔥 {weapon_name}")

            embed.add_field(
                name=f"✅ SELECTED WEAPONS ({len(self.selected_weapons)})",
                value="\n".join(selected_list) if selected_list else "None selected",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 NO WEAPONS SELECTED",
                value="Use the dropdown below to select weapons",
                inline=False
            )

        # Show pricing info
        embed.add_field(
            name="💰 PACKAGE PRICING",
            value="🔒 **FULL SAFE:** $3.00\n👜 **FULL BAG:** $2.00\n 🚛 **FULL TRUNK:** $1.00",
            inline=True
        )

        embed.add_field(
            name="🎮 SELLER CARDS",
            value="🔥 **Zpofe** - Services of all types\n💎 **Drow** - Services for THA BRONX 3",
            inline=True
        )

        embed.set_footer(text="STK Weapons • THA BRONX 3 • Select weapons then checkout")
        return embed

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.success, row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
                return

            if not self.selected_weapons:
                await interaction.response.send_message("❌ Please select at least one weapon first!", ephemeral=True)
                return

            # Add to cart
            if interaction.user.id not in bot.user_carts:
                bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

            bot.user_carts[interaction.user.id]["weapons"].update(self.selected_weapons)

            await interaction.response.send_message(f"✅ Added {len(self.selected_weapons)} weapon(s) to your cart!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in add_to_cart: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🗑️ CLEAR SELECTION', style=discord.ButtonStyle.danger, row=1)
    async def clear_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.selected_weapons.clear()
        view = WeaponShopView(interaction.user.id, self.selected_weapons)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class MoneyShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_money = None

    def create_money_embed(self):
        embed = discord.Embed(
            title="💰 STK CASH",
            description="**STK BANK**\n**Unlimited Cash Available** - Get your money fast!",
            color=0x006400  # Dark green for money
        )

        embed.add_field(
            name="💵 UNLIMITED CASH PACKAGES",
            value="💰 **990K Cash** - $1.00\n 🏦 **990K Bank Extension** - $1.00\n💳 **1.6M (More Wallet Gamepass)** - $2.00",
            inline=False
        )

        embed.add_field(
            name="📋 INSTRUCTIONS",
            value="1️⃣ Go to the **Black Market**\n2️⃣ Put your **phone/drill** up for 990k or 1.6m\n3️⃣ **Zpofe** or **Drow** will buy it for that amount",
            inline=False
        )

        if self.selected_money:
            embed.add_field(
                name="✅ SELECTED",
                value=self.selected_money,
                inline=True
            )

        embed.add_field(
            name="🎮 SELLER CARDS",
            value="🔥 **Zpofe** - Services of all types\n💎 **Drow** - Services for THA BRONX 3",
            inline=True
        )

        embed.set_footer(text="STK Cash • THA BRONX 3 • Unlimited cash delivery")
        return embed

    @discord.ui.button(label='💰 990K CASH - $1', style=discord.ButtonStyle.success, row=1)
    async def select_990k(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.selected_money = "990K Cash - $1"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='🏦 990K BANK - $1', style=discord.ButtonStyle.success, row=1)
    async def select_990k_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.selected_money = "990K Bank Extension - $1"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='💳 1.6M WALLET - $2', style=discord.ButtonStyle.success, row=1)
    async def select_1_6m(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        self.selected_money = "1.6M More Wallet - $2"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.primary, row=2)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        if not self.selected_money:
            await interaction.response.send_message("❌ Please select a money package first!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

        bot.user_carts[interaction.user.id]["money"] = self.selected_money
        await interaction.response.send_message(f"✅ Added {self.selected_money} to your cart!", ephemeral=True)

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=2)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class OtherShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_watch = None
        self.selected_hub = None

        # Add dropdowns
        self.add_item(WatchSelect(self.selected_watch))
        self.add_item(ZpofeHubSelect(self.selected_hub))

    def create_other_embed(self):
        embed = discord.Embed(
            title="📦 STK OTHER",
            description="**STK EXTRAS**\n**Watches • Scripts • Ext**\nPremium accessories & tools!",
            color=0x4B0082  # Dark purple
        )

        # Watches section
        embed.add_field(
            name="⌚ LUXURY WATCHES",
            value="**All Watches:** $1.00 each\nSelect from the dropdown below",
            inline=False
        )

        if self.selected_watch:
            watch_info = WATCH_DATA[self.selected_watch]
            embed.add_field(
                name="✅ SELECTED WATCH",
                value=f"⌚ {watch_info['name']} - ${watch_info['price']}",
                inline=True
            )

        # Zpofe Hub section
        embed.add_field(
            name="💻 ZPOFE HUB (COMING SOON)",
            value="🔥 All of Zpofe's Scripts in One Place!\n\n💎 **Permanent Key** - $5.00\n📅 **3 Month Key** - $3.00\n🗓️ **1 Month Key** - $1.00",
            inline=False
        )

        embed.add_field(
            name="🎮 SELLER CARDS",
            value="🔥 **Zpofe** - Services of all types\n💎 **Drow** - Services for THA BRONX 3",
            inline=True
        )

        return embed

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.success, row=2)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        if not self.selected_watch and not self.selected_hub:
            await interaction.response.send_message("❌ Please select an item first!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

        added_items = []
        if self.selected_watch:
            # Ensure selected_watch is added to the 'watches' set
            if self.selected_watch not in bot.user_carts[interaction.user.id]["watches"]:
                bot.user_carts[interaction.user.id]["watches"].add(self.selected_watch)
                added_items.append(f"Watch: {WATCH_DATA[self.selected_watch]['name']}")

        if self.selected_hub:
            bot.user_carts[interaction.user.id]["hub"] = self.selected_hub
            added_items.append(f"Zpofe Hub: {self.selected_hub}")

        if added_items:
            await interaction.response.send_message(f"✅ Added to cart:\n" + "\n".join(added_items), ephemeral=True)
        else:
            await interaction.response.send_message("Nothing new to add to the cart.", ephemeral=True)


    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=2)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class InfoView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_info_embed(self):
        embed = discord.Embed(
            title="ℹ️ STK SHOP - INFO",
            description="**THA BRONX 3 HEADQUARTERS**\nYour trusted street suppliers since day one!",
            color=0x1E90FF  # Blue
        )

        embed.add_field(
            name="🎮 SELLER CARDS",
            value="🔥 **Zpofe** - Services of all types\n💎 **Drow** - Services for THA BRONX 3\n\n*Trusted, reliable, fast delivery*",
            inline=False
        )

        embed.add_field(
            name="🔥 AVAILABLE NOW",
            value="💻 **THA BRONX 3 Services** are the only ones available for purchase right now\n🎮 **All other services coming soon**",
            inline=False
        )

        embed.add_field(
            name="🏆 STK SERVICES",
            value="✅ **Premium Quality**\n✅ **Fast Delivery**\n✅ **24/7 Support**\n✅ **Secure Transactions**",
            inline=True
        )

        embed.add_field(
            name="📞 LOCATIONS",
            value="🏙️ **THA BRONX 3** (Active)\n\n*Expanding to new territories soon*",
            inline=True
        )

        embed.set_footer(text="STK Services • THA BRONX 3 • Est. 2024")
        return embed

    @discord.ui.button(label='📞 SUPPORT', style=discord.ButtonStyle.primary, row=1)
    async def contact_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📞 **SUPPORT CONTACT**\n\nFor support, please DM **Zpofe** directly.\n\n*Response time: Usually within a few hours*", ephemeral=True)

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class CartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_cart_embed(self):
        embed = discord.Embed(
            title="🛒 STK SHOP - CART",
            description="**YOUR THA BRONX 3 ORDER**\nReview your items before checkout:",
            color=0xFF6347  # Orange-red
        )

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": None, "watches": set(), "hub": None})
        total = 0
        items = []

        # Weapons
        if cart["weapons"]:
            items.append(f"🔫 **WEAPONS** ({len(cart['weapons'])})")
            for weapon_id in cart["weapons"]:
                items.append(f"  • {WEAPON_DATA[weapon_id]['name']}")
            items.append("  💰 *Price: Choose package at checkout*")

        # Money
        if cart["money"]:
            items.append(f"💰 **MONEY**")
            items.append(f"  • {cart['money']}")
            if "1.6M" in cart["money"]:
                total += 2
            else:
                total += 1

        # Watches
        if cart["watches"]:
            items.append(f"⌚ **WATCHES** ({len(cart['watches'])})")
            for watch_id in cart["watches"]:
                watch_info = WATCH_DATA[watch_id]
                items.append(f"  • {watch_info['name']}")
                total += watch_info["price"]

        # Hub (coming soon)
        if cart["hub"]:
            items.append(f"💻 **ZPOFE HUB** (Coming Soon)")
            hub_prices = {"1month": 1, "3month": 3, "perm": 5}
            items.append(f"  • {cart['hub']} Key")
            items.append(f"  • *Not available for purchase yet*")

        if not items:
            embed.add_field(
                name="🛒 EMPTY CART",
                value="Your cart is empty! Go back to shop and add some items.",
                inline=False
            )
        else:
            embed.add_field(
                name="📦 CART ITEMS",
                value="\n".join(items),
                inline=False
            )

            if total > 0:
                embed.add_field(
                    name="💰 ESTIMATED TOTAL",
                    value=f"**${total:.2f}**\n*(Weapons pricing determined at checkout)*",
                    inline=True
                )

        embed.add_field(
            name="🎮 SELLER CARDS",
            value="🔥 **Zpofe** - Services of all types\n💎 **Drow** - Services for THA BRONX 3",
            inline=True
        )

        embed.set_footer(text="STK Services • THA BRONX 3 • Secure checkout")
        return embed

    @discord.ui.button(label='💳 CHECKOUT', style=discord.ButtonStyle.success, row=1)
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your cart!", ephemeral=True)
            return

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": None, "watches": set(), "hub": None})

        if not any([cart["weapons"], cart["money"], cart["watches"]]):  # Don't count hub since it's not available
            await interaction.response.send_message("❌ Your cart is empty!", ephemeral=True)
            return

        try:
            ticket_channel = await create_purchase_ticket(interaction, cart)
            if ticket_channel:
                await interaction.response.send_message(f"✅ **Purchase ticket created!**\n\nYour order ticket: {ticket_channel.mention}\n\nZpofe and Drow have been notified and will assist you shortly!", ephemeral=True)

                # Clear cart after successful ticket creation
                bot.user_carts[self.user_id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}
            else:
                await interaction.response.send_message("❌ Unable to create ticket. Please contact an admin.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message("❌ An error occurred while creating your ticket.", ephemeral=True)

    @discord.ui.button(label='🗑️ CLEAR CART', style=discord.ButtonStyle.danger, row=1)
    async def clear_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your cart!", ephemeral=True)
            return

        bot.user_carts[self.user_id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}
        embed = self.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Main STK Shop View
class STKShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_shop_embed(self):
        embed = discord.Embed(
            title="🔥 STK PREMIUM SERVICES",
            description="**🏴‍☠️ WELCOME TO THA BRONX 3 HEADQUARTERS 🏴‍☠️**\n\n*Where legends shop for legendary items*\n\n**👑 PREMIUM QUALITY** • **⚡ INSTANT DELIVERY** • **🔒 SECURE TRANSACTIONS**\n\n*Your trusted street suppliers since day one*\n\n**Choose your category below to start shopping:**",
            color=0x8B0000  # Dark red for STK branding
        )

        # Add STK SHOP header image
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a11fe6&is=689fce66&hm=c6993267511d0fbfe32bf615f5a205279510c9091caa9f217860f1dd9e106ff0&")  # STK SHOP header GIF
        # Add BEST PRICES footer as thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a11fe6&is=689fce66&hm=3d7e0b292626bab621f3dde0fd5a0377f52a31cc9fc81fddcde8db437de66edd&")  # STK SHOP thumbnail GIF

        embed.add_field(
            name="🔫 WEAPONS ARMORY",
            value="**🏴‍☠️ Premium Street Arsenal**\n\n*Fullys • Switches • Buttons • Binarys*\n\n**Package deals from $1-$3**\n*Glock series, AR platform, premium switches*\n\n⚡ **Most Popular Category**",
            inline=True
        )

        embed.add_field(
            name="💰 FINANCIAL SERVICES",
            value="**💸 Unlimited Cash Flow**\n\n*Instant wealth delivery system*\n\n**Packages from $1-$2**\n*990K cash, bank extensions, wallet boosts*\n\n🚀 **Lightning Fast Delivery**",
            inline=True
        )

        embed.add_field(
            name="📦 LUXURY COLLECTION",
            value="**💎 Premium Accessories**\n\n*Watches • Scripts • Exclusive Tools*\n\n**Starting at $1 each**\n*Cartier, Richard Mille, AP watches*\n\n✨ **Status Symbols**",
            inline=True
        )

        embed.add_field(
            name="👑 YOUR ELITE SUPPLIERS",
            value="🔥 **ZPOFE** - *The Mastermind*\n• All services specialist • 3+ years experience\n• Script developer & premium trader\n• 24/7 support • Thousands of customers\n\n💎 **DROW** - *The Specialist*\n• THA BRONX 3 expert • Luxury curator\n• Lightning delivery • Professional service\n• Quality guaranteed • Premium focus",
            inline=False
        )

        embed.add_field(
            name="🏆 WHY CHOOSE STK?",
            value="✅ **5000+** Happy customers\n✅ **2-5 min** Average delivery time\n✅ **99.9%** Success rate\n✅ **24/7** Support availability\n✅ **100%** Satisfaction guarantee\n✅ **Secure** Payment processing",
            inline=True
        )

        embed.add_field(
            name="⚡ GETTING STARTED",
            value="🎯 **Browse** categories above\n🛒 **Add** items to your cart\n💳 **Checkout** securely\n📞 **Support** ticket created\n⚡ **Delivery** in minutes\n\n*Professional service guaranteed*",
            inline=True
        )

        embed.set_footer(text="STK Premium Services • THA BRONX 3 Headquarters • Est. 2024 • Where Legends Shop")
        return embed

    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = WeaponShopView(interaction.user.id)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = MoneyShopView(interaction.user.id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 OTHER', style=discord.ButtonStyle.secondary, row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = OtherShopView(interaction.user.id)
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = InfoView(interaction.user.id)
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = CartView(interaction.user.id)
        embed = view.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# New class for persistent shop view
class PersistentSTKShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # No timeout for persistent views

    def create_shop_embed(self):
        embed = discord.Embed(
            title="🔥 STK PREMIUM SERVICES",
            description="**🏴‍☠️ WELCOME TO THA BRONX 3 HEADQUARTERS 🏴‍☠️**\n\n*Where legends shop for legendary items*\n\n**👑 PREMIUM QUALITY** • **⚡ INSTANT DELIVERY** • **🔒 SECURE TRANSACTIONS**\n\n*Your trusted street suppliers since day one*\n\n**Choose your category below to start shopping:**",
            color=0x8B0000  # Dark red for STK branding
        )

        # Add STK SHOP header image
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a11fe6&is=689fce66&hm=c6993267511d0fbfe32bf615f5a205279510c9091caa9f217860f1dd9e106ff0&")  # STK SHOP header GIF
        # Add BEST PRICES footer as thumbnail
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a11fe6&is=689fce66&hm=3d7e0b292626bab621f3dde0fd5a0377f52a31cc9fc81fddcde8db437de66edd&")  # STK SHOP thumbnail GIF

        embed.add_field(
            name="🔫 WEAPONS ARMORY",
            value="**🏴‍☠️ Premium Street Arsenal**\n\n*Fullys • Switches • Buttons • Binarys*\n\n**Package deals from $1-$3**\n*Glock series, AR platform, premium switches*\n\n⚡ **Most Popular Category**",
            inline=True
        )

        embed.add_field(
            name="💰 FINANCIAL SERVICES",
            value="**💸 Unlimited Cash Flow**\n\n*Instant wealth delivery system*\n\n**Packages from $1-$2**\n*990K cash, bank extensions, wallet boosts*\n\n🚀 **Lightning Fast Delivery**",
            inline=True
        )

        embed.add_field(
            name="📦 LUXURY COLLECTION",
            value="**💎 Premium Accessories**\n\n*Watches • Scripts • Exclusive Tools*\n\n**Starting at $1 each**\n*Cartier, Richard Mille, AP watches*\n\n✨ **Status Symbols**",
            inline=True
        )

        embed.add_field(
            name="👑 YOUR ELITE SUPPLIERS",
            value="🔥 **ZPOFE** - *The Mastermind*\n• All services specialist • 3+ years experience\n• Script developer & premium trader\n• 24/7 support • Thousands of customers\n\n💎 **DROW** - *The Specialist*\n• THA BRONX 3 expert • Luxury curator\n• Lightning delivery • Professional service\n• Quality guaranteed • Premium focus",
            inline=False
        )

        embed.add_field(
            name="🏆 WHY CHOOSE STK?",
            value="✅ **5000+** Happy customers\n✅ **2-5 min** Average delivery time\n✅ **99.9%** Success rate\n✅ **24/7** Support availability\n✅ **100%** Satisfaction guarantee\n✅ **Secure** Payment processing",
            inline=True
        )

        embed.add_field(
            name="⚡ GETTING STARTED",
            value="🎯 **Browse** categories above\n🛒 **Add** items to your cart\n💳 **Checkout** securely\n📞 **Support** ticket created\n⚡ **Delivery** in minutes\n\n*Professional service guaranteed*",
            inline=True
        )

        embed.set_footer(text="STK Premium Services • THA BRONX 3 Headquarters • Est. 2024 • Where Legends Shop")
        return embed

    # These button callbacks will redirect to the appropriate view for any user
    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WeaponShopView(interaction.user.id) # Pass the current user's ID
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MoneyShopView(interaction.user.id) # Pass the current user's ID
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 OTHER', style=discord.ButtonStyle.secondary, row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OtherShopView(interaction.user.id) # Pass the current user's ID
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = InfoView(interaction.user.id) # Pass the current user's ID
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CartView(interaction.user.id) # Pass the current user's ID
        embed = view.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=view)


async def create_purchase_ticket(interaction: discord.Interaction, cart):
    """Create a ticket channel for purchase processing"""
    guild = interaction.guild
    if not guild:
        return None

    # Create ticket category if it doesn't exist
    category = discord.utils.get(guild.categories, name="🎫・TICKETS")
    if not category:
        try:
            category = await guild.create_category("🎫・TICKETS")
        except discord.Forbidden:
            logger.error("No permission to create category")
            return None

    # Create ticket channel
    ticket_name = f"ticket-{interaction.user.name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"

    # Set permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # Add admin role permissions if configured
    if BotConfig.ADMIN_ROLE_ID:
        admin_role = guild.get_role(BotConfig.ADMIN_ROLE_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        ticket_channel = await guild.create_text_channel(
            ticket_name,
            category=category,
            overwrites=overwrites,
            topic=f"Purchase ticket for {interaction.user.display_name}"
        )

        # Send ticket embed
        await send_ticket_embed(ticket_channel, interaction.user, cart)

        return ticket_channel

    except discord.Forbidden:
        logger.error("No permission to create ticket channel")
        return None

async def send_ticket_embed(channel, user, cart):
    """Send the purchase ticket embed with payment information"""

    # Calculate total and create items list
    total = 0
    items_list = []

    # Process cart items
    if cart["weapons"]:
        items_list.append(f"🔫 **WEAPONS** ({len(cart['weapons'])})")
        for weapon_id in cart["weapons"]:
            items_list.append(f"  • {WEAPON_DATA[weapon_id]['name']}")
        items_list.append("  💰 *Price: Package deal pricing*")

    if cart["money"]:
        items_list.append(f"💰 **MONEY**")
        items_list.append(f"  • {cart['money']}")
        if "1.6M" in cart["money"]:
            total += 2
        else:
            total += 1

    if cart["watches"]:
        items_list.append(f"⌚ **WATCHES** ({len(cart['watches'])})")
        for watch_id in cart["watches"]:
            watch_info = WATCH_DATA[watch_id]
            items_list.append(f"  • {watch_info['name']} - ${watch_info['price']}")
            total += watch_info["price"]

    # Create main purchase embed
    embed = discord.Embed(
        title="🎉 Thank you for your STK purchase!",
        description="**Your order is being processed**\n\nZpofe or Drow will be with you shortly. They have been notified!",
        color=0x00ff00,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(
        name="👤 Customer",
        value=f"{user.mention}\n`{user.id}`",
        inline=True
    )

    embed.add_field(
        name="💰 Estimated Total",
        value=f"${total:.2f}" if total > 0 else "TBD",
        inline=True
    )

    embed.add_field(
        name="⏰ Order Time",
        value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>",
        inline=True
    )

    embed.add_field(
        name="🛍️ Order Details",
        value="\n".join(items_list) if items_list else "No items",
        inline=False
    )

    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="STK Services • Professional Service", icon_url=channel.guild.me.display_avatar.url)

    await channel.send(embed=embed)

    # Send payment embed
    payment_embed = discord.Embed(
        title="💳 Payment Information",
        description="**Choose your payment method below:**",
        color=0x00ff00
    )

    # Zpofe's payment info
    if PAYMENT_METHODS["zpofe"]["cashapp"]:
        payment_embed.add_field(
            name="🔥 Zpofe's CashApp",
            value=f"[Click here to pay Zpofe]({PAYMENT_METHODS['zpofe']['cashapp']})\n`{PAYMENT_METHODS['zpofe']['cashapp']}`",
            inline=False
        )

    # Drow's payment info
    if PAYMENT_METHODS["drow"]["cashapp"]:
        payment_embed.add_field(
            name="💎 Drow's Payment",
            value=f"[Click here to pay Drow]({PAYMENT_METHODS['drow']['cashapp']})\n`{PAYMENT_METHODS['drow']['cashapp']}`",
            inline=False
        )
    else:
        payment_embed.add_field(
            name="💎 Drow's Payment",
            value="*Payment method not set*",
            inline=False
        )

    payment_embed.add_field(
        name="📱 Instructions",
        value="1️⃣ Choose your preferred seller\n2️⃣ Send payment using the link above\n3️⃣ Send a screenshot of payment confirmation\n4️⃣ Wait for your items to be delivered!",
        inline=False
    )

    payment_embed.set_footer(text="STK Services • Secure Payment Processing")

    # Add QR code image if available for Zpofe
    if PAYMENT_METHODS["zpofe"]["qr_code"]:
        payment_embed.set_image(url=PAYMENT_METHODS["zpofe"]["qr_code"])

    await channel.send(embed=payment_embed)

    # Ping sellers
    ping_message = "🔔 **New Purchase Alert!**\n\n"

    # Ping Zpofe (you) - replace with your user ID
    zpofe_id = 1399949855799119952  # Replace with Zpofe's actual user ID
    ping_message += f"🔥 <@{zpofe_id}> (Zpofe)\n"

    # Ping Drow if admin role is set, or replace with Drow's user ID
    if BotConfig.ADMIN_ROLE_ID:
        ping_message += f"💎 <@&{BotConfig.ADMIN_ROLE_ID}> (Drow)"
    else:
        drow_id = 123456789  # Replace with Drow's actual user ID when available
        ping_message += f"💎 <@{drow_id}> (Drow)"

    ping_message += "\n\n**A customer is ready to purchase! Please assist them promptly.**"

    await channel.send(ping_message)

    # Add ticket management buttons
    view = TicketManagementView()
    management_embed = discord.Embed(
        title="🛠️ Ticket Management",
        description="**Admin Controls**",
        color=0x9b59b6
    )
    management_embed.add_field(
        name="🔒 Close Ticket",
        value="Close this ticket and delete the channel",
        inline=True
    )
    management_embed.add_field(
        name="✅ Mark Completed",
        value="Mark the order as completed",
        inline=True
    )

    await channel.send(embed=management_embed, view=view)

# Slash Commands
@bot.tree.command(name="setup", description="Setup the STK Shop interface for everyone to use")
async def setup_shop(interaction: discord.Interaction):
    """Setup the STK Shop interface - Creates a persistent shop that everyone can interact with"""
    try:
        # Check if user has admin permissions
        has_permission = False
        if interaction.user.guild_permissions.manage_channels:
            has_permission = True
        elif BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission or Admin role to setup the shop.", ephemeral=True)
            return

        # Respond immediately to avoid timeout
        await interaction.response.send_message("🔄 Setting up STK Shop...", ephemeral=True)

        view = PersistentSTKShopView() # Use the persistent view
        embed = view.create_shop_embed()

        # Add setup success message to embed
        embed.add_field(
            name="🚀 SHOP SETUP COMPLETE",
            value="✅ Shop is now live and ready for customers!\n🔄 Interface stays active 24/7\n👥 Everyone can interact with it",
            inline=False
        )

        # Send the shop interface publicly so everyone can use it
        await interaction.channel.send(embed=embed, view=view)

        # Update the original response with success message
        await interaction.edit_original_response(content="✅ **STK Shop has been successfully setup!** The shop interface is now live and available for all customers to use 24/7.")

    except discord.NotFound:
        logger.error("Interaction expired - Discord API issue")
    except Exception as e:
        logger.error(f"Error in setup_shop command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while setting up the shop.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ An error occurred while setting up the shop.")
        except discord.NotFound:
            logger.error("Could not send error message - interaction expired")
        except Exception as edit_error:
            logger.error(f"Could not edit response: {edit_error}")

@bot.tree.command(name="clear", description="Delete bot messages from this channel")
@app_commands.describe(
    amount="Number of bot messages to delete (default: 10, max: 100)"
)
async def clear_messages(interaction: discord.Interaction, amount: int = 10):
    """Delete bot messages from the current channel"""
    try:
        # Limit the amount to prevent abuse
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1

        # Check if user has manage messages permission or admin role
        has_permission = False
        if interaction.user.guild_permissions.manage_messages:
            has_permission = True
        elif BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need 'Manage Messages' permission or Admin role to use this command.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Clearing up to {amount} bot messages...", ephemeral=True)

        # Get messages from the channel
        messages_deleted = 0
        async for message in interaction.channel.history(limit=500):  # Check last 500 messages
            if messages_deleted >= amount:
                break

            # Only delete messages from this bot
            if message.author == bot.user:
                try:
                    await message.delete()
                    messages_deleted += 1
                    await asyncio.sleep(0.5)  # Rate limit protection
                except discord.errors.NotFound:
                    # Message was already deleted
                    continue
                except discord.errors.Forbidden:
                    # Bot doesn't have permission to delete this message
                    continue

        # Send confirmation
        if messages_deleted > 0:
            await interaction.followup.send(f"✅ Successfully deleted {messages_deleted} bot message(s).", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ No bot messages found to delete.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in clear command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while clearing messages.", ephemeral=True)
        else:
            await interaction.followup.send("❌ An error occurred while clearing messages.", ephemeral=True)

@bot.tree.command(name="addproduct", description="Add a new product (Admin only)")
@app_commands.describe(
    name="Product name",
    price="Product price",
    stock="Initial stock quantity",
    description="Product description",
    category="Product category"
)
async def add_product(interaction: discord.Interaction, name: str, price: float, stock: int,
                     description: str = None, category: str = "general"):
    """Add a new product (Admin only)"""
    try:
        # Check admin permissions
        if BotConfig.ADMIN_ROLE_ID:
            if not any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                return

        product_id = bot.db.add_product(name, description, price, stock, None, category)

        if product_id:
            embed = discord.Embed(
                title="✅ Product Added",
                description=f"Successfully added **{name}** to the shop!",
                color=BotConfig.COLORS['success']
            )
            embed.add_field(name="🆔 Product ID", value=str(product_id), inline=True)
            embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
            embed.add_field(name="📦 Stock", value=str(stock), inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to add product.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in add_product command: {e}")
        await interaction.response.send_message("❌ An error occurred while adding the product.", ephemeral=True)

@bot.tree.command(name="setpayment", description="Set payment method for Drow (Drow only)")
@app_commands.describe(
    cashapp_link="CashApp link (e.g., https://cash.app/$username)",
    qr_code_url="QR code image URL (optional)"
)
async def set_payment(interaction: discord.Interaction, cashapp_link: str, qr_code_url: str = None):
    """Set payment method for Drow"""
    try:
        # Check if user is Drow (admin role) or has admin permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.administrator:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only Drow can use this command.", ephemeral=True)
            return

        # Validate cashapp link
        if not cashapp_link.startswith(("https://cash.app/", "http://cash.app/")):
            await interaction.response.send_message("❌ Please provide a valid CashApp link (e.g., https://cash.app/$username)", ephemeral=True)
            return

        # Update payment methods
        PAYMENT_METHODS["drow"]["cashapp"] = cashapp_link
        if qr_code_url:
            PAYMENT_METHODS["drow"]["qr_code"] = qr_code_url

        embed = discord.Embed(
            title="✅ Payment Method Updated",
            description="Drow's payment method has been successfully updated!",
            color=BotConfig.COLORS['success']
        )
        embed.add_field(name="💳 CashApp Link", value=cashapp_link, inline=False)
        if qr_code_url:
            embed.add_field(name="📱 QR Code", value="QR code image updated", inline=False)
            embed.set_image(url=qr_code_url)

        embed.set_footer(text="Payment method active for all new tickets")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in set_payment command: {e}")
        await interaction.response.send_message("❌ An error occurred while updating payment method.", ephemeral=True)

# Ticket management view
class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Close Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has admin permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only admins can close tickets.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="This ticket has been closed. Thank you for your purchase!",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="STK Services • Ticket System")

        await interaction.response.send_message(embed=embed)

        # Wait a moment then delete the channel
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket closed by admin")
        except:
            pass

    @discord.ui.button(label='✅ Mark Completed', style=discord.ButtonStyle.success, custom_id='mark_completed')
    async def mark_completed(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has admin permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only admins can mark tickets as completed.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Order Completed",
            description="**This order has been successfully completed!**\n\nThank you for choosing STK Services. We hope you enjoy your purchase!",
            color=0x00ff00,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="📞 Support",
            value="If you have any issues, feel free to contact us again!",
            inline=False
        )
        embed.set_footer(text="STK Services • Order Fulfillment")

        await interaction.response.send_message(embed=embed)

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Command error: {error}")

    # Handle specific error types
    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        logger.error(f"Command {interaction.command.name if interaction.command else 'unknown'} failed: {original_error}")

        # Don't handle NotFound errors (Discord API issues)
        if isinstance(original_error, discord.NotFound):
            logger.error("Discord API NotFound error - interaction may have expired")
            return

    try:
        # Only respond if we haven't already responded and the interaction is still valid
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while processing your command.", ephemeral=True)
        else:
            # Use followup if we already responded
            try:
                await interaction.followup.send("❌ An error occurred while processing your command.", ephemeral=True)
            except discord.NotFound:
                logger.error("Could not send followup - interaction expired")
    except discord.NotFound:
        logger.error("Could not respond to interaction - it may have expired")
    except discord.HTTPException as e:
        logger.error(f"HTTP error when sending error message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in error handler: {e}")

if __name__ == "__main__":
    try:
        # Add HTTP server for Koyeb health checks
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import os

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'STK Discord Bot is running')

            def log_message(self, format, *args):
                pass  # Suppress HTTP server logs

        # Start HTTP server for health checks
        port = int(os.getenv('PORT', 5000))
        ports_to_try = [port, 5001, 5002, 5003, 8080]

        server_started = False
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), HealthHandler)
                server_thread = threading.Thread(target=server.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                logger.info(f"Health check server started on port {try_port}")
                server_started = True
                break
            except OSError as e:
                logger.debug(f"Port {try_port} unavailable: {e}")
                continue

        if not server_started:
            logger.warning("Could not start health check server on any available port")
            # Continue without health check server

        # Start Discord bot
        bot.run(BotConfig.get_bot_token())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print("❌ Bot failed to start. Check your configuration and try again.")