import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import datetime
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
        "qr_code": "https://i.imgur.com/ZQR7X8Y.png",
        "display_name": "Zpofe"
    },
    "drow": {
        "cashapp": "https://cash.app/$DatOneGuy13s",
        "qr_code": None,
        "display_name": "Drow"
    }
}

# Verification system configuration
VERIFICATION_CONFIG = {
    "verified_role_id": 1399949469532946483,
    "alert_user_1": 1385239185006268457,
    "alert_user_2": 954818761729376357,
    "max_attempts": 3,
    "timeout_duration": 3600  # 1 hour in seconds
}

# Store verification attempts
verification_attempts = {}
pending_verifications = {}

# Create bot instance
bot = ShopBot()

# Weapon data
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
                description="Selected" if is_selected else "Click to add"
            ))

        super().__init__(
            placeholder="Pick your guns from the collection...",
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
                await interaction.response.send_message("❌ Some shit went wrong. Try again.", ephemeral=True)

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
            placeholder="Pick a watch...",
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
                await interaction.response.send_message("❌ Some shit went wrong. Try again.", ephemeral=True)

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
            placeholder="Pick your Zpofe Hub access...",
            min_values=0,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("🚧 **Zpofe Hub Coming Soon!** 🚧\nThis ain't ready for purchase yet but you can check it out.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in ZpofeHubSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong. Try again.", ephemeral=True)

class WeaponShopView(discord.ui.View):
    def __init__(self, user_id, selected_weapons=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_weapons = selected_weapons or set()

        # Add the weapon select dropdown
        self.add_item(WeaponSelect(self.selected_weapons))

    def create_weapon_embed(self):
        embed = discord.Embed(
            title="🔫 WEAPONS & SWITCHES",
            description="**Real shit for real YNs**\n\nSwitches • Buttons • Full Auto Mods\n\n**Prices: $1-$3**\nGlock collection, AR builds, premium switches\n\n💀 **No bullshit, just results**",
            color=0x000000
        )

        if self.selected_weapons:
            selected_list = []
            for weapon_id in self.selected_weapons:
                weapon_name = WEAPON_DATA[weapon_id]['name']
                selected_list.append(f"💥 {weapon_name}")

            embed.add_field(
                name=f"✅ SELECTED ({len(self.selected_weapons)})",
                value="\n".join(selected_list) if selected_list else "None selected",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 NOTHING SELECTED",
                value="Pick your shit from the dropdown below",
                inline=False
            )

        # Show pricing info
        embed.add_field(
            name="💰 PACKAGES",
            value="🔥 **FULL STASH:** $3.00\n💼 **FULL BAG:** $2.00\n🚛 **FULL LOAD:** $1.00",
            inline=True
        )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n⚡ **DROW** - The connect",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
                return

            if not self.selected_weapons:
                await interaction.response.send_message("❌ Pick some shit before adding to cart!", ephemeral=True)
                return

            # Add to cart
            if interaction.user.id not in bot.user_carts:
                bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

            bot.user_carts[interaction.user.id]["weapons"].update(self.selected_weapons)

            await interaction.response.send_message(f"✅ Added {len(self.selected_weapons)} items to your cart!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in add_to_cart: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong. Try again.", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, emoji='🏠', row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🗑️ CLEAR', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def clear_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
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
            title="💰 MONEY PACKAGES",
            description="**Clean cash for real YNs**\n\nNo questions asked money transfers",
            color=0x000000
        )

        embed.add_field(
            name="💸 CASH PACKAGES",
            value="💰 **990K Clean** - $1.00\n🏦 **990K Bank Drop** - $1.00\n💳 **1.6M Wallet Fill** - $2.00",
            inline=False
        )

        embed.add_field(
            name="💼 HOW IT WORKS",
            value="1️⃣ Go to **Black Market**\n2️⃣ Put your **phone/drill** up for the amount\n3️⃣ **Zpofe** or **Drow** buys it for that price",
            inline=False
        )

        if self.selected_money:
            embed.add_field(
                name="✅ SELECTED",
                value=self.selected_money,
                inline=True
            )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n⚡ **DROW** - The connect",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    @discord.ui.button(label='💰 990K CLEAN', style=discord.ButtonStyle.success, emoji='💵', row=1)
    async def select_990k(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        self.selected_money = "990K Clean - $1"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='🏦 990K BANK', style=discord.ButtonStyle.success, emoji='🏧', row=1)
    async def select_990k_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        self.selected_money = "990K Bank Drop - $1"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='💳 1.6M BOOST', style=discord.ButtonStyle.success, emoji='💎', row=1)
    async def select_1_6m(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        self.selected_money = "1.6M Wallet Fill - $2"
        embed = self.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.primary, emoji='🔥', row=2)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        if not self.selected_money:
            await interaction.response.send_message("❌ Pick a package before adding to cart!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

        bot.user_carts[interaction.user.id]["money"] = self.selected_money
        await interaction.response.send_message(f"✅ Added {self.selected_money} to your cart!", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, emoji='🏠', row=2)
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
            title="📦 PREMIUM SHIT",
            description="**High-end gear for real YNs**\n\nWatches • Scripts • Exclusive items",
            color=0x000000
        )

        # Watches section
        embed.add_field(
            name="⌚ LUXURY WATCHES",
            value="**All Watches:** $1.00 each\nPick from the dropdown below",
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
            value="🔥 All of Zpofe's Scripts in One Place!\n\n💎 **Lifetime Key** - $5.00\n📅 **3 Month Key** - $3.00\n🗓️ **1 Month Key** - $1.00",
            inline=False
        )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n⚡ **DROW** - The connect",
            inline=True
        )

        return embed

    @discord.ui.button(label='🛒 ADD TO CART', style=discord.ButtonStyle.success, emoji='🔥', row=2)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        if not self.selected_watch and not self.selected_hub:
            await interaction.response.send_message("❌ Pick some shit before adding to cart!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}

        added_items = []
        if self.selected_watch:
            if self.selected_watch not in bot.user_carts[interaction.user.id]["watches"]:
                bot.user_carts[interaction.user.id]["watches"].add(self.selected_watch)
                added_items.append(f"Watch: {WATCH_DATA[self.selected_watch]['name']}")

        if self.selected_hub:
            bot.user_carts[interaction.user.id]["hub"] = self.selected_hub
            added_items.append(f"Zpofe Hub: {self.selected_hub}")

        if added_items:
            await interaction.response.send_message(f"✅ Added to cart:\n" + "\n".join(added_items), ephemeral=True)
        else:
            await interaction.response.send_message("Nothing new to add.", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, emoji='🏠', row=2)
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
            title="ℹ️ ABOUT US",
            description="**Real YN suppliers with real results**\n\nYour trusted connects since day one!",
            color=0x808080
        )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n• 3+ years in the game • All services\n• Fast delivery • Loyal customers\n• Always available • Real shit only\n\n⚡ **DROW** - The specialist\n• High-end connect • Quality guaranteed\n• Silent moves • Trusted source\n• No bullshit • Results speak",
            inline=False
        )

        embed.add_field(
            name="🚀 SERVICES ACTIVE",
            value="💻 **All services** are currently live\n🎮 **More shit coming soon**",
            inline=False
        )

        embed.add_field(
            name="🏆 WHY US?",
            value="✅ **50+** Happy customers\n✅ **2-5 min** Fast delivery\n✅ **99.9%** Success rate\n✅ **24/7** Always available\n✅ **100%** No scam guarantee\n✅ **Silent** Professional service",
            inline=True
        )

        embed.add_field(
            name="📞 CONTACT",
            value="🎯 **Active now**\n\n*Ready for business*",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    @discord.ui.button(label='📞 CONTACT', style=discord.ButtonStyle.primary, emoji='💬', row=1)
    async def contact_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📞 **CONTACT INFO**\n\nDM **Zpofe** for any questions or support.\n\n*Response time: Usually within a few hours*", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, emoji='🏠', row=1)
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
            title="🛒 YOUR CART",
            description="**Review your shit before checkout:**",
            color=0xFF8C00
        )

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": None, "watches": set(), "hub": None})
        total = 0
        items = []

        # Weapons
        if cart["weapons"]:
            items.append(f"🔫 **WEAPONS** ({len(cart['weapons'])})")
            for weapon_id in cart["weapons"]:
                items.append(f"  • {WEAPON_DATA[weapon_id]['name']}")
            items.append("  💰 *Price: Package deal pricing*")

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
            items.append(f"  • *Not available yet*")

        if not items:
            embed.add_field(
                name="🛒 EMPTY CART",
                value="Your cart is empty! Go back and pick some shit.",
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
                    name="💰 TOTAL",
                    value=f"**${total:.2f}**\n*(Weapon pricing at checkout)*",
                    inline=True
                )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n⚡ **DROW** - The connect",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    @discord.ui.button(label='💳 CHECKOUT', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your cart!", ephemeral=True)
            return

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": None, "watches": set(), "hub": None})

        if not any([cart["weapons"], cart["money"], cart["watches"]]):
            await interaction.response.send_message("❌ Your cart is empty!", ephemeral=True)
            return

        try:
            ticket_channel = await create_purchase_ticket(interaction, cart)
            if ticket_channel:
                await interaction.response.send_message(f"✅ **Order placed!**\n\nYour private channel: {ticket_channel.mention}\n\nZpofe and Drow have been notified!", ephemeral=True)

                # Clear cart after successful ticket creation
                bot.user_carts[self.user_id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}
            else:
                await interaction.response.send_message("❌ Couldn't place order. Contact support.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error during checkout: {e}")
            await interaction.response.send_message("❌ Some shit went wrong during checkout.", ephemeral=True)

    @discord.ui.button(label='🗑️ CLEAR CART', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def clear_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your cart!", ephemeral=True)
            return

        bot.user_carts[self.user_id] = {"weapons": set(), "money": None, "watches": set(), "hub": None}
        embed = self.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, emoji='🏠', row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Main STK Shop View - Each user gets their own instance when they interact
class STKShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_shop_embed(self):
        embed = discord.Embed(
            title="💀 STK SUPPLY 💀",
            description="**Real YN business with real results**\n\n**🔥 QUALITY GUARANTEED** • **⚡ FAST DELIVERY** • **💯 NO SCAM**\n\nYour trusted plugs since day one\n\n**Pick what you need:**",
            color=0x000000
        )

        # Add images
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a11fe6&is=689fce66&hm=c6993267511d0fbfe32bf615f5a205279510c9091caa9f217860f1dd9e106ff0&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a11fe6&is=689fce66&hm=3d7e0b292626bab621f3dde0fd5a0377f52a31cc9fc81fddcde8db437de66edd&")

        embed.add_field(
            name="🔫 WEAPONS & SWITCHES",
            value="**Real shit for real YNs**\n\nSwitches • Buttons • Full Auto Mods\n\n**Prices: $1-$3**\nGlock collection, AR builds, premium switches\n\n💀 **No bullshit**",
            inline=True
        )

        embed.add_field(
            name="💰 MONEY PACKAGES",
            value="**Clean cash for YNs**\n\nNo questions asked transfers\n\n**Packages: $1-$2**\n990K clean, bank drops, wallet fills\n\n⚡ **Fast & clean**",
            inline=True
        )

        embed.add_field(
            name="📦 PREMIUM SHIT",
            value="**High-end gear**\n\nWatches • Scripts • Exclusive items\n\n**Starting at $1**\nLuxury watches, premium codes\n\n🔥 **Top quality**",
            inline=True
        )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n• 3+ years in the game • All services\n• Fast delivery • Loyal customers\n\n⚡ **DROW** - The specialist\n• High-end connect • Quality guaranteed\n• Silent moves • Trusted source",
            inline=False
        )

        embed.add_field(
            name="🏆 WHY US?",
            value="💀 **50+** Happy customers\n⚡ **2-5 min** Fast delivery\n🔥 **99.9%** Success rate\n💯 **24/7** Always available\n🚫 **100%** No scam guarantee",
            inline=True
        )

        embed.add_field(
            name="💼 HOW IT WORKS",
            value="🎯 **Browse** the catalog\n💀 **Pick** your shit\n💰 **Pay** your plug\n📞 **Get** private chat\n⚡ **Receive** fast delivery",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        view = WeaponShopView(interaction.user.id)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, emoji='💵', row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        view = MoneyShopView(interaction.user.id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 PREMIUM', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        view = OtherShopView(interaction.user.id)
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, emoji='📋', row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        view = InfoView(interaction.user.id)
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, emoji='🔥', row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        view = CartView(interaction.user.id)
        embed = view.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Persistent shop view for the main shop message
class PersistentSTKShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def create_shop_embed(self):
        embed = discord.Embed(
            title="💀 STK SUPPLY 💀",
            description="**Real YN business with real results**\n\n**🔥 QUALITY GUARANTEED** • **⚡ FAST DELIVERY** • **💯 NO SCAM**\n\nYour trusted plugs since day one\n\n**Pick what you need:**",
            color=0x000000
        )

        # Add images
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a11fe6&is=689fce66&hm=c6993267511d0fbfe32bf615f5a205279510c9091caa9f217860f1dd9e106ff0&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a11fe6&is=689fce66&hm=3d7e0b292626bab621f3dde0fd5a0377f52a31cc9fc81fddcde8db437de66edd&")

        embed.add_field(
            name="🔫 WEAPONS & SWITCHES",
            value="**Real shit for real YNs**\n\nSwitches • Buttons • Full Auto Mods\n\n**Prices: $1-$3**\nGlock collection, AR builds, premium switches\n\n💀 **No bullshit**",
            inline=True
        )

        embed.add_field(
            name="💰 MONEY PACKAGES",
            value="**Clean cash for YNs**\n\nNo questions asked transfers\n\n**Packages: $1-$2**\n990K clean, bank drops, wallet fills\n\n⚡ **Fast & clean**",
            inline=True
        )

        embed.add_field(
            name="📦 PREMIUM SHIT",
            value="**High-end gear**\n\nWatches • Scripts • Exclusive items\n\n**Starting at $1**\nLuxury watches, premium codes\n\n🔥 **Top quality**",
            inline=True
        )

        embed.add_field(
            name="👑 YOUR PLUGS",
            value="💀 **ZPOFE** - Main supplier\n• 3+ years in the game • All services\n• Fast delivery • Loyal customers\n\n⚡ **DROW** - The specialist\n• High-end connect • Quality guaranteed\n• Silent moves • Trusted source",
            inline=False
        )

        embed.add_field(
            name="🏆 WHY US?",
            value="💀 **50+** Happy customers\n⚡ **2-5 min** Fast delivery\n🔥 **99.9%** Success rate\n💯 **24/7** Always available\n🚫 **100%** No scam guarantee",
            inline=True
        )

        embed.add_field(
            name="💼 HOW IT WORKS",
            value="🎯 **Browse** the catalog\n💀 **Pick** your shit\n💰 **Pay** your plug\n📞 **Get** private chat\n⚡ **Receive** fast delivery",
            inline=True
        )

        embed.set_footer(text="STK Supply • Real YN business • Since day one • 50+ customers served")
        return embed

    # These buttons create a new user-specific view for each interaction
    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WeaponShopView(interaction.user.id)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, emoji='💵', row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MoneyShopView(interaction.user.id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 PREMIUM', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OtherShopView(interaction.user.id)
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, emoji='📋', row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = InfoView(interaction.user.id)
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, emoji='🔥', row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CartView(interaction.user.id)
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
        title="🔥 Order Received!",
        description="**Your order is being processed**\n\nZpofe or Drow will be with you soon. They've been notified!",
        color=0x00ff00,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(
        name="👤 Customer",
        value=f"{user.mention}\n`{user.id}`",
        inline=True
    )

    embed.add_field(
        name="💰 Total",
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
    embed.set_footer(text="STK Supply • Professional Service", icon_url=channel.guild.me.display_avatar.url)

    await channel.send(embed=embed)

    # Send payment embed
    payment_embed = discord.Embed(
        title="💳 Payment Info",
        description="**Pick your payment method:**",
        color=0x00ff00
    )

    # Zpofe's payment info
    if PAYMENT_METHODS["zpofe"]["cashapp"]:
        payment_embed.add_field(
            name="💀 Zpofe's CashApp",
            value=f"[Pay Zpofe here]({PAYMENT_METHODS['zpofe']['cashapp']})\n`{PAYMENT_METHODS['zpofe']['cashapp']}`",
            inline=False
        )

    # Drow's payment info
    if PAYMENT_METHODS["drow"]["cashapp"]:
        payment_embed.add_field(
            name="⚡ Drow's Payment",
            value=f"[Pay Drow here]({PAYMENT_METHODS['drow']['cashapp']})\n`{PAYMENT_METHODS['drow']['cashapp']}`",
            inline=False
        )
    else:
        payment_embed.add_field(
            name="⚡ Drow's Payment",
            value="*Payment method not set*",
            inline=False
        )

    payment_embed.add_field(
        name="📱 How to pay",
        value="1️⃣ Pick your plug\n2️⃣ Send payment using the link\n3️⃣ Send screenshot of payment\n4️⃣ Get your shit delivered fast!",
        inline=False
    )

    payment_embed.set_footer(text="STK Supply • Secure Payment")

    # Add QR code image if available
    if PAYMENT_METHODS["zpofe"]["qr_code"]:
        payment_embed.set_image(url=PAYMENT_METHODS["zpofe"]["qr_code"])

    await channel.send(embed=payment_embed)

    # Ping sellers
    ping_message = "🔔 **New Order!**\n\n"

    # Ping Zpofe
    zpofe_id = 1399949855799119952
    ping_message += f"💀 <@{zpofe_id}> (Zpofe)\n"

    # Ping Drow
    if BotConfig.ADMIN_ROLE_ID:
        ping_message += f"⚡ <@&{BotConfig.ADMIN_ROLE_ID}> (Drow)"
    else:
        drow_id = 123456789
        ping_message += f"⚡ <@{drow_id}> (Drow)"

    ping_message += "\n\n**Customer ready to do business! Handle this shit.**"

    await channel.send(ping_message)

    # Add ticket management buttons
    view = TicketManagementView()
    management_embed = discord.Embed(
        title="🛠️ Ticket Controls",
        description="**Staff Controls**",
        color=0xDAA520
    )
    management_embed.add_field(
        name="🔒 Close Ticket",
        value="Close this ticket and delete channel",
        inline=True
    )
    management_embed.add_field(
        name="✅ Mark Done",
        value="Mark the order as complete",
        inline=True
    )

    await channel.send(embed=management_embed, view=view)

# Captcha generation function
def generate_captcha():
    """Generate a simple captcha image with text"""
    # Generate random 5-character string
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    # Create image
    width, height = 200, 80
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Try to use a system font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = ImageFont.load_default()

    # Add noise lines
    for _ in range(5):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill='lightgray', width=1)

    # Draw text with slight variations
    for i, char in enumerate(captcha_text):
        x = 20 + i * 30 + random.randint(-5, 5)
        y = 20 + random.randint(-5, 5)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), char, font=font, fill=color)

    # Add noise dots
    for _ in range(50):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill='gray')

    # Save to bytes
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return captcha_text, img_byte_arr

