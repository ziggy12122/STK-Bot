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
        self.selected_watch = self.values[0] if self.values else None

        # Get the parent view and update cart
        view = interaction.message.view
        if hasattr(view, 'selected_watch'):
            view.selected_watch = self.selected_watch

        # Update embed and view
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

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
        await interaction.response.send_message("🚧 **Zpofe Hub Coming Soon!** 🚧\nThis feature is not available for purchase yet, but you can preview the options.", ephemeral=True)

class WeaponShopView(discord.ui.View):
    def __init__(self, user_id, selected_weapons=None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_weapons = selected_weapons or set()

        # Add the weapon select dropdown
        self.add_item(WeaponSelect(self.selected_weapons))

    def create_weapon_embed(self):
        embed = discord.Embed(
            title="🔫 STK SHOP - WEAPONS",
            description="**SOUTH BRONX ARMORY**\nSelect multiple weapons from our street collection:",
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
            value="🔒 **FULL SAFE:** $3.00\n👜 **FULL BAG:** $2.00\n🚛 **FULL TRUNK:** $1.00",
            inline=True
        )

        embed.add_field(
            name="🏪 SELLERS",
            value="👤 **Zpofe**\n👤 **Drow**",
            inline=True
        )

        embed.set_footer(text="STK Services • South Bronx • Select weapons then checkout")
        return embed

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.success, row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = STKShopView(interaction.user.id)
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
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_money = None

    def create_money_embed(self):
        embed = discord.Embed(
            title="💰 STK SHOP - MONEY",
            description="**SOUTH BRONX BANK**\nGet your cash quick and easy!",
            color=0x006400  # Dark green for money
        )

        embed.add_field(
            name="💵 MONEY PACKAGES",
            value="💰 **990K Cash** - $1.00\n🏦 **990K Bank Extension** - $1.00\n💳 **1.6M (More Wallet Gamepass)** - $2.00",
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
            name="🏪 SELLERS",
            value="👤 **Zpofe**\n👤 **Drow**",
            inline=True
        )

        embed.set_footer(text="STK Services • South Bronx • Fast money delivery")
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
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = STKShopView(interaction.user.id)
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class OtherShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_watch = None
        self.selected_hub = None

        # Add dropdowns
        self.add_item(WatchSelect(self.selected_watch))
        self.add_item(ZpofeHubSelect(self.selected_hub))

    def create_other_embed(self):
        embed = discord.Embed(
            title="📦 STK SHOP - OTHER",
            description="**SOUTH BRONX EXTRAS**\nWatches, Scripts & More!",
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
            name="🏪 SELLERS",
            value="👤 **Zpofe**\n👤 **Drow**",
            inline=True
        )

        embed.set_footer(text="STK Services • South Bronx • Premium extras")
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
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = STKShopView(interaction.user.id)
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class InfoView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    def create_info_embed(self):
        embed = discord.Embed(
            title="ℹ️ STK SHOP - INFO",
            description="**SOUTH BRONX HEADQUARTERS**\nYour trusted street suppliers since day one!",
            color=0x1E90FF  # Blue
        )

        embed.add_field(
            name="👥 OUR SELLERS",
            value="🔥 **Zpofe** - Lead Supplier\n🔥 **Drow** - Senior Supplier\n\n*Trusted, reliable, fast delivery*",
            inline=False
        )

        embed.add_field(
            name="🚧 COMING SOON",
            value="💻 **Zpofe Hub Script Collection**\n🎮 **New Game Support**",
            inline=False
        )

        embed.add_field(
            name="🏆 STK SERVICES",
            value="✅ **Premium Quality**\n✅ **Fast Delivery**\n✅ **24/7 Support**\n✅ **Secure Transactions**",
            inline=True
        )

        embed.add_field(
            name="📞 LOCATIONS",
            value="🏙️ **South Bronx** (Active)\n\n*Expanding to new territories soon*",
            inline=True
        )

        embed.set_footer(text="STK Services • South Bronx • Est. 2024")
        return embed

    @discord.ui.button(label='📞 SUPPORT', style=discord.ButtonStyle.primary, row=1)
    async def contact_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📞 **SUPPORT CONTACT**\n\nFor support, please DM **Zpofe** directly.\n\n*Response time: Usually within a few hours*", ephemeral=True)

    @discord.ui.button(label='◀️ BACK TO SHOP', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return

        view = STKShopView(interaction.user.id)
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class CartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    def create_cart_embed(self):
        embed = discord.Embed(
            title="🛒 STK SHOP - CART",
            description="**YOUR SOUTH BRONX ORDER**\nReview your items before checkout:",
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
            name="🏪 SELLERS",
            value="👤 **Zpofe**\n👤 **Drow**",
            inline=True
        )

        embed.set_footer(text="STK Services • South Bronx • Secure checkout")
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

        # For now, just show a checkout message
        await interaction.response.send_message("🚧 **CHECKOUT COMING SOON!**\n\nFull checkout system will be available soon. For now, contact **Zpofe** or **Drow** directly with your order.", ephemeral=True)

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
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your cart!", ephemeral=True)
            return

        view = STKShopView(interaction.user.id)
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Main STK Shop View
class STKShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    def create_shop_embed(self):
        embed = discord.Embed(
            title="🔥 STK SHOP",
            description="**WELCOME TO STK SHOP**\n*Your trusted street suppliers - Zpofe & Drow*\n\nChoose your category below:",
            color=0x8B0000  # Dark red for STK branding
        )

        embed.add_field(
            name="🔫 WEAPONS",
            value="Premium switches, triggers & more\n*Package deals available*",
            inline=True
        )

        embed.add_field(
            name="💰 MONEY",
            value="Fast cash & bank extensions\n*990K - 1.6M available*",
            inline=True
        )

        embed.add_field(
            name="📦 OTHER",
            value="Luxury watches & Zpofe Hub\n*Premium accessories*",
            inline=True
        )

        embed.add_field(
            name="🏪 OUR SELLERS",
            value="👤 **Zpofe** - Lead Supplier\n👤 **Drow** - Senior Supplier",
            inline=False
        )

        embed.set_footer(text="STK Services • South Bronx • Philly Streets Coming Soon")
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

# Slash Commands
@bot.tree.command(name="shop", description="Browse the STK Shop")
async def shop(interaction: discord.Interaction):
    """Browse the STK Shop"""
    try:
        view = STKShopView(interaction.user.id)
        embed = view.create_shop_embed()

        await interaction.response.send_message(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Error in shop command: {e}")
        await interaction.response.send_message("❌ An error occurred while loading the shop.", ephemeral=True)

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

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Command error: {error}")
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while processing the command.", ephemeral=True)
    except:
        logger.error("Could not send error message")

if __name__ == "__main__":
    try:
        bot.run(BotConfig.get_bot_token())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print("❌ Bot failed to start. Check your configuration and try again.")