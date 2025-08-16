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
        self.user_carts = {}  # Store user carts in memory - each user gets their own isolated cart

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

    async def setup_hook(self):
        """This is called when the bot is starting up"""
        logger.info("Bot is starting up...")

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

# Customer role ID
CUSTOMER_ROLE_ID = 1405942363721044199

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
    def __init__(self, selected_weapons=None, user_id=None):
        self.selected_weapons = selected_weapons or set()
        self.user_id = user_id

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
            placeholder="Pick your guns from the arsenal...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Ensure only the correct user can interact
            if self.user_id and interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shop session!", ephemeral=True)
                return

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
    def __init__(self, selected_watch=None, user_id=None):
        self.selected_watch = selected_watch
        self.user_id = user_id

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
            # Ensure only the correct user can interact
            if self.user_id and interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shop session!", ephemeral=True)
                return

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

class WeaponShopView(discord.ui.View):
    def __init__(self, user_id, selected_weapons=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_weapons = selected_weapons or set()

        # Add the weapon select dropdown with user_id
        self.add_item(WeaponSelect(self.selected_weapons, self.user_id))

    def create_weapon_embed(self):
        embed = discord.Embed(
            title="🔫 STREET ARSENAL",
            description="**Essential gear for the streets** • Fully, buttons, switches, binary, AR9\n**$1-$3** Premium setups • Custom builds • Street ready",
            color=0xFF0000
        )

        if self.selected_weapons:
            selected_list = []
            for weapon_id in self.selected_weapons:
                weapon_name = WEAPON_DATA[weapon_id]['name']
                selected_list.append(f"💥 {weapon_name}")

            embed.add_field(
                name=f"✅ SELECTED ({len(self.selected_weapons)})",
                value="\n".join(selected_list[:10]) + ("\n..." if len(selected_list) > 10 else ""),
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 SELECT YOUR SHIT",
                value="Pick from dropdown below",
                inline=True
            )

        embed.add_field(
            name="💰 PACKAGES",
            value="🔥 **FULL SAFE:** $3\n💼 **FULL BAG:** $2\n🚛 **FULL TRUNK:** $1",
            inline=True
        )

        embed.set_footer(text="STK Supply • No BS business")
        return embed

    @discord.ui.button(label='🛒 ADD', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
                return

            if not self.selected_weapons:
                await interaction.response.send_message("❌ Pick some shit first!", ephemeral=True)
                return

            # Add to cart
            if interaction.user.id not in bot.user_carts:
                bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "hub": None}

            bot.user_carts[interaction.user.id]["weapons"].update(self.selected_weapons)

            await interaction.response.send_message(f"✅ Added {len(self.selected_weapons)} items!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in add_to_cart: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Always go back to personal shop since this is user-specific
        view = PersonalSTKShopView(self.user_id)
        embed = view.create_personal_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🗑️ CLEAR', style=discord.ButtonStyle.danger, row=1)
    async def clear_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        self.selected_weapons.clear()
        view = WeaponShopView(interaction.user.id, self.selected_weapons)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Money data with regular and gamepass options
MONEY_DATA = {
    "max_money_990k": {"name": "Max Money 990k", "price": 1, "type": "regular"},
    "max_bank_990k": {"name": "Max Bank 990k", "price": 1, "type": "regular"},
    "max_money_1600k_gp": {"name": "Max Money 1.6M (Gamepass)", "price": 2, "type": "gamepass"},
    "max_bank_1600k_gp": {"name": "Max Bank 1.6M (Gamepass)", "price": 2, "type": "gamepass"}
}

# Multi-select money options
class MoneySelect(discord.ui.Select):
    def __init__(self, selected_money=None, user_id=None):
        self.selected_money = selected_money or set()
        self.user_id = user_id

        options = []
        for money_id, money_info in MONEY_DATA.items():
            is_selected = money_id in self.selected_money
            label = f"✅ {money_info['name']}" if is_selected else money_info['name']
            description = f"${money_info['price']} - {'GP Required' if money_info['type'] == 'gamepass' else 'No GP'}"
            if is_selected:
                description = "Selected"

            options.append(discord.SelectOption(
                label=label,
                value=money_id,
                description=description
            ))

        super().__init__(
            placeholder="Pick your money packages...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Ensure only the correct user can interact
            if self.user_id and interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shop session!", ephemeral=True)
                return

            # Toggle selection for each value
            for value in self.values:
                if value in self.selected_money:
                    self.selected_money.remove(value)
                else:
                    self.selected_money.add(value)

            # Update the view with new selections
            view = MoneyShopView(interaction.user.id, self.selected_money)
            embed = view.create_money_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in MoneySelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong. Try again.", ephemeral=True)

class MoneyShopView(discord.ui.View):
    def __init__(self, user_id, selected_money=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_money = selected_money or set()

        # Add the money select dropdown with user_id
        self.add_item(MoneySelect(self.selected_money, self.user_id))

    def create_money_embed(self):
        embed = discord.Embed(
            title="💰 CASH FLOW",
            description="**Clean money packages** • Regular & Gamepass options\n**$1-$2** packages • Max out your cash",
            color=0x00FF00
        )

        # Regular packages
        regular_packages = []
        gamepass_packages = []

        for money_id, money_info in MONEY_DATA.items():
            package_text = f"{money_info['name']} - ${money_info['price']}"
            if money_info['type'] == 'regular':
                regular_packages.append(f"💰 **{package_text}**")
            else:
                gamepass_packages.append(f"💎 **{package_text}**")

        embed.add_field(
            name="💸 REGULAR PACKAGES",
            value="\n".join(regular_packages),
            inline=True
        )

        embed.add_field(
            name="🎮 GAMEPASS PACKAGES",
            value="\n".join(gamepass_packages),
            inline=True
        )

        if self.selected_money:
            selected_list = []
            total_cost = 0
            for money_id in self.selected_money:
                money_info = MONEY_DATA[money_id]
                selected_list.append(f"💵 {money_info['name']} - ${money_info['price']}")
                total_cost += money_info['price']

            embed.add_field(
                name=f"✅ SELECTED ({len(self.selected_money)}) - Total: ${total_cost}",
                value="\n".join(selected_list),
                inline=False
            )

        embed.add_field(
            name="💼 HOW IT WORKS",
            value="1️⃣ Go to Black Market\n2️⃣ Put phone/drill up for sale\n3️⃣ We buy it for exact amount",
            inline=False
        )

        embed.set_footer(text="STK Supply • No BS business")
        return embed

    @discord.ui.button(label='🛒 ADD', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        if not self.selected_money:
            await interaction.response.send_message("❌ Pick some packages first!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "hub": None}

        bot.user_carts[interaction.user.id]["money"].update(self.selected_money)
        await interaction.response.send_message(f"✅ Added {len(self.selected_money)} packages!", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Always go back to personal shop since this is user-specific
        view = PersonalSTKShopView(self.user_id)
        embed = view.create_personal_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class OtherShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_watch = None

        # Add dropdowns with user_id
        self.add_item(WatchSelect(self.selected_watch, self.user_id))

    def create_other_embed(self):
        embed = discord.Embed(
            title="📦 PREMIUM GEAR",
            description="**High-end connections** • Watches & Scripts\n**$1** Designer pieces • Custom codes",
            color=0x9932CC
        )

        # Watches section
        embed.add_field(
            name="⌚ LUXURY WATCHES",
            value="**All Watches:** $1 each\nPick from dropdown",
            inline=True
        )

        if self.selected_watch:
            watch_info = WATCH_DATA[self.selected_watch]
            embed.add_field(
                name="✅ SELECTED",
                value=f"⌚ {watch_info['name']} - ${watch_info['price']}",
                inline=True
            )

        # Zpofe Hub section
        embed.add_field(
            name="💻 ZPOFE HUB (SOON)",
            value="🔥 All Scripts in One!\n💎 **Lifetime** - $5\n📅 **3 Month** - $3\n🗓️ **1 Month** - $1",
            inline=False
        )

        embed.set_footer(text="STK Supply • No BS business")
        return embed

    @discord.ui.button(label='🛒 ADD', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your session!", ephemeral=True)
            return

        if not self.selected_watch:
            await interaction.response.send_message("❌ Pick something first!", ephemeral=True)
            return

        # Add to cart
        if interaction.user.id not in bot.user_carts:
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "hub": None}

        if self.selected_watch not in bot.user_carts[interaction.user.id]["watches"]:
            bot.user_carts[interaction.user.id]["watches"].add(self.selected_watch)
            await interaction.response.send_message(f"✅ Added watch to cart!", ephemeral=True)
        else:
            await interaction.response.send_message("Already in cart!", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Always go back to personal shop since this is user-specific
        view = PersonalSTKShopView(self.user_id)
        embed = view.create_personal_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class InfoView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_info_embed(self):
        embed = discord.Embed(
            title="ℹ️ ABOUT STK",
            description="**The Block's Most Trusted Connect** • Your neighborhood plugs",
            color=0x00BFFF
        )

        embed.add_field(
            name="👑 THE CREW",
            value="💀 **ZPOFE** - Main connect • 3+ years • Lightning delivery\n⚡ **DROW** - Specialist • Premium connections • Trusted",
            inline=False
        )

        embed.add_field(
            name="🏆 STREET CRED",
            value="💀 **50+** customers\n⚡ **2-5 min** delivery\n🔥 **99.9%** success\n💯 **24/7** grinding",
            inline=True
        )

        embed.add_field(
            name="📞 CONTACT",
            value="🎯 **Active now**\n*Ready for business*",
            inline=True
        )

        embed.set_footer(text="STK Supply • No BS business")
        return embed

    @discord.ui.button(label='📞 CONTACT', style=discord.ButtonStyle.primary, row=1)
    async def contact_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📞 **CONTACT INFO**\n\nDM **Zpofe** for questions.\n\n*Response: Usually few hours*", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Always go back to personal shop since this is user-specific
        view = PersonalSTKShopView(self.user_id)
        embed = view.create_personal_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

class CartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_cart_embed(self):
        embed = discord.Embed(
            title="🛒 YOUR CART",
            description="**Review your shit:**",
            color=0xFF8C00
        )

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": set(), "watches": set(), "hub": None})
        total = 0
        items = []

        # Weapons
        if cart["weapons"]:
            items.append(f"🔫 **WEAPONS** ({len(cart['weapons'])})")
            for weapon_id in list(cart["weapons"])[:3]:  # Show only first 3
                items.append(f"  • {WEAPON_DATA[weapon_id]['name']}")
            if len(cart["weapons"]) > 3:
                items.append(f"  • ...and {len(cart['weapons']) - 3} more")

        # Money
        if cart["money"]:
            items.append(f"💰 **MONEY** ({len(cart['money'])})")
            for money_id in cart["money"]:
                money_info = MONEY_DATA[money_id]
                items.append(f"  • {money_info['name']} - ${money_info['price']}")
                total += money_info["price"]

        # Watches
        if cart["watches"]:
            items.append(f"⌚ **WATCHES** ({len(cart['watches'])})")
            for watch_id in cart["watches"]:
                watch_info = WATCH_DATA[watch_id]
                items.append(f"  • {watch_info['name']} - ${watch_info['price']}")
                total += watch_info["price"]

        if not items:
            embed.add_field(
                name="🛒 EMPTY",
                value="Your cart is empty!",
                inline=False
            )
        else:
            embed.add_field(
                name="📦 ITEMS",
                value="\n".join(items),
                inline=False
            )

            if total > 0:
                embed.add_field(
                    name="💰 TOTAL",
                    value=f"**${total:.2f}**\n*(+ weapon pricing)*",
                    inline=True
                )

        embed.set_footer(text="STK Supply • No BS business")
        return embed

    @discord.ui.button(label='💳 CHECKOUT', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your cart!", ephemeral=True)
            return

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": set(), "watches": set(), "hub": None})

        if not any([cart["weapons"], cart["money"], cart["watches"]]):
            await interaction.response.send_message("❌ Your cart is empty!", ephemeral=True)
            return

        try:
            ticket_channel = await create_purchase_ticket(interaction, cart)
            if ticket_channel:
                # Assign customer role
                try:
                    guild = interaction.guild
                    member = guild.get_member(interaction.user.id)
                    role = guild.get_role(CUSTOMER_ROLE_ID)
                    if role and member:
                        await member.add_roles(role)
                        logger.info(f"Assigned customer role to {member.display_name}")
                except Exception as e:
                    logger.error(f"Error assigning customer role: {e}")

                await interaction.response.send_message(f"✅ **Order placed!**\n\nYour channel: {ticket_channel.mention}\n\nYou've been given the customer role!", ephemeral=True)

                # Clear cart after successful ticket creation
                bot.user_carts[self.user_id] = {"weapons": set(), "money": set(), "watches": set(), "hub": None}
            else:
                await interaction.response.send_message("❌ Couldn't place order. Contact support.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error during checkout: {e}")
            await interaction.response.send_message("❌ Some shit went wrong during checkout.", ephemeral=True)

    @discord.ui.button(label='🗑️ CLEAR', style=discord.ButtonStyle.danger, row=1)
    async def clear_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This ain't your cart!", ephemeral=True)
            return

        bot.user_carts[self.user_id] = {"weapons": set(), "money": set(), "watches": set(), "hub": None}
        embed = self.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Always go back to personal shop since this is user-specific
        view = PersonalSTKShopView(self.user_id)
        embed = view.create_personal_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Shop selection dropdown for multi-shop system
class ShopSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Main STK Shop",
                value="main",
                description="Original STK Supply shop",
                emoji="💀"
            ),
            discord.SelectOption(
                label="South Bronx (Coming Soon)",
                value="south_bronx",
                description="Shop for South Bronx is coming soon",
                emoji="🚧"
            ),
            discord.SelectOption(
                label="Philly Streets (Coming Soon)",
                value="philly",
                description="Shop for Philly Streets is coming soon",
                emoji="🚧"
            )
        ]

        super().__init__(
            placeholder="Select a shop location...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_shop = self.values[0]

            if selected_shop == "main":
                view = PersistentSTKShopView()
                embed = view.create_shop_embed()
                await interaction.response.edit_message(embed=embed, view=view)
            elif selected_shop == "south_bronx":
                embed = discord.Embed(
                    title="🚧 SOUTH BRONX SHOP",
                    description="**COMING SOON**\n\nShop for South Bronx is not ready yet!\nStay tuned for updates.",
                    color=0xFFFF00
                )
                embed.set_footer(text="STK Supply • Expanding soon")
                view = ShopSelectorView()
                await interaction.response.edit_message(embed=embed, view=view)
            elif selected_shop == "philly":
                embed = discord.Embed(
                    title="🚧 PHILLY STREETS SHOP",
                    description="**COMING SOON**\n\nShop for Philly Streets is not ready yet!\nStay tuned for updates.",
                    color=0xFFFF00
                )
                embed.set_footer(text="STK Supply • Expanding soon")
                view = ShopSelectorView()
                await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in ShopSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

class ShopSelectorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ShopSelect())

    def create_selector_embed(self):
        embed = discord.Embed(
            title="🏪 VIEW ALL SHOPS",
            description="**Select a shop location:**\n\nChoose from our available locations below",
            color=0x39FF14
        )
        embed.add_field(
            name="📍 Available Locations",
            value="💀 **Main STK Shop** - Fully operational\n🚧 **South Bronx** - Coming soon\n🚧 **Philly Streets** - Coming soon",
            inline=False
        )
        embed.set_footer(text="STK Supply • Multiple locations")
        return embed

    @discord.ui.button(label='◀️ BACK TO MAIN', style=discord.ButtonStyle.primary, row=1)
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Personal Shop View (user-specific)
class PersonalSTKShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    def create_personal_shop_embed(self):
        user = bot.get_user(self.user_id)
        if user is None:
            # Fallback to user ID if user not in cache
            title = f"💀 User's STK Shop 💀"
        else:
            title = f"💀 {user.display_name}'s STK Shop 💀"
            
        embed = discord.Embed(
            title=title,
            description="**🔥 QUALITY** • **⚡ FAST** • **💯 NO BS**",
            color=0x39FF14
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a1c8a6&is=68a07726&hm=1a990b57e6e70e8c31978e9d90aba07b1607e688f610331dddd8b42d4ccb88dd&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a1c8a6&is=68a07726&hm=a73756ad78ccbf90f487df0045bc1ce19d558842ea8527d1444691fd4a29dc74&")

        embed.add_field(name="🔫 WEAPONS", value="**Street arsenal** • $1-$3", inline=True)
        embed.add_field(name="💰 MONEY", value="**Clean cash** • $1-$2", inline=True)
        embed.add_field(name="📦 PREMIUM", value="**High-end gear** • $1+", inline=True)
        embed.add_field(name="👑 THE CREW", value="💀 **ZPOFE** • ⚡ **DROW**", inline=False)
        embed.add_field(name="🏆 STREET CRED", value="50+ Customers • 2-5 Min Delivery", inline=True)
        embed.add_field(name="💼 HOW WE MOVE", value="Pick gear • Hit up connect • Get delivery", inline=True)

        embed.set_footer(text="STK Supply • Personal Shop")
        return embed

    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WeaponShopView(interaction.user.id)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, emoji='💵', row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MoneyShopView(self.user_id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 PREMIUM', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OtherShopView(self.user_id)
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, emoji='📋', row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = InfoView(self.user_id)
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, emoji='🔥', row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CartView(self.user_id)
        embed = view.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='◀️ BACK TO MAIN', style=discord.ButtonStyle.secondary, row=3)
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# Persistent STK Shop View - For setup command (no user restrictions)
class PersistentSTKShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def create_shop_embed(self):
        embed = discord.Embed(
            title="💀 STK SUPPLY GANG 💀",
            description="**The Block's Most Trusted Connect**\n**🔥 QUALITY** • **⚡ FAST** • **💯 NO BS**",
            color=0x39FF14
        )

        # Add images
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a1c8a6&is=68a07726&hm=1a990b57e6e70e8c31978e9d90aba07b1607e688f610331dddd8b42d4ccb88dd&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a1c8a6&is=68a07726&hm=a73756ad78ccbf90f487df0045bc1ce19d558842ea8527d1444691fd4a29dc74&")

        embed.add_field(
            name="🔫 WEAPONS",
            value="**Street arsenal** • $1-$3\nFully • Buttons • Switches • Binary • AR9",
            inline=True
        )

        embed.add_field(
            name="💰 MONEY",
            value="**Clean cash** • $1-$2\nMax money/bank • Regular & Gamepass",
            inline=True
        )

        embed.add_field(
            name="📦 PREMIUM",
            value="**High-end gear** • $1+\nWatches • Scripts • Exclusive drops",
            inline=True
        )

        embed.add_field(
            name="👑 THE CREW",
            value="💀 **ZPOFE** - Main connect • 3+ years\n⚡ **DROW** - Specialist • Premium connects",
            inline=False
        )

        embed.add_field(
            name="🏆 STREET CRED",
            value="💀 **50+** customers • ⚡ **2-5 min** delivery\n🔥 **99.9%** success • 💯 **24/7** grinding",
            inline=True
        )

        embed.add_field(
            name="💼 HOW WE MOVE",
            value="🎯 Check inventory • 💀 Pick gear\n💰 Hit up connect • ⚡ Get delivery",
            inline=True
        )

        embed.set_footer(text="STK Supply • No BS business • Holding it down since day one")
        return embed

    @discord.ui.button(label='🔫 WEAPONS', style=discord.ButtonStyle.danger, emoji='💥', row=1)
    async def weapons_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Each user gets their own weapon shop view
        view = WeaponShopView(interaction.user.id)
        embed = view.create_weapon_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💰 MONEY', style=discord.ButtonStyle.success, emoji='💵', row=1)
    async def money_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Each user gets their own money shop view
        view = MoneyShopView(interaction.user.id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 PREMIUM', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Each user gets their own other shop view
        view = OtherShopView(interaction.user.id)
        embed = view.create_other_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='ℹ️ INFO', style=discord.ButtonStyle.primary, emoji='📋', row=2)
    async def info_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Each user gets their own info view
        view = InfoView(interaction.user.id)
        embed = view.create_info_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🛒 CART', style=discord.ButtonStyle.primary, emoji='🔥', row=2)
    async def cart_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Each user gets their own cart view
        view = CartView(interaction.user.id)
        embed = view.create_cart_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🏪 ALL SHOPS', style=discord.ButtonStyle.secondary, emoji='🌍', row=3)
    async def view_all_shops(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ShopSelectorView()
        embed = view.create_selector_embed()
        await interaction.response.edit_message(embed=embed, view=view)

# STK Join System
class STKJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def create_join_embed(self):
        embed = discord.Embed(
            title="💀 JOIN STK 💀",
            description="**🔥 STK Entry Requirements**\n**No exceptions, no shortcuts.**",
            color=0xFF0000
        )

        # Warning section
        embed.add_field(
            name="⚠️ **AGE REQUIREMENT**",
            value="**IF YOU ARE NOT 16+ DO NOT TRY TO JOIN**\n**WE CHECK THIS SHIT**",
            inline=False
        )

        embed.add_field(
            name="🧠 Eligibility",
            value="• Must be 16+ years old\n• Active Roblox main account\n• Regularly play Tha Bronx 3",
            inline=True
        )

        embed.add_field(
            name="🎯 Behavior Standards",
            value="• No leaking, stealing, advertising\n• No alternate accounts\n• No disruptive behavior",
            inline=True
        )

        embed.add_field(
            name="🏗️ Respect Structure",
            value="• All services through Zpofe\n• Verified sellers only\n• STK channels only",
            inline=False
        )

        embed.add_field(
            name="⚔️ **TRYOUTS**",
            value="**3 FIGHTS TO JOIN:**\n🥊 **1v1 ZPOFE**\n🥊 **1v1 ASAI**\n🥊 **1v1 DROW**\n\n*Wait for all 3 members to join before starting*",
            inline=False
        )

        embed.set_footer(text="STK Gang • Elite only • No weak shit allowed")
        return embed

    @discord.ui.button(label='🥊 JOIN STK', style=discord.ButtonStyle.danger, emoji='💀', row=1)
    async def join_stk(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ticket_channel = await create_stk_join_ticket(interaction)
            if ticket_channel:
                await interaction.response.send_message(f"✅ **STK JOIN REQUEST CREATED!**\n\nYour tryout channel: {ticket_channel.mention}\n\n**Wait for all 3 STK members to join before starting fights!**", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Couldn't create join request. Contact staff.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating STK join ticket: {e}")
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

async def create_stk_join_ticket(interaction: discord.Interaction):
    """Create a ticket channel for STK join processing"""
    guild = interaction.guild
    if not guild:
        return None

    # Create ticket category if it doesn't exist
    category = discord.utils.get(guild.categories, name="🥊・STK TRYOUTS")
    if not category:
        try:
            category = await guild.create_category("🥊・STK TRYOUTS")
        except discord.Forbidden:
            logger.error("No permission to create category")
            return None

    # Create ticket channel
    ticket_name = f"stk-tryout-{interaction.user.name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"

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
            topic=f"STK join tryout for {interaction.user.display_name}"
        )

        # Send STK join embed
        await send_stk_join_embed(ticket_channel, interaction.user)

        return ticket_channel

    except discord.Forbidden:
        logger.error("No permission to create STK join ticket channel")
        return None

async def send_stk_join_embed(channel, user):
    """Send the STK join ticket embed"""

    # Create main STK join embed
    embed = discord.Embed(
        title="🥊 STK TRYOUT STARTED!",
        description="**Your tryout has been created**\n\n**WAIT FOR ALL 3 STK MEMBERS TO JOIN**",
        color=0xFF0000,
        timestamp=datetime.datetime.utcnow()
    )

    embed.add_field(
        name="👤 Applicant",
        value=f"{user.mention}\n`{user.id}`",
        inline=True
    )

    embed.add_field(
        name="⏰ Tryout Time",
        value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>",
        inline=True
    )

    embed.add_field(
        name="🥊 **FIGHT REQUIREMENTS**",
        value="**YOU MUST FIGHT ALL 3:**\n💀 **ZPOFE**\n⚡ **ASAI** \n🔥 **DROW**\n\n*1v1 each person one time*\n*Wait for all 3 to be pinged*",
        inline=False
    )

    embed.add_field(
        name="⚠️ **IMPORTANT**",
        value="**🔞 MUST BE 16+ YEARS OLD**\n**If you're under 16, leave now**\n\nAge will be verified!",
        inline=False
    )

    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="STK Gang • Elite tryouts • No weak shit", icon_url=channel.guild.me.display_avatar.url)

    await channel.send(embed=embed)

    # Ping STK members
    ping_message = "🔔 **NEW STK TRYOUT!**\n\n"

    # Ping Zpofe
    zpofe_id = 1385239185006268457
    ping_message += f"💀 <@{zpofe_id}> (ZPOFE)\n"

    # Ping Asai
    asai_id = 954818761729376357
    ping_message += f"⚡ <@{asai_id}> (ASAI)\n"

    # Ping Drow
    drow_id = 1394285950464426066
    ping_message += f"🔥 <@{drow_id}> (DROW)"

    ping_message += "\n\n**SOMEONE WANTS TO JOIN STK!**\n**ALL 3 OF YOU NEED TO FIGHT THEM!**"

    await channel.send(ping_message)

    # Add tryout management buttons
    view = STKTryoutManagementView()
    management_embed = discord.Embed(
        title="🛠️ Tryout Controls",
        description="**STK Member Controls**",
        color=0xFF0000
    )
    management_embed.add_field(
        name="✅ Accept",
        value="Accept them into STK",
        inline=True
    )
    management_embed.add_field(
        name="❌ Reject",
        value="Reject their application",
        inline=True
    )
    management_embed.add_field(
        name="🔒 Close",
        value="Close tryout channel",
        inline=True
    )

    await channel.send(embed=management_embed, view=view)

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

    # Calculate total and create detailed items list
    total = 0
    weapons_list = []
    money_list = []
    watches_list = []

    # Process weapons
    if cart["weapons"]:
        for weapon_id in cart["weapons"]:
            weapons_list.append(WEAPON_DATA[weapon_id]['name'])

    # Process money with pricing
    if cart["money"]:
        for money_id in cart["money"]:
            money_info = MONEY_DATA[money_id]
            money_list.append(f"{money_info['name']} - ${money_info['price']}")
            total += money_info["price"]

    # Process watches with pricing
    if cart["watches"]:
        for watch_id in cart["watches"]:
            watch_info = WATCH_DATA[watch_id]
            watches_list.append(f"{watch_info['name']} - ${watch_info['price']}")
            total += watch_info["price"]

    # Create detailed order summary embed
    order_embed = discord.Embed(
        title=" رپور ORDER SUMMARY",
        description=f"**Customer:** {user.mention} (`{user.id}`)\n**Order Time:** <t:{int(datetime.datetime.utcnow().timestamp())}:F>",
        color=0x00ff00,
        timestamp=datetime.datetime.utcnow()
    )

    # Add weapons section
    if weapons_list:
        weapons_text = "\n".join([f"• {weapon}" for weapon in weapons_list[:15]])
        if len(weapons_list) > 15:
            weapons_text += f"\n• ...and {len(weapons_list) - 15} more"
        order_embed.add_field(
            name=f"🔫 WEAPONS ({len(weapons_list)})",
            value=weapons_text,
            inline=False
        )

    # Add money section
    if money_list:
        money_text = "\n".join([f"• {money}" for money in money_list])
        order_embed.add_field(
            name=f"💰 MONEY PACKAGES ({len(money_list)})",
            value=money_text,
            inline=False
        )

    # Add watches section
    if watches_list:
        watches_text = "\n".join([f"• {watch}" for watch in watches_list])
        order_embed.add_field(
            name=f"⌚ WATCHES ({len(watches_list)})",
            value=watches_text,
            inline=False
        )

    # Add total
    order_embed.add_field(
        name="💰 TOTAL AMOUNT",
        value=f"**${total:.2f}**" if total > 0 else "**FREE** (Weapons only)",
        inline=True
    )

    order_embed.set_thumbnail(url=user.display_avatar.url)
    order_embed.set_footer(text="STK Supply • Order Processing", icon_url=channel.guild.me.display_avatar.url)

    await channel.send(embed=order_embed)

    # Send payment options with buttons
    payment_view = PaymentView()
    payment_embed = discord.Embed(
        title="💳 PAYMENT OPTIONS",
        description="**Choose your payment method:**",
        color=0x39FF14
    )

    payment_embed.add_field(
        name="💀 ZPOFE'S CASHAPP",
        value=f"[Click here to pay Zpofe]({PAYMENT_METHODS['zpofe']['cashapp']})",
        inline=True
    )

    payment_embed.add_field(
        name="⚡ DROW'S CASHAPP",
        value=f"[Click here to pay Drow]({PAYMENT_METHODS['drow']['cashapp']})",
        inline=True
    )

    payment_embed.add_field(
        name="📱 PAYMENT STEPS",
        value="1️⃣ Click payment button below\n2️⃣ Send the exact amount\n3️⃣ Screenshot proof\n4️⃣ Wait for delivery!",
        inline=False
    )

    # Add QR code if available
    if PAYMENT_METHODS["zpofe"]["qr_code"]:
        payment_embed.set_image(url=PAYMENT_METHODS["zpofe"]["qr_code"])

    payment_embed.set_footer(text="STK Supply • Secure Payments")
    await channel.send(embed=payment_embed, view=payment_view)

    # Send delivery tutorials based on cart contents
    await send_delivery_tutorials(channel, cart)

    # Ping sellers
    ping_message = "🔔 **NEW ORDER ALERT!**\n\n"
    zpofe_id = 1385239185006268457
    ping_message += f"💀 <@{zpofe_id}> (ZPOFE)\n"

    drow_id = 1394285950464426066
    ping_message += f"⚡ <@{drow_id}> (DROW)"

    ping_message += f"\n\n**CUSTOMER:** {user.mention}\n**TOTAL:** ${total:.2f}\n**READY FOR BUSINESS!**"
    await channel.send(ping_message)

    # Add ticket management
    management_view = TicketManagementView()
    management_embed = discord.Embed(
        title="🛠️ STAFF CONTROLS",
        description="**Order Management Tools**",
        color=0xDAA520
    )
    management_embed.add_field(name="✅ Complete", value="Mark order as completed", inline=True)
    management_embed.add_field(name="🔒 Close", value="Close and archive ticket", inline=True)

    await channel.send(embed=management_embed, view=management_view)

async def send_delivery_tutorials(channel, cart):
    """Send appropriate tutorials based on cart contents"""

    # Money tutorial
    if cart["money"]:
        money_embed = discord.Embed(
            title="💰 MONEY DELIVERY TUTORIAL",
            description="**How to receive your money packages:**",
            color=0x00FF00
        )

        money_embed.add_field(
            name="📍 STEP 1: Location",
            value="Go to **Black Market** in the game\nWait for Zpofe/Drow to join your server",
            inline=False
        )

        money_embed.add_field(
            name="📱 STEP 2: Put Item Up",
            value="Put your **phone** or **drill** up for sale\nSet price to the amount you're buying\n*(Example: $990,000 for 990K or $1,600,000 for 1.6M gamepass)*",
            inline=False
        )

        money_embed.add_field(
            name="💵 STEP 3: Get Paid",
            value="Zpofe/Drow will buy your item\nYou receive the clean money instantly\n**Transaction complete!**",
            inline=False
        )

        money_embed.set_footer(text="STK Supply • Money Delivery")
        await channel.send(embed=money_embed)

    # Weapons tutorial
    if cart["weapons"]:
        weapons_embed = discord.Embed(
            title="🔫 WEAPONS DELIVERY TUTORIAL",
            description="**How to receive your weapons:**",
            color=0xFF0000
        )

        # Check if they need storage
        storage_needed = []
        if any("bag" in weapon.lower() for weapon in [WEAPON_DATA[w]['name'] for w in cart["weapons"]]):
            storage_needed.append("**Get a bag** from safe")
        if any("trunk" in weapon.lower() for weapon in [WEAPON_DATA[w]['name'] for w in cart["weapons"]]):
            storage_needed.append("**Get a car** and empty trunk")

        weapons_embed.add_field(
            name="📍 STEP 1: Preparation",
            value="Go to your **safe** location\n" + "\n".join(storage_needed) if storage_needed else "Make sure you have storage space",
            inline=False
        )

        weapons_embed.add_field(
            name="🚗 STEP 2: Get Ready",
            value="Empty your **current inventory**\nIf you ordered trunk items, get a car\nWait at a safe location",
            inline=False
        )

        weapons_embed.add_field(
            name="⚡ STEP 3: Delivery",
            value="Zpofe/Drow will **join your server**\nThey will **teleport to you**\nThey will **dupe and give** your weapons",
            inline=False
        )

        weapons_embed.add_field(
            name="📦 STEP 4: Storage",
            value="**IMMEDIATELY** put weapons in:\n• **Bag** (if you ordered bag items)\n• **Trunk** (if you ordered trunk items)\n• **Safe** (for secure storage)",
            inline=False
        )

        weapons_embed.add_field(
            name="⚠️ IMPORTANT",
            value="**DON'T** leave weapons in inventory\n**DO** store them immediately\n**BE** ready when they join",
            inline=False
        )

        weapons_embed.set_footer(text="STK Supply • Weapons Delivery")
        await channel.send(embed=weapons_embed)

    # Watches tutorial
    if cart["watches"]:
        watch_embed = discord.Embed(
            title="⌚ WATCHES DELIVERY TUTORIAL",
            description="**How to receive your luxury watches:**",
            color=0x9932CC
        )

        watch_embed.add_field(
            name="📍 STEP 1: Meet Up",
            value="Wait for Zpofe/Drow to join\nThey'll teleport to your location\nBe ready to receive items",
            inline=False
        )

        watch_embed.add_field(
            name="💎 STEP 2: Delivery",
            value="They will trade you the watch\nCheck that it's the correct model\nEnjoy your luxury timepiece!",
            inline=False
        )

        watch_embed.set_footer(text="STK Supply • Watch Delivery")
        await channel.send(embed=watch_embed)

# Setup shop command
@bot.tree.command(name="setup", description="Setup the STK Shop")
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
            await interaction.response.send_message("❌ You need admin permissions.", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Setting up STK Supply...", ephemeral=True)

        view = PersistentSTKShopView()
        embed = view.create_shop_embed()

        await interaction.channel.send(embed=embed, view=view)
        await interaction.edit_original_response(content="✅ **STK Supply live!**")

    except Exception as e:
        logger.error(f"Error in setup_shop command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ Some shit went wrong.")
        except discord.NotFound:
            logger.error("Could not send error message")

# Setup STK Join command
@bot.tree.command(name="setup_stkjoin", description="Setup the STK Join system")
async def setup_stk_join(interaction: discord.Interaction):
    """Setup the STK Join interface"""
    try:
        # Check permissions
        has_permission = False
        if interaction.user.guild_permissions.manage_channels:
            has_permission = True
        elif BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ You need admin permissions.", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Setting up STK Join...", ephemeral=True)

        view = STKJoinView()
        embed = view.create_join_embed()

        await interaction.channel.send(embed=embed, view=view)
        await interaction.edit_original_response(content="✅ **STK Join system live!**")

    except Exception as e:
        logger.error(f"Error in setup_stk_join command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ Some shit went wrong.")
        except discord.NotFound:
            logger.error("Could not send error message")

# STK Tryout management view
class STKTryoutManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ ACCEPT', style=discord.ButtonStyle.success, custom_id='accept_stk')
    async def accept_stk(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK members can do this.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ ACCEPTED INTO STK",
            description="**Welcome to the gang!**\n\nYou've proven yourself. Welcome to STK!",
            color=0x00ff00,
            timestamp=datetime.datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label='❌ REJECT', style=discord.ButtonStyle.danger, custom_id='reject_stk')
    async def reject_stk(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK members can do this.", ephemeral=True)
            return

        embed = discord.Embed(
            title="❌ REJECTED",
            description="**You didn't make it**\n\nYou're not STK material. Better luck next time.",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label='🔒 CLOSE', style=discord.ButtonStyle.secondary, custom_id='close_stk_tryout')
    async def close_tryout(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK members can close tryouts.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔒 Tryout Closed",
            description="This tryout is now closed.",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )

        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Tryout closed by STK member")
        except:
            pass

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
            await interaction.response.send_message("❌ You need admin permissions.", ephemeral=True)
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
                await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
                return

        product_id = bot.db.add_product(name, description, price, stock, None, category)

        if product_id:
            embed = discord.Embed(
                title="✅ Product Added",
                description=f"Added **{name}** to inventory!",
                color=0x00ff00
            )
            embed.add_field(name="🆔 ID", value=str(product_id), inline=True)
            embed.add_field(name="💰 Price", value=f"${price:.2f}", inline=True)
            embed.add_field(name="📦 Stock", value=str(stock), inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to add product.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in add_product command: {e}")
        await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

# Payment view with buttons
class PaymentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='💀 PAY ZPOFE', style=discord.ButtonStyle.success, custom_id='pay_zpofe')
    async def pay_zpofe(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💀 ZPOFE'S PAYMENT",
            description="**Send payment to Zpofe:**",
            color=0x00ff00
        )

        embed.add_field(
            name="💰 CashApp Link",
            value=f"[Click here to pay Zpofe]({PAYMENT_METHODS['zpofe']['cashapp']})",
            inline=False
        )

        embed.add_field(
            name="📱 CashApp Tag",
            value=f"`{PAYMENT_METHODS['zpofe']['cashapp']}`",
            inline=False
        )

        embed.add_field(
            name="📋 Instructions",
            value="1️⃣ Click the link above\n2️⃣ Send the exact amount\n3️⃣ Screenshot the payment\n4️⃣ Send proof in this ticket",
            inline=False
        )

        if PAYMENT_METHODS["zpofe"]["qr_code"]:
            embed.set_image(url=PAYMENT_METHODS["zpofe"]["qr_code"])

        embed.set_footer(text="STK Supply • Zpofe's Payment")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='⚡ PAY DROW', style=discord.ButtonStyle.primary, custom_id='pay_drow')
    async def pay_drow(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚡ DROW'S PAYMENT",
            description="**Send payment to Drow:**",
            color=0x3498db
        )

        embed.add_field(
            name="💰 CashApp Link",
            value=f"[Click here to pay Drow]({PAYMENT_METHODS['drow']['cashapp']})",
            inline=False
        )

        embed.add_field(
            name="📱 CashApp Tag",
            value=f"`{PAYMENT_METHODS['drow']['cashapp']}`",
            inline=False
        )

        embed.add_field(
            name="📋 Instructions",
            value="1️⃣ Click the link above\n2️⃣ Send the exact amount\n3️⃣ Screenshot the payment\n4️⃣ Send proof in this ticket",
            inline=False
        )

        embed.set_footer(text="STK Supply • Drow's Payment")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            description="This order is closed. Thanks for business!",
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
            description="**Order fulfilled!**\n\nThanks for choosing STK Supply!",
            color=0x00ff00,
            timestamp=datetime.datetime.utcnow()
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
        # Add connection retries and better error handling
        import time

        # Start HTTP server for health checks
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

        # Try multiple ports for health check server
        port = int(os.getenv('PORT', 5000))
        ports_to_try = [port, 5000, 8080, 8081, 8082, 3000]

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

        # Retry connection logic
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                logger.info(f"Starting Discord bot (attempt {attempt + 1}/{max_retries})...")

                # Add delay between retries to avoid rate limiting
                if attempt > 0:
                    logger.info(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

                # Start Discord bot
                bot.run(BotConfig.get_bot_token(), reconnect=True)
                break

            except discord.HTTPException as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    logger.error(f"Rate limited. Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        continue
                else:
                    logger.error(f"HTTP Exception: {e}")
                    break
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    break

        logger.error("All connection attempts failed")
        print("❌ Bot failed to start after all retries. Check your bot token and try again later.")

    except Exception as e:
        logger.error(f"Critical error: {e}")
        print("❌ Bot failed to start. Check your configuration.")