# Verification View
class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔐 VERIFY YOURSELF', style=discord.ButtonStyle.primary, custom_id='start_verification')
    async def start_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_id = interaction.user.id

            # Check if user already has verified role
            verified_role = interaction.guild.get_role(VERIFICATION_CONFIG["verified_role_id"])
            if verified_role and verified_role in interaction.user.roles:
                await interaction.response.send_message("✅ You're already verified!", ephemeral=True)
                return

            # Check attempt count
            if user_id not in verification_attempts:
                verification_attempts[user_id] = 0

            if verification_attempts[user_id] >= VERIFICATION_CONFIG["max_attempts"]:
                await handle_verification_failure(interaction, "too_many_attempts")
                return

            # Generate captcha
            captcha_text, captcha_image = generate_captcha()
            pending_verifications[user_id] = captcha_text

            # Create verification embed
            embed = discord.Embed(
                title="💀 STK VERIFICATION 💀",
                description="**Type what you see in the image**\n\n🔥 **CAPTCHA CHALLENGE** 🔥\n\nProve you're real to access the server",
                color=0x000000
            )

            embed.add_field(
                name="📋 VERIFICATION RULES",
                value="💀 **Type EXACTLY what you see**\n⚡ **Case sensitive**\n🔥 **2 minutes max**\n👑 **Wrong answer = timeout**",
                inline=False
            )

            embed.set_footer(text=f"Attempt {verification_attempts[user_id] + 1}/{VERIFICATION_CONFIG['max_attempts']} • STK Security • Real members only")

            # Send captcha
            file = discord.File(captcha_image, filename="captcha.png")
            embed.set_image(url="attachment://captcha.png")

            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

            # Wait for response
            def check(m):
                return m.author.id == user_id and isinstance(m.channel, discord.DMChannel)

            try:
                # Try to send DM for response
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send("**Reply with the captcha text here:**")

                response = await bot.wait_for('message', check=check, timeout=120.0)

                # Check captcha
                if response.content.upper() == captcha_text.upper():
                    await handle_verification_success(interaction)
                else:
                    verification_attempts[user_id] += 1
                    await handle_verification_failure(interaction, "wrong_answer")

            except asyncio.TimeoutError:
                verification_attempts[user_id] += 1
                await handle_verification_failure(interaction, "timeout")
            except discord.Forbidden:
                # Can't DM user, try verification channel
                verification_channel = interaction.guild.get_channel(1406083380591722668)
                if verification_channel:
                    await verification_channel.send(f"❌ {interaction.user.mention} **Can't send DM!** Enable DMs from server members to complete verification.")
                await interaction.followup.send("❌ **Can't send DM!** Enable DMs from server members to complete verification.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in verification: {e}")
            await interaction.followup.send("❌ Verification system error. Contact staff.", ephemeral=True)

