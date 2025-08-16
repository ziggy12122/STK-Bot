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
import aiohttp
import urllib.parse
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
        intents.members = True # Added to ensure member data is available

        super().__init__(
            command_prefix=BotConfig.PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.playing, name="🚀 Starting Up STK Operations..."),
            status=discord.Status.dnd
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

        # Sync slash commands with retry logic
        try:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} command(s)')
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.warning("Rate limited when syncing commands, retrying in 60 seconds...")
                await asyncio.sleep(60)
                try:
                    synced = await self.tree.sync()
                    logger.info(f'Synced {len(synced)} command(s) after retry')
                except Exception as retry_error:
                    logger.error(f'Failed to sync commands after retry: {retry_error}')
            else:
                logger.error(f'Failed to sync commands: {e}')
        except Exception as e:
            logger.error(f'Failed to sync commands: {e}')

        # Start cool status rotation
        self.status_task = asyncio.create_task(self.rotate_status())

    async def rotate_status(self):
        """Rotate through cool status messages"""
        statuses = [
            {"activity": discord.Activity(type=discord.ActivityType.watching, name="💀 STK Operations 💀"), "status": discord.Status.online},
            {"activity": discord.Activity(type=discord.ActivityType.playing, name="🔫 The Block 🔫"), "status": discord.Status.dnd},
            {"activity": discord.Game(name="💰 Making Money Moves 💰"), "status": discord.Status.online},
            {"activity": discord.Activity(type=discord.ActivityType.listening, name="🎯 Customer Orders 🎯"), "status": discord.Status.idle},
            {"activity": discord.Activity(type=discord.ActivityType.watching, name="⚡ 24/7 Grinding ⚡"), "status": discord.Status.online},
            {"activity": discord.Game(name="🏆 50+ Customers Served 🏆"), "status": discord.Status.dnd},
            {"activity": discord.Activity(type=discord.ActivityType.competing, name="💯 Street Rankings 💯"), "status": discord.Status.online},
            {"activity": discord.Activity(type=discord.ActivityType.playing, name="🔥 No BS Business 🔥"), "status": discord.Status.dnd},
            {"activity": discord.Activity(type=discord.ActivityType.watching, name="📦 Fresh Inventory 📦"), "status": discord.Status.online},
            {"activity": discord.Game(name="⚔️ Elite STK Gang ⚔️"), "status": discord.Status.idle},
        ]
        
        while not self.is_closed():
            try:
                for status_info in statuses:
                    if self.is_closed():
                        break
                    
                    await self.change_presence(
                        activity=status_info["activity"],
                        status=status_info["status"]
                    )
                    
                    # Wait 30 seconds before changing to next status
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error updating status: {e}")
                await asyncio.sleep(60)  # Wait longer if there's an error

    async def setup_hook(self):
        """This is called when the bot is starting up"""
        logger.info("Bot is starting up...")

    async def close(self):
        """Clean up when bot shuts down"""
        if hasattr(self, 'status_task'):
            self.status_task.cancel()
        await super().close()

    async def on_command_error(self, ctx, error):
        """Handle command errors to prevent crashes"""
        logger.error(f"Command error in {ctx.command}: {error}")

    async def on_error(self, event, *args, **kwargs):
        """Handle general bot errors"""
        logger.error(f"Bot error in {event}: {args}")

    async def on_member_join(self, member):
        """Handle new member join - assign auto-role for unverified users"""
        try:
            # Auto-add to directory
            auto_detect_members(member.guild)
            
            # Role IDs for verification system
            AUTO_ROLE_ID = 1406380208507977899  # Unverified role
            VERIFIED_ROLE_ID = 1399949469532946483  # Verified role
            VERIFICATION_CHANNEL_ID = 1398741781331447890  # Verification channel
            
            # Check if user already has verified role (shouldn't happen for new joins)
            verified_role = member.guild.get_role(VERIFIED_ROLE_ID)
            if verified_role and verified_role in member.roles:
                logger.info(f"{member.display_name} already verified, skipping auto-role")
                return
            
            # Assign auto-role to new member (unverified users get this role)
            try:
                auto_role = member.guild.get_role(AUTO_ROLE_ID)
                if auto_role:
                    await member.add_roles(auto_role, reason="Auto-assigned unverified role on join")
                    logger.info(f"Assigned auto-role to {member.display_name} - they need to verify")
                    
                    # Wait a moment for role to be applied
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Auto-role {AUTO_ROLE_ID} not found in guild")
            except Exception as e:
                logger.error(f"Failed to assign auto-role to {member.display_name}: {e}")
            
            # Get verification channel
            verification_channel = member.guild.get_channel(VERIFICATION_CHANNEL_ID)
            if not verification_channel:
                logger.error(f"Verification channel {VERIFICATION_CHANNEL_ID} not found")
                return
            
            # Create welcome embed with verification focus
            embed = discord.Embed(
                title="🔥 WELCOME TO STK 🔥",
                description=f"**{member.mention} - You must verify to access the server!**",
                color=0xFF0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            
            embed.add_field(
                name="⚠️ MANDATORY VERIFICATION",
                value=f"**Click the VERIFY button in {verification_channel.mention}**\n\nYou can only see this channel until you verify!",
                inline=False
            )
            
            embed.add_field(
                name="🚨 IMPORTANT",
                value="• Verification is **REQUIRED**\n• No verification = No access to other channels\n• Click verify to unlock everything",
                inline=False
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="STK Supply • Verification Required", icon_url=member.guild.me.display_avatar.url)
            
            # Send welcome message to verification channel
            try:
                await verification_channel.send(f"{member.mention}", embed=embed)
                logger.info(f"Sent verification message for {member.display_name}")
            except Exception as e:
                logger.error(f"Failed to send verification message: {e}")
                
            logger.info(f"New member joined: {member.display_name} ({member.id}) - Auto-role assigned, needs verification")
            
        except Exception as e:
            logger.error(f"Error in member join event: {e}")

    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # Auto-assign unverified role to existing members without verified role
        await self.auto_assign_unverified_roles()

        # Test database connection
        try:
            test_products = self.db.get_all_products()
            logger.info(f'Database connected successfully. Found {len(test_products)} products.')
        except Exception as e:
            logger.error(f'Database connection issue: {e}')

        # Sync slash commands with retry logic
        try:
            synced = await self.tree.sync()
            logger.info(f'Synced {len(synced)} command(s)')
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.warning("Rate limited when syncing commands, retrying in 60 seconds...")
                await asyncio.sleep(60)
                try:
                    synced = await self.tree.sync()
                    logger.info(f'Synced {len(synced)} command(s) after retry')
                except Exception as retry_error:
                    logger.error(f'Failed to sync commands after retry: {retry_error}')
            else:
                logger.error(f'Failed to sync commands: {e}')
        except Exception as e:
            logger.error(f'Failed to sync commands: {e}')

        # Start cool status rotation
        self.status_task = asyncio.create_task(self.rotate_status())

    async def auto_assign_unverified_roles(self):
        """Auto-assign unverified role to existing members who don't have verified role"""
        try:
            AUTO_ROLE_ID = 1406380208507977899  # Unverified role
            VERIFIED_ROLE_ID = 1399949469532946483  # Verified role
            
            assigned_count = 0
            for guild in self.guilds:
                auto_role = guild.get_role(AUTO_ROLE_ID)
                verified_role = guild.get_role(VERIFIED_ROLE_ID)
                
                if not auto_role or not verified_role:
                    logger.error(f"Missing roles in guild {guild.name}")
                    continue
                
                for member in guild.members:
                    if member.bot:
                        continue
                    
                    # If member doesn't have verified role and doesn't have auto role, give them auto role
                    if verified_role not in member.roles and auto_role not in member.roles:
                        try:
                            await member.add_roles(auto_role, reason="Auto-assigned unverified role - needs verification")
                            assigned_count += 1
                            logger.info(f"Auto-assigned unverified role to {member.display_name}")
                            await asyncio.sleep(0.5)  # Rate limit protection
                        except Exception as e:
                            logger.error(f"Failed to assign auto-role to {member.display_name}: {e}")
            
            if assigned_count > 0:
                logger.info(f"Auto-assigned unverified role to {assigned_count} existing members")
                
        except Exception as e:
            logger.error(f"Error in auto_assign_unverified_roles: {e}")

    async def on_member_remove(self, member):
        """Cool member leave message"""
        try:
            embed = discord.Embed(
                title="💨 MEMBER LEFT",
                description=f"**{member.display_name}** left the server",
                color=0xFF0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            
            embed.add_field(
                name="📊 Stats",
                value=f"**Members:** {len(member.guild.members)}\n**Joined:** <t:{int(member.joined_at.timestamp())}:R>",
                inline=True
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="STK Supply • Member departed")
            
            # Send to general channel
            log_channel = None
            for channel in member.guild.text_channels:
                if channel.name.lower() in ['general', 'logs', 'chat']:
                    log_channel = channel
                    break
            
            if log_channel:
                await log_channel.send(embed=embed)
                
            logger.info(f"Member left: {member.display_name} ({member.id})")
            
        except Exception as e:
            logger.error(f"Error in member remove event: {e}")

# Create bot instance
bot = ShopBot()

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

# STK Directory Data - Updated for 2025
STK_DIRECTORY = {
    "king_slime": {
        "user_id": 954818761729376357,
        "rank": "🐍 King Slime 🐍",
        "role": "Leader",
        "description": "Supreme leader of STK operations",
        "specialties": ["Leadership", "Strategy", "Operations"],
        "status": "Active",
        "joined": "2025",
        "achievements": ["Founded STK", "50+ Operations", "Elite Status"],
        "color": 0xFFD700,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif"
    },
    "zpofe": {
        "user_id": 1385239185006268457,
        "rank": "🪖 General 🪖",
        "role": "Main Connect & Developer",
        "description": "Lead developer and primary connection for all services",
        "specialties": ["Development", "Connections", "Customer Service"],
        "status": "Active",
        "joined": "2025",
        "achievements": ["3+ Years Experience", "Bot Developer", "Top Seller"],
        "color": 0xFF0000,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif"
    },
    "asai": {
        "user_id": 666394721039417346,
        "rank": "🪖 General 🪖",
        "role": "Operations General",
        "description": "Strategic operations and coordination specialist",
        "specialties": ["Operations", "Coordination", "Strategy"],
        "status": "Active",
        "joined": "2025",
        "achievements": ["Strategic Mastermind", "Operations Expert"],
        "color": 0x00FF00,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif"
    },
    "drow": {
        "user_id": 1394285950464426066,
        "rank": "🪖 General 🪖 | 🔌 Plug 🔌 | 👏 Top Smacka 👏",
        "role": "Multi-Role Elite",
        "description": "Premium connections and top-tier operations specialist",
        "specialties": ["Premium Services", "Elite Operations", "Connections"],
        "status": "Active",
        "joined": "2025",
        "achievements": ["Multi-Role Elite", "Premium Connect", "Top Performer"],
        "color": 0x9932CC,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif"
    },
    "top_smacka": {
        "user_id": 1106038406317871184,
        "rank": "👏 Top Smacka 👏",
        "role": "Elite Operator",
        "description": "High-performance operations specialist",
        "specialties": ["Elite Operations", "Performance", "Execution"],
        "status": "Active",
        "joined": "2025",
        "achievements": ["Top Performance", "Elite Status"],
        "color": 0xFF6600,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif"
    }
}

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
    "BlueFaceCartier": {"name": "Blue Face Cartier", "price": 1},
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

# Money data with regular and gamepass options
MONEY_DATA = {
    "max_money_990k": {"name": "Max Money 990k", "price": 1, "type": "regular"},
    "max_bank_990k": {"name": "Max Bank 990k", "price": 1, "type": "regular"},
    "max_money_1600k_gp": {"name": "Max Money 1.6M (Gamepass)", "price": 2, "type": "gamepass"},
    "max_bank_1600k_gp": {"name": "Max Bank 1.6M (Gamepass)", "price": 2, "type": "gamepass"}
}

# Storage package data - these are storage types, not weapon bundles
PACKAGE_DATA = {
    "safe_storage": {
        "name": "SAFE STORAGE",
        "price": 3,
        "description": "Store weapons in your safe",
        "storage_type": "safe"
    },
    "bag_storage": {
        "name": "BAG STORAGE",
        "price": 2,
        "description": "Store weapons in your bag",
        "storage_type": "bag"
    },
    "trunk_storage": {
        "name": "TRUNK STORAGE",
        "price": 1,
        "description": "Store weapons in your trunk",
        "storage_type": "trunk"
    }
}

# Storage select dropdown
class StorageSelect(discord.ui.Select):
    def __init__(self, user_id, selected_storage=None):
        self.user_id = user_id
        self.selected_storage = selected_storage

        options = []
        for package_id, package_info in PACKAGE_DATA.items():
            is_selected = package_id == self.selected_storage
            label = f"✅ {package_info['name']}" if is_selected else package_info['name']
            options.append(discord.SelectOption(
                label=label,
                value=package_id,
                description=f"${package_info['price']} - {package_info['description']}",
                emoji="📦"
            ))

        super().__init__(
            placeholder="Select storage type for your weapons...",
            min_values=0,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            if self.user_id and interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your shop session!", ephemeral=True)
                return

            self.selected_storage = self.values[0] if self.values else None

            # Get the parent view and update storage
            view = interaction.message.view
            if hasattr(view, 'selected_storage'):
                view.selected_storage = self.selected_storage

            # Update embed and view
            embed = view.create_weapon_embed()
            await interaction.response.edit_message(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in StorageSelect callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

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

class WeaponShopView(discord.ui.View):
    def __init__(self, user_id, selected_weapons=None, selected_storage=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.selected_weapons = selected_weapons or set()
        self.selected_storage = selected_storage

        # Add the weapon select dropdown with user_id
        self.add_item(WeaponSelect(self.selected_weapons, self.user_id))

        # Add storage select dropdown
        self.add_item(StorageSelect(self.user_id, self.selected_storage))

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

        # Storage selection display
        if self.selected_storage:
            storage_info = PACKAGE_DATA[self.selected_storage]
            embed.add_field(
                name="📦 SELECTED STORAGE",
                value=f"✅ {storage_info['name']} - ${storage_info['price']}\n{storage_info['description']}",
                inline=True
            )
        else:
            embed.add_field(
                name="📦 SELECT STORAGE",
                value="🔥 **SAFE:** $3\n💼 **BAG:** $2\n🚛 **TRUNK:** $1",
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

            if not self.selected_weapons and not self.selected_storage:
                await interaction.response.send_message("❌ Pick some weapons or storage first!", ephemeral=True)
                return

            # Add to cart
            if interaction.user.id not in bot.user_carts:
                bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}

            if self.selected_weapons:
                bot.user_carts[interaction.user.id]["weapons"].update(self.selected_weapons)

            if self.selected_storage:
                bot.user_carts[interaction.user.id]["packages"].add(self.selected_storage)

            message = f"✅ Added "
            if self.selected_weapons:
                message += f"{len(self.selected_weapons)} weapons"
            if self.selected_storage:
                storage_name = PACKAGE_DATA[self.selected_storage]['name']
                if self.selected_weapons:
                    message += f" + {storage_name}"
                else:
                    message += storage_name
            message += "!"

            await interaction.response.send_message(message, ephemeral=True)
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

    def auto_add_to_cart(self, user_id):
        """Automatically add selected money to cart"""
        if user_id not in bot.user_carts:
            bot.user_carts[user_id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}

        if self.selected_money:
            bot.user_carts[user_id]["money"].update(self.selected_money)


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
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}

        bot.user_carts[interaction.user.id]["money"].update(self.selected_money)
        await interaction.response.send_message(f"✅ Added {len(self.selected_money)} packages!", ephemeral=True)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Auto-add items to cart before going back
        self.auto_add_to_cart(interaction.user.id)

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
            bot.user_carts[interaction.user.id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}

        if self.selected_watch not in bot.user_carts[interaction.user.id]["watches"]:
            bot.user_carts[interaction.user.id]["watches"].add(self.selected_watch)
            await interaction.response.send_message(f"✅ Added watch to cart!", ephemeral=True)
        else:
            await interaction.response.send_message("Already in cart!", ephemeral=True)

    def auto_add_to_cart(self, user_id):
        """Automatically add selected watch to cart"""
        if user_id not in bot.user_carts:
            bot.user_carts[user_id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}

        if self.selected_watch:
            bot.user_carts[user_id]["watches"].add(self.selected_watch)

    @discord.ui.button(label='◀️ BACK', style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Auto-add items to cart before going back
        self.auto_add_to_cart(interaction.user.id)

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

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None})
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

        # Storage packages
        if cart["packages"]:
            items.append(f"📦 **STORAGE** ({len(cart['packages'])})")
            for package_id in cart["packages"]:
                if package_id in PACKAGE_DATA:
                    package_info = PACKAGE_DATA[package_id]
                    items.append(f"  • {package_info['name']} - ${package_info['price']}")
                    total += package_info["price"]

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

        cart = bot.user_carts.get(self.user_id, {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None})

        if not any([cart["weapons"], cart["money"], cart["watches"], cart["packages"]]):
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
                bot.user_carts[self.user_id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}
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

        bot.user_carts[self.user_id] = {"weapons": set(), "money": set(), "watches": set(), "packages": set(), "hub": None}
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
        view = MoneyShopView(interaction.user.id)
        embed = view.create_money_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='📦 PREMIUM', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def other_tab(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OtherShopView(interaction.user_id)
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
            value="💀 **ZPOFE** • ⚡ **DROW**",
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
        view = OtherShopView(interaction.user_id)
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
        title=" postureProxy STK TRYOUT STARTED!",
        description="**Your tryout has been created**\n\n**WAIT FOR ALL 3 STK MEMBERS TO JOIN**",
        color=0xFF0000,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.add_field(
        name="👤 Applicant",
        value=f"{user.mention}\n`{user.id}`",
        inline=True
    )

    embed.add_field(
        name="⏰ Tryout Time",
        value=f"<t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:F>",
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

    # Process packages first
    packages_list = []
    if cart["packages"]:
        for package_id in cart["packages"]:
            if package_id in PACKAGE_DATA:
                package_info = PACKAGE_DATA[package_id]
                packages_list.append(f"{package_info['name']} - ${package_info['price']}")
                total += package_info["price"]

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
        title="📋 ORDER SUMMARY",
        description=f"**Customer:** {user.mention} (`{user.id}`)\n**Order Time:** <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:F>",
        color=0x00ff00,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    # Add packages section
    if packages_list:
        packages_text = "\n".join([f"• {package}" for package in packages_list])
        order_embed.add_field(
            name=f"📦 PACKAGES ({len(packages_list)})",
            value=packages_text,
            inline=False
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
        value="1️⃣ Click payment button below\n2️⃣ Send the exact amount\n3️⃣ Screenshot proof\n4️⃣ Send proof in this ticket",
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
            value="Zpofe/Drow will **join your server**\nThey will **dupe and give** your weapons",
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

# Verification Button View
class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ VERIFY', style=discord.ButtonStyle.success, custom_id='verify_user', emoji='🔓')
    async def verify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            AUTO_ROLE_ID = 1406380208507977899  # Unverified role
            VERIFIED_ROLE_ID = 1399949469532946483  # Verified role
            
            auto_role = interaction.guild.get_role(AUTO_ROLE_ID)
            verified_role = interaction.guild.get_role(VERIFIED_ROLE_ID)
            
            if not verified_role:
                await interaction.response.send_message("❌ Verified role not found! Contact an admin.", ephemeral=True)
                return
            
            # Check if user already verified
            if verified_role in interaction.user.roles:
                await interaction.response.send_message("✅ You're already verified! You have access to all channels.", ephemeral=True)
                return
            
            # Remove auto-role and add verified role
            roles_to_remove = []
            roles_to_add = [verified_role]
            
            if auto_role and auto_role in interaction.user.roles:
                roles_to_remove.append(auto_role)
            
            # Remove unverified role
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove, reason="User verified - removing unverified role")
            
            # Add verified role
            await interaction.user.add_roles(*roles_to_add, reason="User completed verification")
            
            # Create success embed
            embed = discord.Embed(
                title="✅ VERIFICATION COMPLETE!",
                description="**Welcome to STK Supply!**\n\nYou now have access to all channels in the server.",
                color=0x00FF00,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            
            embed.add_field(
                name="🎉 Access Granted",
                value="• All text channels unlocked\n• All voice channels available\n• Full server access enabled",
                inline=False
            )
            
            embed.add_field(
                name="🔥 What's Next?",
                value="• Check out the shop for services\n• Read server rules and info\n• Join the community!",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="STK Supply • Successfully Verified", icon_url=interaction.guild.me.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"User {interaction.user.display_name} ({interaction.user.id}) successfully verified")
            
        except Exception as e:
            logger.error(f"Error in verification: {e}")
            await interaction.response.send_message("❌ Verification failed. Please contact an admin.", ephemeral=True)

# Setup verification system command
@bot.tree.command(name="setup_verification_system", description="Setup the verification system with button")
async def setup_verification_system(interaction: discord.Interaction):
    """Setup the verification system"""
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

        await interaction.response.send_message("🔄 Setting up verification system...", ephemeral=True)

        # Create verification embed
        embed = discord.Embed(
            title="🔓 SERVER VERIFICATION",
            description="**Click the button below to verify and gain access to all channels!**",
            color=0x39FF14,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="⚠️ Verification Required",
            value="You must verify to access other channels in this server.\nThis is a one-time process.",
            inline=False
        )

        embed.add_field(
            name="✅ After Verification",
            value="• Access to all text channels\n• Access to all voice channels\n• Full server participation\n• Shop and services access",
            inline=False
        )

        embed.add_field(
            name="🔒 Current Access",
            value="Until you verify, you can only see this channel.",
            inline=False
        )

        embed.set_footer(text="STK Supply • Verification System", icon_url=interaction.guild.me.display_avatar.url)

        # Create the view with verification button
        view = VerificationView()
        
        # Send the verification message
        await interaction.channel.send(embed=embed, view=view)
        await interaction.edit_original_response(content="✅ **Verification system setup complete!**")

    except Exception as e:
        logger.error(f"Error in setup_verification_system command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
            else:
                await interaction.edit_original_response(content="❌ Some shit went wrong.")
        except discord.NotFound:
            logger.error("Could not send error message")

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

# Admin Action Modals
class WarnModal(discord.ui.Modal):
    def __init__(self, target_user_id: int):
        super().__init__(title="Warn User")
        self.target_user_id = target_user_id

        self.reason = discord.ui.TextInput(
            label="Warning Reason",
            placeholder="Enter the reason for this warning...",
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_user = await bot.fetch_user(self.target_user_id)
            if not target_user:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            # Create warning embed
            embed = discord.Embed(
                title="⚠️ USER WARNED",
                description=f"**User:** {target_user.mention}\n**Reason:** {self.reason.value}\n**Warned by:** {interaction.user.mention}",
                color=0xFFFF00,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"User {interaction.user.id} warned {target_user.id} for: {self.reason.value}")

        except Exception as e:
            logger.error(f"Error warning user: {e}")
            await interaction.response.send_message("❌ Failed to warn user.", ephemeral=True)

class KickModal(discord.ui.Modal):
    def __init__(self, target_user_id: int):
        super().__init__(title="Kick User")
        self.target_user_id = target_user_id

        self.reason = discord.ui.TextInput(
            label="Kick Reason",
            placeholder="Enter the reason for kicking this user...",
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_member = interaction.guild.get_member(self.target_user_id)
            if not target_member:
                await interaction.response.send_message("User not found in this server.", ephemeral=True)
                return

            reason = f"Kicked by {interaction.user.display_name}: {self.reason.value}"
            await target_member.kick(reason=reason)

            embed = discord.Embed(
                title="👢 USER KICKED",
                description=f"**User:** {target_member.mention}\n**Reason:** {self.reason.value}\n**Kicked by:** {interaction.user.mention}",
                color=0xFF0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"User {interaction.user.id} kicked {target_member.id} for: {self.reason.value}")

        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permissions to kick this user.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
            await interaction.response.send_message("❌ Failed to kick user.", ephemeral=True)

class BanModal(discord.ui.Modal):
    def __init__(self, target_user_id: int):
        super().__init__(title="Ban User")
        self.target_user_id = target_user_id

        self.reason = discord.ui.TextInput(
            label="Ban Reason",
            placeholder="Enter the reason for banning this user...",
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_member = interaction.guild.get_member(self.target_user_id)
            target_user = await bot.fetch_user(self.target_user_id)
            
            if not target_user:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            reason = f"Banned by {interaction.user.display_name}: {self.reason.value}"
            await interaction.guild.ban(target_user, reason=reason)

            embed = discord.Embed(
                title="⚖️ USER BANNED",
                description=f"**User:** {target_user.mention}\n**Reason:** {self.reason.value}\n**Banned by:** {interaction.user.mention}",
                color=0x8B0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"User {interaction.user.id} banned {target_user.id} for: {self.reason.value}")

        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permissions to ban this user.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await interaction.response.send_message("❌ Failed to ban user.", ephemeral=True)

class TimeoutModal(discord.ui.Modal):
    def __init__(self, target_user_id: int):
        super().__init__(title="Timeout User")
        self.target_user_id = target_user_id

        self.duration = discord.ui.TextInput(
            label="Timeout Duration (minutes)",
            placeholder="Enter timeout duration in minutes (max 40320)...",
            max_length=10
        )
        self.add_item(self.duration)

        self.reason = discord.ui.TextInput(
            label="Timeout Reason",
            placeholder="Enter the reason for this timeout...",
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_member = interaction.guild.get_member(self.target_user_id)
            if not target_member:
                await interaction.response.send_message("User not found in this server.", ephemeral=True)
                return

            # Parse duration
            try:
                duration_minutes = int(self.duration.value)
                if duration_minutes <= 0 or duration_minutes > 40320:  # Discord's max timeout
                    await interaction.response.send_message("❌ Duration must be between 1 and 40320 minutes (28 days).", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Please enter a valid number for duration.", ephemeral=True)
                return

            # Calculate timeout until datetime
            timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=duration_minutes)
            
            reason = f"Timed out by {interaction.user.display_name}: {self.reason.value}"
            await target_member.timeout(timeout_until, reason=reason)

            embed = discord.Embed(
                title="⏳ USER TIMED OUT",
                description=f"**User:** {target_member.mention}\n**Duration:** {duration_minutes} minutes\n**Reason:** {self.reason.value}\n**Timed out by:** {interaction.user.mention}",
                color=0xFFA500,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"User {interaction.user.id} timed out {target_member.id} for {duration_minutes} minutes: {self.reason.value}")

        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permissions to timeout this user.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error timing out user: {e}")
            await interaction.response.send_message("❌ Failed to timeout user.", ephemeral=True)

class RewardModal(discord.ui.Modal):
    def __init__(self, target_user_id: int):
        super().__init__(title="Give Achievement Reward")
        self.target_user_id = target_user_id

        self.achievement = discord.ui.TextInput(
            label="Achievement Name",
            placeholder="Enter the achievement to give...",
            max_length=100
        )
        self.add_item(self.achievement)

        self.description = discord.ui.TextInput(
            label="Achievement Description (Optional)",
            placeholder="Enter a description for this achievement...",
            max_length=200,
            required=False,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_user = await bot.fetch_user(self.target_user_id)
            if not target_user:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            # Auto-detect members and get user's card
            auto_detect_members(interaction.guild)
            member_key = get_user_card_key(self.target_user_id)
            
            # Add achievement to user's card
            achievement_text = self.achievement.value
            if self.description.value:
                achievement_text += f" - {self.description.value}"

            # Check if achievement already exists
            if achievement_text not in STK_DIRECTORY[member_key]["achievements"]:
                STK_DIRECTORY[member_key]["achievements"].append(achievement_text)

                embed = discord.Embed(
                    title="🎁 ACHIEVEMENT AWARDED",
                    description=f"**User:** {target_user.mention}\n**Achievement:** {achievement_text}\n**Awarded by:** {interaction.user.mention}",
                    color=0x00FF00,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )

                await interaction.response.send_message(embed=embed)
                logger.info(f"User {interaction.user.id} gave achievement '{achievement_text}' to {target_user.id}")
            else:
                await interaction.response.send_message("❌ User already has this achievement.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error giving achievement: {e}")
            await interaction.response.send_message("❌ Failed to give achievement.", ephemeral=True)

# Card Editing Views and Components
class CardEditModal(discord.ui.Modal):
    def __init__(self, member_key: str, field_type: str, current_value: str = "", user_id: int = None, edit_view=None):
        super().__init__(title=f"Edit {field_type.title()}")
        self.member_key = member_key
        self.field_type = field_type
        self.user_id = user_id
        self.edit_view = edit_view

        if field_type == "description":
            self.field = discord.ui.TextInput(
                label="Description",
                placeholder="Enter member description...",
                default=current_value,
                max_length=200,
                style=discord.TextStyle.paragraph
            )
        elif field_type == "role":
            self.field = discord.ui.TextInput(
                label="Role",
                placeholder="Enter member role...",
                default=current_value,
                max_length=100
            )
        elif field_type == "status":
            self.field = discord.ui.TextInput(
                label="Status",
                placeholder="Active, Inactive, etc...",
                default=current_value,
                max_length=50
            )
        elif field_type == "card_image":
            self.field = discord.ui.TextInput(
                label="Card Image URL",
                placeholder="https://example.com/image.gif",
                default=current_value,
                max_length=500
            )

        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Only allow users to edit their own cards
            if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
                await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
                return

            # Store change temporarily in edit view
            if self.edit_view:
                self.edit_view.pending_changes[self.field_type] = self.field.value

            await interaction.response.send_message(f"✅ {self.field_type.title()} staged for update. Click 'Confirm Changes' to save all changes.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error staging card change: {e}")
            await interaction.response.send_message("❌ Failed to stage change.", ephemeral=True)

class SpecialtiesEditModal(discord.ui.Modal):
    def __init__(self, member_key: str, current_specialties: list, user_id: int = None, edit_view=None):
        super().__init__(title="Edit Specialties")
        self.member_key = member_key
        self.user_id = user_id
        self.edit_view = edit_view

        specialties_text = "\n".join(current_specialties)
        self.specialties_field = discord.ui.TextInput(
            label="Specialties (one per line)",
            placeholder="Development\nConnections\nCustomer Service",
            default=specialties_text,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.specialties_field)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Only allow users to edit their own cards
            if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
                await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
                return

            # Convert text to list and store temporarily
            new_specialties = [specialty.strip() for specialty in self.specialties_field.value.split('\n') if specialty.strip()]
            if self.edit_view:
                self.edit_view.pending_changes["specialties"] = new_specialties

            await interaction.response.send_message("✅ Specialties staged for update. Click 'Confirm Changes' to save all changes.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error staging specialties change: {e}")
            await interaction.response.send_message("❌ Failed to stage change.", ephemeral=True)

class AchievementsEditModal(discord.ui.Modal):
    def __init__(self, member_key: str, current_achievements: list, user_id: int = None, edit_view=None):
        super().__init__(title="Edit Achievements")
        self.member_key = member_key
        self.user_id = user_id
        self.edit_view = edit_view

        achievements_text = "\n".join(current_achievements)
        self.achievements_field = discord.ui.TextInput(
            label="Achievements (one per line)",
            placeholder="Bot Developer\nTop Seller\nElite Status",
            default=achievements_text,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.achievements_field)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Only allow users to edit their own cards
            if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
                await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
                return

            # Convert text to list and store temporarily
            new_achievements = [achievement.strip() for achievement in self.achievements_field.value.split('\n') if achievement.strip()]
            if self.edit_view:
                self.edit_view.pending_changes["achievements"] = new_achievements

            await interaction.response.send_message("✅ Achievements staged for update. Click 'Confirm Changes' to save all changes.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error staging achievements change: {e}")
            await interaction.response.send_message("❌ Failed to stage change.", ephemeral=True)

class ColorSelectView(discord.ui.View):
    def __init__(self, member_key: str, user_id: int = None, edit_view=None):
        super().__init__(timeout=300)
        self.member_key = member_key
        self.user_id = user_id
        self.edit_view = edit_view

    @discord.ui.button(label='🔴 Red', style=discord.ButtonStyle.danger)
    async def red_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0xFF0000)

    @discord.ui.button(label='🟢 Green', style=discord.ButtonStyle.success)
    async def green_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0x00FF00)

    @discord.ui.button(label='🔵 Blue', style=discord.ButtonStyle.primary)
    async def blue_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0x0000FF)

    @discord.ui.button(label='🟡 Gold', style=discord.ButtonStyle.secondary)
    async def gold_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0xFFD700)

    @discord.ui.button(label=' purple', style=discord.ButtonStyle.secondary)
    async def purple_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0x9932CC)

    @discord.ui.button(label='🟠 Orange', style=discord.ButtonStyle.secondary)
    async def orange_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0xFF6600)

    @discord.ui.button(label='⚫ Black', style=discord.ButtonStyle.secondary)
    async def black_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0x000000)

    @discord.ui.button(label='⚪ White', style=discord.ButtonStyle.secondary)
    async def white_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_color(interaction, 0xFFFFFF)

    async def update_color(self, interaction: discord.Interaction, color: int):
        try:
            # Only allow users to edit their own cards
            if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
                await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
                return

            # Store color change temporarily
            if self.edit_view:
                self.edit_view.pending_changes["color"] = color

            await interaction.response.send_message("✅ Color staged for update. Click 'Confirm Changes' to save all changes.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error staging color change: {e}")
            await interaction.response.send_message("❌ Failed to stage change.", ephemeral=True)

class CardEditView(discord.ui.View):
    def __init__(self, member_key: str, user_id: int = None):
        super().__init__(timeout=300)
        self.member_key = member_key
        self.user_id = user_id
        self.pending_changes = {}  # Store pending changes before confirmation

    @discord.ui.button(label='📝 Edit Description', style=discord.ButtonStyle.secondary, row=0)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        current_value = STK_DIRECTORY[self.member_key].get("description", "")
        modal = CardEditModal(self.member_key, "description", current_value, interaction.user.id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='💼 Edit Role', style=discord.ButtonStyle.secondary, row=0)
    async def edit_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        current_value = STK_DIRECTORY[self.member_key].get("role", "")
        modal = CardEditModal(self.member_key, "role", current_value, interaction.user.id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='📊 Edit Status', style=discord.ButtonStyle.secondary, row=0)
    async def edit_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        current_value = STK_DIRECTORY[self.member_key].get("status", "")
        modal = CardEditModal(self.member_key, "status", current_value, interaction.user.id, self)
        await interaction.response.send_modal(modal)

    # Join date editing removed - this should only be set by admins

    @discord.ui.button(label='🖼️ Edit Image', style=discord.ButtonStyle.secondary, row=1)
    async def edit_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        current_value = STK_DIRECTORY[self.member_key].get("card_image", "")
        modal = CardEditModal(self.member_key, "card_image", current_value, interaction.user.id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🎯 Edit Specialties', style=discord.ButtonStyle.primary, row=2)
    async def edit_specialties(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        current_specialties = STK_DIRECTORY[self.member_key].get("specialties", [])
        modal = SpecialtiesEditModal(self.member_key, current_specialties, interaction.user.id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🏅 View Achievements', style=discord.ButtonStyle.secondary, row=2)
    async def view_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow viewing own card achievements
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only view your own achievements.", ephemeral=True)
            return

        current_achievements = STK_DIRECTORY[self.member_key].get("achievements", [])
        
        embed = discord.Embed(
            title="🏆 Your Achievements",
            description="**Achievements are awarded by admins only**",
            color=STK_DIRECTORY[self.member_key]["color"]
        )

        if current_achievements:
            achievement_list = "\n".join([f"🔥 {achievement}" for achievement in current_achievements])
            embed.add_field(
                name="🏅 Earned Achievements",
                value=achievement_list,
                inline=False
            )
        else:
            embed.add_field(
                name="🏅 No Achievements Yet",
                value="Keep contributing to earn achievements from admins!",
                inline=False
            )

        embed.set_footer(text="STK Supply • Achievements are admin-awarded only")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='🎨 Change Color', style=discord.ButtonStyle.primary, row=2)
    async def change_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow editing own card
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        color_view = ColorSelectView(self.member_key, interaction.user.id, self)
        embed = discord.Embed(
            title="🎨 Choose Your Card Color",
            description="Select a color for your member card:",
            color=STK_DIRECTORY[self.member_key]["color"]
        )
        await interaction.response.send_message(embed=embed, view=color_view, ephemeral=True)

    @discord.ui.button(label='👁️ Preview Card', style=discord.ButtonStyle.success, row=3)
    async def preview_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show updated card preview with pending changes
        member_data = STK_DIRECTORY[self.member_key].copy()

        # Apply pending changes to preview
        for field, value in self.pending_changes.items():
            member_data[field] = value

        user_id = member_data["user_id"]

        # Try to get the Discord user
        try:
            discord_user = await bot.fetch_user(user_id)
            username = discord_user.display_name
            avatar_url = discord_user.display_avatar.url
        except:
            username = f"User {user_id}"
            avatar_url = None

        # Create professional member card
        embed = discord.Embed(
            title=f"{member_data['rank']}",
            description=f"**{member_data['role']}**\n{member_data['description']}",
            color=member_data['color'],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Set user avatar if available
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        # Member info
        embed.add_field(
            name="👤 Member Info",
            value=f"**Discord:** <@{user_id}>\n**Status:** {member_data['status']}\n**Joined STK:** {member_data['joined']}",
            inline=True
        )

        # Specialties
        embed.add_field(
            name="🎯 Specialties",
            value="\n".join([f"• {specialty}" for specialty in member_data['specialties']]),
            inline=True
        )

        # Earned Rewards
        embed.add_field(
            name="🏆 Earned Rewards",
            value="\n".join([f"🔥 {achievement}" for achievement in member_data['achievements']]) if member_data['achievements'] else "No rewards earned yet",
            inline=False
        )

        # STK branding
        embed.set_footer(
            text="STK Supply • Official Directory • Your Card Preview (With Pending Changes)",
            icon_url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif"
        )

        # Add card image if available
        if member_data.get("card_image"):
            embed.set_image(url=member_data["card_image"])

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='✅ CONFIRM CHANGES', style=discord.ButtonStyle.success, row=4)
    async def confirm_changes(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow users to edit their own cards
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        if not self.pending_changes:
            await interaction.response.send_message("❌ No changes to save.", ephemeral=True)
            return

        try:
            # Apply all pending changes to the actual directory
            for field, value in self.pending_changes.items():
                STK_DIRECTORY[self.member_key][field] = value

            # Create confirmation message
            changes_list = []
            for field, value in self.pending_changes.items():
                if field == "specialties" or field == "achievements":
                    changes_list.append(f"**{field.title()}:** {len(value)} items")
                else:
                    changes_list.append(f"**{field.title()}:** Updated")

            embed = discord.Embed(
                title="✅ CHANGES SAVED",
                description="Your card has been successfully updated!",
                color=0x00FF00
            )

            embed.add_field(
                name="📝 Applied Changes",
                value="\n".join(changes_list),
                inline=False
            )

            embed.set_footer(text="STK Supply • Card Updated Successfully")

            # Clear pending changes
            self.pending_changes = {}

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"User {interaction.user.id} confirmed card changes for {self.member_key}")

        except Exception as e:
            logger.error(f"Error confirming card changes: {e}")
            await interaction.response.send_message("❌ Failed to save changes.", ephemeral=True)

    @discord.ui.button(label='❌ DISCARD CHANGES', style=discord.ButtonStyle.danger, row=4)
    async def discard_changes(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow users to edit their own cards
        if STK_DIRECTORY[self.member_key]["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ You can only edit your own card.", ephemeral=True)
            return

        if not self.pending_changes:
            await interaction.response.send_message("❌ No changes to discard.", ephemeral=True)
            return

        # Clear pending changes
        discarded_count = len(self.pending_changes)
        self.pending_changes = {}

        embed = discord.Embed(
            title="❌ CHANGES DISCARDED",
            description=f"Discarded {discarded_count} pending change(s).",
            color=0xFF0000
        )
        embed.set_footer(text="STK Supply • Changes Discarded")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"User {interaction.user.id} discarded card changes for {self.member_key}")

# Function to automatically detect and add new members
def auto_detect_members(guild):
    """Automatically detect new members and add them to directory"""
    if not guild:
        return

    # Get all members from the guild
    for member in guild.members:
        if member.bot:
            continue

        # Check if member is already in directory
        member_exists = False
        for member_key, member_data in STK_DIRECTORY.items():
            if member_data["user_id"] == member.id:
                member_exists = True
                break

        # If not in directory, add as new member
        if not member_exists:
            member_key = f"member_{member.id}"
            STK_DIRECTORY[member_key] = {
                "user_id": member.id,
                "rank": "👤 Member 👤",
                "role": "",
                "description": "",
                "specialties": [],
                "status": "",
                "joined": "2025",
                "achievements": [],
                "color": 0x808080,
                "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif"
            }
            logger.info(f"Auto-added new member: {member.display_name} ({member.id})")

# Function to get user's own card key
def get_user_card_key(user_id: int) -> str:
    """Get the card key for a user's own card"""
    for member_key, member_data in STK_DIRECTORY.items():
        if member_data["user_id"] == user_id:
            return member_key

    # If user not found, create new member entry
    member_key = f"member_{user_id}"
    STK_DIRECTORY[member_key] = {
        "user_id": user_id,
        "rank": "👤 Member 👤",
        "role": "",
        "description": "",
        "specialties": [],
        "status": "",
        "joined": "2025",
        "achievements": [],
        "color": 0x808080,
        "card_image": "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif"
    }
    logger.info(f"Auto-created card for user: {user_id}")
    return member_key

# User directory command - shows Discord members only
@bot.tree.command(name="user", description="Display user profile card")
@app_commands.describe(user="Select a Discord user to view their profile (optional - defaults to your own card)")
async def user_directory(interaction: discord.Interaction, user: discord.Member = None):
    """Display user profile card"""
    try:
        # Check if interaction is already responded to or expired
        if interaction.response.is_done():
            return

        # If no user specified, show interaction user's card
        target_user = user or interaction.user

        # Auto-detect members when command is used
        auto_detect_members(interaction.guild)

        # Get user's card key
        member_key = get_user_card_key(target_user.id)
        member_data = STK_DIRECTORY[member_key]

        # Check if the target user is an admin (or has a specific role to be modded)
        is_admin = False
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184] # Example admin IDs
        if target_user.id in admin_ids:
            is_admin = True

        # Create user profile card
        embed = discord.Embed(
            title=f"{member_data['rank']}",
            description=f"**{member_data['role']}**\n{member_data['description']}",
            color=member_data['color'],
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Set user avatar
        embed.set_thumbnail(url=target_user.display_avatar.url)

        # Member info
        embed.add_field(
            name="👤 User Info",
            value=f"**Discord:** {target_user.mention}\n**Status:** {member_data['status']}\n**Joined:** {member_data['joined']}",
            inline=True
        )

        # Specialties
        embed.add_field(
            name="🎯 Specialties",
            value="\n".join([f"• {specialty}" for specialty in member_data['specialties']]) if member_data['specialties'] else "No specialties listed",
            inline=True
        )

        # Earned Rewards
        embed.add_field(
            name="🏆 Earned Rewards",
            value="\n".join([f"🔥 {achievement}" for achievement in member_data['achievements']]) if member_data['achievements'] else "No rewards earned yet",
            inline=False
        )

        # STK branding
        embed.set_footer(
            text="STK Supply • User Directory",
            icon_url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif"
        )

        # Add custom card image if available
        card_image = member_data.get("card_image", "https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
        embed.set_image(url=card_image)

        # Add admin buttons if the user is an admin and the target is not themselves
        if is_admin and target_user.id != interaction.user.id:
            admin_view = AdminManagementView(target_user.id)
            await interaction.response.send_message(embed=embed, view=admin_view)
        else:
            await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error in user_directory command: {e}")
        # Only try to respond if interaction is still valid
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
        except (discord.NotFound, discord.HTTPException):
            # Interaction expired or already handled - this is normal
            pass

# Admin management view
class AdminManagementView(discord.ui.View):
    def __init__(self, target_user_id: int):
        super().__init__(timeout=180)
        self.target_user_id = target_user_id

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, emoji="👢", row=0)
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184]
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message("❌ Only admins can use this action.", ephemeral=True)
            return

        modal = KickModal(self.target_user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="⚖️", row=0)
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184]
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message("❌ Only admins can use this action.", ephemeral=True)
            return

        modal = BanModal(self.target_user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Warn", style=discord.ButtonStyle.secondary, emoji="⚠️", row=0)
    async def warn_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184]
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message("❌ Only admins can use this action.", ephemeral=True)
            return

        modal = WarnModal(self.target_user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Timeout", style=discord.ButtonStyle.secondary, emoji="⏳", row=1)
    async def timeout_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184]
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message("❌ Only admins can use this action.", ephemeral=True)
            return

        modal = TimeoutModal(self.target_user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Give Reward", style=discord.ButtonStyle.success, emoji="🎁", row=1)
    async def give_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        admin_ids = [954818761729376357, 1385239185006268457, 666394721039417346, 1394285950464426066, 1106038406317871184]
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message("❌ Only admins can use this action.", ephemeral=True)
            return

        modal = RewardModal(self.target_user_id)
        await interaction.response.send_modal(modal)


# Edit Card Command - Users can only edit their own card
@bot.tree.command(name="editcard", description="Edit your STK member directory card")
async def edit_card(interaction: discord.Interaction):
    """Edit your own STK member directory card"""
    try:
        # Auto-detect members when command is used
        auto_detect_members(interaction.guild)

        # Get user's own card
        member_key = get_user_card_key(interaction.user.id)
        member_data = STK_DIRECTORY[member_key]

        # Create edit interface for user's own card
        edit_view = CardEditView(member_key, interaction.user.id)
        embed = discord.Embed(
            title=f"🛠️ Editing Your Card: {member_data['rank']}",
            description="**Your Card Editor**\nCustomize your member card below:",
            color=member_data['color']
        )

        embed.add_field(
            name="📝 Current Info",
            value=f"**Role:** {member_data['role']}\n**Status:** {member_data['status']}\n**Joined:** {member_data['joined']}",
            inline=True
        )

        embed.add_field(
            name="🎯 Current Specialties",
            value="\n".join([f"• {specialty}" for specialty in member_data['specialties'][:3]]) +
                  (f"\n• ...and {len(member_data['specialties']) - 3} more" if len(member_data['specialties']) > 3 else ""),
            inline=True
        )

        # Earned Rewards
        embed.add_field(
            name="🏆 Earned Rewards",
            value="\n".join([f"🔥 {achievement}" for achievement in member_data['achievements']]) if member_data['achievements'] else "No rewards earned yet",
            inline=False
        )

        embed.add_field(
            name="⚠️ Note",
            value="You can only edit your own card.\nRank, join date, and achievements cannot be changed.\nAchievements are awarded by admins only.",
            inline=False
        )

        embed.set_footer(text="STK Supply • Your Card Editor • Changes save automatically")

        await interaction.response.send_message(embed=embed, view=edit_view, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in edit_card command: {e}")
        await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)


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
            timestamp=datetime.datetime.now(datetime.timezone.utc)
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
            timestamp=datetime.datetime.now(datetime.datetime.now(datetime.timezone.utc))
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
            timestamp=datetime.datetime.now(datetime.timezone.utc)
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
            timestamp=datetime.datetime.now(datetime.timezone.utc)
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
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await interaction.response.send_message(embed=embed)



# Bot bio command - shows cool STK information
@bot.tree.command(name="fixperms", description="Fix member channel permissions (admin only)")
async def fix_permissions(interaction: discord.Interaction):
    """Fix member channel permissions"""
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

        await interaction.response.send_message("🔧 Checking member permissions...", ephemeral=True)

        AUTO_ROLE_ID = 1406380208507977899  # Unverified role
        VERIFIED_ROLE_ID = 1399949469532946483  # Verified role
        
        auto_role = interaction.guild.get_role(AUTO_ROLE_ID)
        verified_role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        
        if not auto_role:
            await interaction.edit_original_response(content="❌ Unverified role not found! Create role with ID 1406380208507977899")
            return

        if not verified_role:
            await interaction.edit_original_response(content="❌ Verified role not found! Create role with ID 1399949469532946483")
            return

        # Check members who need unverified role (don't have verified role and don't have auto role)
        members_fixed = 0
        for member in interaction.guild.members:
            if member.bot:
                continue
            
            # If member doesn't have verified role and doesn't have auto role, give them auto role
            if verified_role not in member.roles and auto_role not in member.roles:
                try:
                    await member.add_roles(auto_role, reason="Fixed missing unverified role - needs verification")
                    members_fixed += 1
                    await asyncio.sleep(0.5)  # Rate limit protection
                except Exception as e:
                    logger.error(f"Failed to assign role to {member.display_name}: {e}")

        embed = discord.Embed(
            title="✅ PERMISSIONS FIXED",
            description=f"**Fixed {members_fixed} members**",
            color=0x00FF00
        )

        embed.add_field(
            name="🔧 Actions Taken",
            value=f"• Added unverified role to {members_fixed} members who need to verify\n• Unverified Role: {auto_role.name}\n• Verified Role: {verified_role.name}\n• Members with unverified role can only see verification channel",
            inline=False
        )

        embed.add_field(
            name="ℹ️ Verification System",
            value="• Members without verified role get unverified role\n• Unverified members can only see verification channel\n• They must click verify button to get full access\n• Verified members see all channels",
            inline=False
        )

        await interaction.edit_original_response(content="", embed=embed)
        logger.info(f"Fixed permissions for {members_fixed} members")

    except Exception as e:
        logger.error(f"Error in fix_permissions command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
        else:
            await interaction.edit_original_response(content="❌ Some shit went wrong.")

@bot.tree.command(name="setup_verification", description="Configure server so unverified users only see verification channel (admin only)")
async def setup_verification(interaction: discord.Interaction):
    """Configure server permissions so unverified users only see verification channel"""
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

        await interaction.response.send_message("🔄 Setting up verification-only permissions...", ephemeral=True)

        guild = interaction.guild
        VERIFICATION_CHANNEL_ID = 1398741781331447890  # Verification channel
        AUTO_ROLE_ID = 1406380208507977899  # Unverified role (can only see verification channel)
        VERIFIED_ROLE_ID = 1399949469532946483  # Verified role (can see all channels)
        
        verification_channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
        auto_role = guild.get_role(AUTO_ROLE_ID)
        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        
        if not verification_channel:
            await interaction.edit_original_response(content="❌ Verification channel not found! Check channel ID 1398741781331447890")
            return
            
        if not auto_role:
            await interaction.edit_original_response(content="❌ Unverified role not found! Create role with ID 1406380208507977899")
            return

        if not verified_role:
            await interaction.edit_original_response(content="❌ Verified role not found! Create role with ID 1399949469532946483")
            return

        changes_made = 0
        errors = []

        # Step 1: Set @everyone to see ONLY verification channel
        try:
            # Remove @everyone from seeing all other channels except verification
            for channel in guild.text_channels:
                if channel.id != VERIFICATION_CHANNEL_ID:
                    # Deny @everyone from seeing other channels
                    await channel.set_permissions(guild.default_role, read_messages=False, reason="Verification setup - hide from unverified")
                    changes_made += 1
                    await asyncio.sleep(0.1)  # Rate limit protection
                else:
                    # Allow @everyone to see verification channel
                    await channel.set_permissions(guild.default_role, read_messages=True, send_messages=True, reason="Verification setup - allow verification channel")
                    changes_made += 1

            # Do the same for voice channels
            for channel in guild.voice_channels:
                await channel.set_permissions(guild.default_role, view_channel=False, reason="Verification setup - hide voice from unverified")
                changes_made += 1
                await asyncio.sleep(0.1)

        except Exception as e:
            errors.append(f"Channel permissions: {str(e)[:100]}")

        # Step 2: Set auto-role (unverified) to ONLY see verification channel
        try:
            for channel in guild.text_channels:
                if channel.id != VERIFICATION_CHANNEL_ID:
                    # Deny auto-role (unverified users) from seeing other channels
                    await channel.set_permissions(auto_role, read_messages=False, reason="Verification setup - unverified users only see verification")
                    await asyncio.sleep(0.1)
                else:
                    # Allow auto-role to see verification channel
                    await channel.set_permissions(auto_role, read_messages=True, send_messages=True, reason="Verification setup - allow verification channel")
                    
            for channel in guild.voice_channels:
                await channel.set_permissions(auto_role, view_channel=False, reason="Verification setup - unverified users no voice access")
                await asyncio.sleep(0.1)

        except Exception as e:
            errors.append(f"Auto-role permissions: {str(e)[:100]}")

        # Step 3: Set verified role to see all channels
        try:
            for channel in guild.text_channels:
                # Allow verified role to see all channels
                await channel.set_permissions(verified_role, read_messages=True, reason="Verification setup - verified users see all")
                await asyncio.sleep(0.1)
                    
            for channel in guild.voice_channels:
                await channel.set_permissions(verified_role, view_channel=True, reason="Verification setup - verified users voice access")
                await asyncio.sleep(0.1)

        except Exception as e:
            errors.append(f"Verified role permissions: {str(e)[:100]}")

        # Step 4: Set category permissions if they exist
        try:
            for category in guild.categories:
                # Deny @everyone from seeing categories
                await category.set_permissions(guild.default_role, read_messages=False, reason="Verification setup - hide categories")
                # Deny auto-role (unverified) from seeing categories except verification
                await category.set_permissions(auto_role, read_messages=False, reason="Verification setup - unverified users restricted")
                # Allow verified role to see categories
                await category.set_permissions(verified_role, read_messages=True, reason="Verification setup - verified users see categories")
                changes_made += 1
                await asyncio.sleep(0.1)
        except Exception as e:
            errors.append(f"Category permissions: {str(e)[:100]}")

        # Create result embed
        embed = discord.Embed(
            title="✅ VERIFICATION SETUP COMPLETE" if not errors else "⚠️ VERIFICATION SETUP PARTIAL",
            description=f"**{changes_made} permission changes made**",
            color=0x00FF00 if not errors else 0xFFFF00
        )

        embed.add_field(
            name="🔧 Actions Taken",
            value=f"• Set @everyone to ONLY see verification channel\n• Set {auto_role.name} (unverified) to ONLY see verification channel\n• Set {verified_role.name} to see all channels\n• Applied to {len(guild.text_channels)} text channels\n• Applied to {len(guild.voice_channels)} voice channels\n• Applied to {len(guild.categories)} categories",
            inline=False
        )

        embed.add_field(
            name="✅ Result",
            value=f"**Unverified users:** Only see <#{VERIFICATION_CHANNEL_ID}>\n**Verified users:** See all channels\n**Unverified Role:** {auto_role.name}\n**Verified Role:** {verified_role.name}",
            inline=False
        )

        if errors:
            embed.add_field(
                name="⚠️ Some Errors",
                value="\n".join([f"• {error}" for error in errors[:3]]),
                inline=False
            )

        embed.add_field(
            name="🎯 Next Steps",
            value="1. Use `/setup_verification_system` to add the verify button\n2. Test with an alt account (gets auto-role)\n3. Verify they only see verification channel\n4. Click verify button to test full access",
            inline=False
        )

        await interaction.edit_original_response(content="", embed=embed)
        logger.info(f"Verification setup completed by {interaction.user.id} - {changes_made} changes made")

    except Exception as e:
        logger.error(f"Error in setup_verification command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)
        else:
            await interaction.edit_original_response(content="❌ Some shit went wrong.")

@bot.tree.command(name="bio", description="Learn about STK Supply Bot")
async def bot_bio(interaction: discord.Interaction):
    """Display STK Supply Bot bio and information"""
    try:
        embed = discord.Embed(
            title="💀 STK SUPPLY BOT 💀",
            description="**The Block's Most Advanced Digital Connect**",
            color=0x39FF14,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="🤖 About Me",
            value="I'm the official STK Supply automation system - built to handle business 24/7. No human needed, just pure digital efficiency.",
            inline=False
        )

        embed.add_field(
            name="🏆 My Capabilities",
            value="• **Instant Order Processing** - Cart to delivery in minutes\n• **Smart User Management** - Auto-profiles & achievements\n• **Secure Ticket System** - Private order channels\n• **Multi-Shop Support** - Expanding to new territories",
            inline=False
        )

        embed.add_field(
            name="💻 Tech Stack",
            value="**Language:** Python 3.11+\n**Framework:** Discord.py\n**Database:** SQLite\n**Hosting:** Replit Cloud\n**Uptime:** 99.9% guaranteed",
            inline=True
        )

        embed.add_field(
            name="🔥 Street Stats",
            value="**Orders Processed:** 50+\n**Response Time:** <2 seconds\n**Customer Satisfaction:** 99.9%\n**Downtime:** Basically none",
            inline=True
        )

        embed.add_field(
            name="⚡ Developer Credits",
            value="**Lead Dev:** Zpofe\n**Systems:** Custom STK architecture\n**Purpose:** Revolutionizing digital street commerce",
            inline=False
        )

        embed.add_field(
            name="🎯 Mission Statement",
            value="*\"Bringing the streets into the digital age - one order at a time. No human errors, no delays, just pure automated excellence.\"*",
            inline=False
        )

        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif")
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
        embed.set_footer(text="STK Supply • Advanced AI Commerce System • Built Different", icon_url=interaction.guild.me.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error in bot_bio command: {e}")
        await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error(f"Command error: {error}")

    # Handle specific Discord errors that shouldn't trigger responses
    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        logger.error(f"Command {interaction.command.name if interaction.command else 'unknown'} failed: {original_error}")

        # Skip responding for these specific errors - these are normal and expected
        if any(phrase in str(original_error).lower() for phrase in [
            "already been acknowledged",
            "interaction has already been acknowledged",
            "unknown interaction",
            "interaction expired",
            "interaction not found"
        ]):
            return  # Don't log as error, this is normal

        if isinstance(original_error, discord.NotFound):
            return  # Don't log as error, this is normal

        if isinstance(original_error, discord.HTTPException) and original_error.status in [404, 40060]:
            return  # Don't log as error, this is normal

    # Only attempt to respond if we can safely do so
    try:
        if hasattr(interaction, 'response') and not interaction.response.is_done():
            await interaction.response.send_message("❌ Command failed. Please try again.", ephemeral=True)
    except (discord.NotFound, discord.HTTPException):
        # These errors are expected when interactions expire - don't log them
        pass
    except Exception as e:
        logger.error(f"Unexpected error in error handler: {e}")

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