async def handle_verification_success(interaction):
    """Handle successful verification"""
    try:
        # Add verified role
        verified_role = interaction.guild.get_role(VERIFICATION_CONFIG["verified_role_id"])
        if verified_role:
            await interaction.user.add_roles(verified_role, reason="Passed verification")

        # Clean up
        user_id = interaction.user.id
        if user_id in verification_attempts:
            del verification_attempts[user_id]
        if user_id in pending_verifications:
            del pending_verifications[user_id]

        # Success message
        success_embed = discord.Embed(
            title="💀 WELCOME TO STK 💀",
            description="**Verification successful!**\n\n🔥 **You're now a verified member** 🔥",
            color=0x000000
        )
        success_embed.add_field(
            name="🎉 ACCESS GRANTED",
            value="💯 **All channels unlocked**\n⚡ **Welcome to the community**\n👑 **Enjoy STK Supply**",
            inline=False
        )

        try:
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send(embed=success_embed)
        except:
            pass

        await interaction.followup.send("✅ **Verification successful!** Welcome to the server.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in verification success: {e}")

async def handle_verification_failure(interaction, reason):
    """Handle failed verification"""
    try:
        user_id = interaction.user.id
        guild = interaction.guild

        # Timeout user
        timeout_until = discord.utils.utcnow() + datetime.timedelta(seconds=VERIFICATION_CONFIG["timeout_duration"])
        await interaction.user.timeout(timeout_until, reason=f"Verification failure: {reason}")

        # Create alert ticket
        await create_security_alert(guild, interaction.user, reason)

        # Send failure message
        failure_embed = discord.Embed(
            title="💀 VERIFICATION FAILED 💀",
            description="**Access denied - You ain't real**",
            color=0xff0000
        )

        if reason == "too_many_attempts":
            failure_embed.add_field(
                name="🚫 TOO MANY ATTEMPTS",
                value="❌ **You failed too many times**\n\n💀 **Suspicious activity detected**\n🔥 **You have been timed out**",
                inline=False
            )
        elif reason == "wrong_answer":
            failure_embed.add_field(
                name="❌ WRONG ANSWER",
                value=f"💀 **Incorrect captcha answer**\n\n⚡ **Attempts: {verification_attempts[user_id]}/{VERIFICATION_CONFIG['max_attempts']}**\n🔥 **You have been timed out**",
                inline=False
            )
        elif reason == "timeout":
            failure_embed.add_field(
                name="⏰ VERIFICATION TIMEOUT",
                value="💀 **You took too long**\n\n🔥 **Please respond faster**\n⚡ **You have been timed out**",
                inline=False
            )

        failure_embed.add_field(
            name="🔒 SECURITY ALERT",
            value="👑 **Staff been notified**\n💀 **Sus activity detected**",
            inline=False
        )

        try:
            await interaction.followup.send(embed=failure_embed, ephemeral=True)
        except:
            pass

    except Exception as e:
        logger.error(f"Error in verification failure: {e}")

async def create_security_alert(guild, user, reason):
    """Create security alert ticket for failed verification"""
    try:
        # Create ticket category if it doesn't exist
        category = discord.utils.get(guild.categories, name="🚨・SECURITY-ALERTS")
        if not category:
            try:
                category = await guild.create_category("🚨・SECURITY-ALERTS")
            except discord.Forbidden:
                logger.error("No permission to create security alert category")
                return

        # Create alert channel
        alert_name = f"security-alert-{user.name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add alert users
        alert_user_1 = guild.get_member(VERIFICATION_CONFIG["alert_user_1"])
        alert_user_2 = guild.get_member(VERIFICATION_CONFIG["alert_user_2"])

        if alert_user_1:
            overwrites[alert_user_1] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if alert_user_2:
            overwrites[alert_user_2] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        alert_channel = await guild.create_text_channel(
            alert_name,
            category=category,
            overwrites=overwrites,
            topic=f"Security alert for {user.display_name}"
        )

        # Send alert embed
        alert_embed = discord.Embed(
            title="🚨 SECURITY ALERT",
            description="**Verification failure detected**",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )

        alert_embed.add_field(
            name="👤 User",
            value=f"{user.mention}\n`{user.id}`\n{user.display_name}",
            inline=True
        )

        alert_embed.add_field(
            name="📅 Account Age",
            value=f"<t:{int(user.created_at.timestamp())}:R>",
            inline=True
        )

        alert_embed.add_field(
            name="📊 Join Date",
            value=f"<t:{int(user.joined_at.timestamp())}:R>",
            inline=True
        )

        reason_text = {
            "too_many_attempts": "❌ **TOO MANY FAILED ATTEMPTS**\nUser exceeded maximum verification attempts.",
            "wrong_answer": "❌ **WRONG CAPTCHA ANSWER**\nUser provided incorrect captcha response.",
            "timeout": "⏰ **VERIFICATION TIMEOUT**\nUser failed to respond within time limit.",
            "suspicious": "🤖 **SUSPICIOUS BEHAVIOR**\nAutomatic bot detection triggered."
        }

        alert_embed.add_field(
            name="⚠️ Failure Reason",
            value=reason_text.get(reason, "Unknown reason"),
            inline=False
        )

        alert_embed.add_field(
            name="🔒 Actions Taken",
            value=f"• User timed out for {VERIFICATION_CONFIG['timeout_duration']//60} minutes\n• Security alert created\n• Staff notified",
            inline=False
        )

        alert_embed.set_thumbnail(url=user.display_avatar.url)
        alert_embed.set_footer(text="STK Security System")

        # Send alert with management buttons
        view = SecurityAlertView(user.id)
        await alert_channel.send(f"🚨 <@{VERIFICATION_CONFIG['alert_user_1']}> <@{VERIFICATION_CONFIG['alert_user_2']}>", embed=alert_embed, view=view)

    except Exception as e:
        logger.error(f"Error creating security alert: {e}")

# Security alert management view
class SecurityAlertView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label='🔨 BAN USER', style=discord.ButtonStyle.danger, custom_id='ban_user')
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user = interaction.guild.get_member(self.user_id)
            if user:
                await user.ban(reason="Security verification failure - Suspicious activity")
                await interaction.response.send_message(f"✅ **{user.display_name}** has been banned for verification failure.", ephemeral=False)
            else:
                await interaction.response.send_message("❌ User not found in server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error banning user: {e}", ephemeral=True)

    @discord.ui.button(label='👢 KICK USER', style=discord.ButtonStyle.secondary, custom_id='kick_user')
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user = interaction.guild.get_member(self.user_id)
            if user:
                await user.kick(reason="Security verification failure - Suspicious activity")
                await interaction.response.send_message(f"✅ **{user.display_name}** has been kicked for verification failure.", ephemeral=False)
            else:
                await interaction.response.send_message("❌ User not found in server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error kicking user: {e}", ephemeral=True)

    @discord.ui.button(label='🔓 REMOVE TIMEOUT', style=discord.ButtonStyle.success, custom_id='remove_timeout')
    async def remove_timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user = interaction.guild.get_member(self.user_id)
            if user:
                await user.timeout(None, reason="Timeout removed by staff")
                await interaction.response.send_message(f"✅ **{user.display_name}**'s timeout has been removed.", ephemeral=False)
            else:
                await interaction.response.send_message("❌ User not found in server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing timeout: {e}", ephemeral=True)

# Member join event
@bot.event
async def on_member_join(member):
    """Handle new member joins"""
    try:
        # Check if verification system is enabled
        verified_role = member.guild.get_role(VERIFICATION_CONFIG["verified_role_id"])
        if not verified_role:
            return

        # Send welcome message with verification
        try:
            embed = discord.Embed(
                title="💀 WELCOME TO STK 💀",
                description=f"**Welcome to the server!**\n\n🔥 **VERIFICATION REQUIRED** 🔥\n\nComplete verification to get access",
                color=0x000000
            )

            embed.add_field(
                name="🛡️ SECURITY CHECK",
                value="💀 **Real members only** - No bots, no fake accounts\n\n⚡ **Click below to start verification**",
                inline=False
            )

            embed.add_field(
                name="⚠️ VERIFICATION RULES",
                value="💯 **2 minutes to complete**\n🔥 **3 attempts max**\n⚡ **Fail = timeout**\n👑 **Staff alerts for suspicious activity**",
                inline=False
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="STK Security • Real member verification • Professional service")

            view = VerificationView()

            # Try to send DM first
            try:
                dm_channel = await member.create_dm()
                await dm_channel.send(embed=embed, view=view)
            except discord.Forbidden:
                # If DM fails, send in the specific verification channel
                verification_channel = member.guild.get_channel(1406083380591722668)
                if verification_channel:
                    await verification_channel.send(f"{member.mention}", embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error sending verification message: {e}")

    except Exception as e:
        logger.error(f"Error in on_member_join: {e}")

# Verification setup command
@bot.tree.command(name="setup_verification", description="Setup the verification system (Admin only)")
async def setup_verification(interaction: discord.Interaction):
    """Setup verification system"""
    try:
        # Check permissions
        has_permission = False
        if interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to setup verification.", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Setting up verification system...", ephemeral=True)

        # Get verification channel
        guild = interaction.guild
        verification_channel = guild.get_channel(1406083380591722668)

        if not verification_channel:
            await interaction.edit_original_response(content="❌ **Verification channel not found!** Make sure the channel exists.")
            return

        # Send verification embed
        embed = discord.Embed(
            title="💀 STK VERIFICATION 💀",
            description="**Real members only - No bots allowed**\n\n🔥 **SECURITY CHECK REQUIRED** 🔥\n\nComplete verification to access the server",
            color=0x000000
        )

        embed.add_field(
            name="🛡️ SECURITY FEATURES",
            value="💀 **Anti-bot protection**\n⚡ **Real person verification**\n🔥 **Auto-timeout for failures**\n👑 **Staff alerts for suspicious activity**",
            inline=False
        )

        embed.add_field(
            name="📋 HOW TO GET ACCESS",
            value="1️⃣ **Click** the verification button\n2️⃣ **Complete** the captcha challenge\n3️⃣ **Get access** to all channels\n\n💯 **Simple verification process**",
            inline=False
        )

        embed.add_field(
            name="👑 STK SECURITY",
            value="💀 **3 attempts max**\n⚡ **2 minute time limit**\n🚫 **Failures = timeout**\n🔥 **Real members welcome**",
            inline=True
        )

        embed.set_footer(text="STK Security • Real member verification • Professional service")

        view = VerificationView()
        await verification_channel.send(embed=embed, view=view)

        # Set up channel permissions for verification-only access
        verified_role = guild.get_role(VERIFICATION_CONFIG["verified_role_id"])
        if verified_role:
            channels_updated = 0
            permission_errors = 0

            # Process all channels in the server
            for channel in guild.channels:
                if channel.id != verification_channel.id:  # Don't modify verification channel
                    try:
                        # Get existing overwrites to preserve admin permissions
                        existing_overwrites = channel.overwrites.copy()

                        # Set @everyone to completely hide channel
                        existing_overwrites[guild.default_role] = discord.PermissionOverwrite(
                            read_messages=False,
                            view_channel=False,
                            send_messages=False,
                            connect=False,
                            speak=False,
                            add_reactions=False,
                            embed_links=False,
                            attach_files=False,
                            use_external_emojis=False,
                            manage_messages=False
                        )

                        # Give verified role full access
                        existing_overwrites[verified_role] = discord.PermissionOverwrite(
                            read_messages=True,
                            view_channel=True,
                            send_messages=True,
                            connect=True,
                            speak=True,
                            add_reactions=True,
                            embed_links=True,
                            attach_files=True,
                            use_external_emojis=True,
                            read_message_history=True
                        )

                        # Ensure bot has full access
                        existing_overwrites[guild.me] = discord.PermissionOverwrite(
                            read_messages=True,
                            view_channel=True,
                            send_messages=True,
                            connect=True,
                            speak=True,
                            manage_messages=True,
                            embed_links=True,
                            attach_files=True,
                            add_reactions=True,
                            use_external_emojis=True,
                            read_message_history=True,
                            manage_roles=True
                        )

                        # Apply overwrites
                        await channel.edit(overwrites=existing_overwrites)
                        channels_updated += 1

                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.1)

                    except discord.Forbidden:
                        permission_errors += 1
                        logger.warning(f"No permission to edit channel: {channel.name}")
                        continue
                    except Exception as e:
                        permission_errors += 1
                        logger.error(f"Error setting permissions for {channel.name}: {e}")
                        continue

            # Set up verification channel with proper permissions
            verification_overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    view_channel=True,
                    send_messages=False,
                    add_reactions=False,
                    connect=False,
                    embed_links=False,
                    attach_files=False,
                    use_external_emojis=False
                ),
                verified_role: discord.PermissionOverwrite(
                    read_messages=True,
                    view_channel=True,
                    send_messages=True,
                    add_reactions=True,
                    embed_links=True,
                    attach_files=True,
                    use_external_emojis=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True,
                    add_reactions=True,
                    use_external_emojis=True,
                    manage_roles=True
                )
            }

            try:
                await verification_channel.edit(overwrites=verification_overwrites)
            except Exception as e:
                logger.error(f"Error setting verification channel permissions: {e}")

            # Auto-verify all existing members who don't have the role
            members_verified = 0
            verification_errors = 0

            for member in guild.members:
                if not member.bot and verified_role not in member.roles:
                    try:
                        await member.add_roles(verified_role, reason="Auto-verification for existing members during setup")
                        members_verified += 1
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.2)
                    except discord.Forbidden:
                        verification_errors += 1
                        logger.warning(f"No permission to give role to: {member.display_name}")
                        continue
                    except Exception as e:
                        verification_errors += 1
                        logger.error(f"Error verifying member {member.display_name}: {e}")
                        continue

            # Create detailed response
            response_parts = [
                "✅ **STK Verification System Activated!**",
                "",
                f"🔒 **Channel Security:** {channels_updated} channels secured",
                f"👥 **Members Verified:** {members_verified} existing members auto-verified",
                f"⚡ **Verification Channel:** Set up and ready",
                "💀 **Security Level:** Maximum protection active"
            ]

            if permission_errors > 0:
                response_parts.append(f"⚠️ **Note:** {permission_errors} channels couldn't be modified (permission issues)")

            if verification_errors > 0:
                response_parts.append(f"⚠️ **Note:** {verification_errors} members couldn't be auto-verified (permission issues)")

            response_parts.extend([
                "",
                "🔥 **SECURITY STATUS:**",
                "• Unverified users see ONLY verification channel",
                "• All other channels completely hidden",
                "• Existing members automatically verified",
                "• New members must complete verification",
                "",
                "👑 **Real YNs only - Security tight!**"
            ])

            await interaction.edit_original_response(content="\n".join(response_parts))
        else:
            await interaction.edit_original_response(content="❌ **Verified role not found!** Check the role ID in config.")

    except Exception as e:
        logger.error(f"Error in setup_verification: {e}")
        await interaction.edit_original_response(content="❌ Error setting up verification system.")

# Setup shop command
@bot.tree.command(name="setup", description="Setup the STK Shop for everyone to use")
async def setup_shop(interaction: discord.Interaction):
    """Setup the STK Shop interface"""
    try:
        # Check permissions
        has_permission = False
        if interaction.user.guild_permissions.manage_channels:
            has_permission = True
        elif BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission or admin role to setup the shop.", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Setting up STK Supply...", ephemeral=True)

        view = PersistentSTKShopView()
        embed = view.create_shop_embed()



        await interaction.channel.send(embed=embed, view=view)
        await interaction.edit_original_response(content="✅ **STK Supply updated!** All changes are live.")

    except discord.NotFound:
        logger.error("Interaction expired")
    except Exception as e:
        logger.error(f"Error in setup_shop command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong during setup.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ Some shit went wrong during setup.")
        except discord.NotFound:
            logger.error("Could not send error message")

@bot.tree.command(name="clear", description="Delete bot messages from this channel")
@app_commands.describe(
    amount="Number of bot messages to delete (default: 10, max: 100)"
)
async def clear_messages(interaction: discord.Interaction, amount: int = 10):
    """Delete bot messages from the current channel"""
    try:
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1

        # Check permissions
        has_permission = False
        if interaction.user.guild_permissions.manage_messages:
            has_permission = True
        elif BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need 'Manage Messages' permission or admin role to use this.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Clearing up to {amount} messages...", ephemeral=True)

        messages_deleted = 0
        async for message in interaction.channel.history(limit=500):
            if messages_deleted >= amount:
                break

            if message.author == bot.user:
                try:
                    await message.delete()
                    messages_deleted += 1
                    await asyncio.sleep(0.5)
                except discord.errors.NotFound:
                    continue
                except discord.errors.Forbidden:
                    continue

        if messages_deleted > 0:
            await interaction.followup.send(f"✅ Cleared {messages_deleted} message(s).", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ No messages found to clear.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in clear command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Some shit went wrong.", ephemeral=True)

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
    """Add a new product"""
    try:
        # Check admin permissions
        if BotConfig.ADMIN_ROLE_ID:
            if not any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("❌ You don't have permission for this.", ephemeral=True)
                return

        product_id = bot.db.add_product(name, description, price, stock, None, category)

        if product_id:
            embed = discord.Embed(
                title="✅ Product Added",
                description=f"Added **{name}** to inventory!",
                color=0x00ff00
            )
            embed.add_field(name="🆔 Product ID", value=str(product_id), inline=True)
            embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
            embed.add_field(name="📦 Stock", value=str(stock), inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to add product.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in add_product command: {e}")
        await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

@bot.tree.command(name="setpayment", description="Set payment method for Drow (Admin only)")
@app_commands.describe(
    cashapp_link="CashApp link (e.g., https://cash.app/$username)",
    qr_code_url="QR code image URL (optional)"
)
async def set_payment(interaction: discord.Interaction, cashapp_link: str, qr_code_url: str = None):
    """Set payment method for Drow"""
    try:
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.administrator:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only admins can set payment methods.", ephemeral=True)
            return

        # Validate cashapp link
        if not cashapp_link.startswith(("https://cash.app/", "http://cash.app/")):
            await interaction.response.send_message("❌ Provide a valid CashApp link", ephemeral=True)
            return

        # Update payment methods
        PAYMENT_METHODS["drow"]["cashapp"] = cashapp_link
        if qr_code_url:
            PAYMENT_METHODS["drow"]["qr_code"] = qr_code_url

        embed = discord.Embed(
            title="✅ Payment Method Updated",
            description="Drow's payment method updated!",
            color=0x00ff00
        )
        embed.add_field(name="💳 CashApp Link", value=cashapp_link, inline=False)
        if qr_code_url:
            embed.add_field(name="📱 QR Code", value="QR code updated", inline=False)
            embed.set_image(url=qr_code_url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in set_payment command: {e}")
        await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

# Ticket management view
class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 CLOSE', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only staff can close tickets.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="This order is closed. Thanks for the business!",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket closed by staff")
        except:
            pass

    @discord.ui.button(label='✅ MARK DONE', style=discord.ButtonStyle.success, custom_id='mark_completed')
    async def mark_completed(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only staff can mark orders complete.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Order Complete",
            description="**This order has been fulfilled!**\n\nThanks for choosing STK Supply. Enjoy your shit!",
            color=0x00ff00,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="📞 Support",
            value="Hit us up if you have any issues!",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Command error: {error}")

    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        logger.error(f"Command {interaction.command.name if interaction.command else 'unknown'} failed: {original_error}")

        if isinstance(original_error, discord.NotFound):
            logger.error("Discord API NotFound error")
            return

    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
        else:
            try:
                await interaction.followup.send("❌ Some shit went wrong.", ephemeral=True)
            except discord.NotFound:
                logger.error("Could not send followup")
    except discord.NotFound:
        logger.error("Could not respond to interaction")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

if __name__ == "__main__":
    try:
        # Add HTTP server for health checks
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
                pass

        # Start HTTP server
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
            logger.warning("Could not start health check server")

        # Start Discord bot
        bot.run(BotConfig.get_bot_token())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print("❌ Bot failed to start. Check your config.")