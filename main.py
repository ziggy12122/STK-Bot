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

        # Send STK Board message to specified channel
        await self.send_stk_board_message()

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
        """Handle new member join"""
        try:
            # Assign role to new member
            role_id = 1406402417863430204
            try:
                role = member.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    logger.info(f"Assigned role {role.name} to {member.display_name}")
                else:
                    logger.error(f"Role with ID {role_id} not found in guild {member.guild.name}")
            except Exception as e:
                logger.error(f"Failed to assign role to {member.display_name}: {e}")

            # Send welcome message
            await self.send_welcome_to_member(member)

            logger.info(f"New member joined: {member.display_name} ({member.id})")

        except Exception as e:
            logger.error(f"Error in member join event: {e}")

    async def on_member_ban(self, guild, user):
        """Handle member ban with STK-style message"""
        try:
            ban_messages = [
                f"⚔️ **{user.display_name}** GOT THE FUCKING HAMMER! ⚔️",
                f"🔨 **{user.display_name}** BANNED FOR BEING A FUCKING LOSER! 🔨",
                f"💀 **{user.display_name}** VIOLATED THE CODE AND GOT MURKED! 💀",
                f"🗑️ **{user.display_name}** TOOK OUT THE FUCKING TRASH! 🗑️",
                f"⚖️ **{user.display_name}** FACED STK JUSTICE AND LOST! ⚖️"
            ]

            import random
            selected_message = random.choice(ban_messages)

            embed = discord.Embed(
                title="🔨 STK JUSTICE SERVED 🔨",
                description=selected_message,
                color=0x000000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            embed.add_field(
                name="⚖️ COURT IS IN SESSION",
                value="**VERDICT: GUILTY AS FUCK**\n**SENTENCE: BANNED FOR LIFE**\n\nDon't fuck with STK! 💀",
                inline=False
            )

            embed.add_field(
                name="🚨 WARNING TO OTHERS",
                value="**THIS IS WHAT HAPPENS WHEN YOU DISRESPECT STK**\n\nStay in line or get the same treatment! 🔥",
                inline=False
            )

            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="STK (Shoot to Kill) • Justice System • Don't Test Us", icon_url=guild.me.display_avatar.url)

            # Send to general channel
            log_channel = None
            for channel in guild.text_channels:
                if channel.name.lower() in ['general', 'logs', 'chat', 'welcome']:
                    log_channel = channel
                    break

            if log_channel:
                await log_channel.send("🚨 **STK JUSTICE ALERT** 🚨", embed=embed)

            logger.info(f"Member banned: {user.display_name} ({user.id})")

        except Exception as e:
            logger.error(f"Error in member ban event: {e}")

    async def on_member_remove(self, member):
        """Aggressive member leave message - STK style"""
        try:
            # Random aggressive messages for different scenarios
            leave_messages = [
                f"💀 **{member.display_name}** COULDN'T HANDLE THE HEAT AND DIPPED! 💀",
                f"🗑️ **{member.display_name}** TOOK THE TRASH OUT THEMSELVES! 🗑️",
                f"🤡 **{member.display_name}** WAS TOO SOFT FOR STK! 🤡",
                f"👋 **{member.display_name}** LEFT CRYING! BYE BYE! 👋",
                f"💸 **{member.display_name}** COULDN'T AFFORD THE LIFESTYLE! 💸",
                f"😂 **{member.display_name}** RAN AWAY LIKE A LITTLE BITCH! 😂"
            ]

            import random
            selected_message = random.choice(leave_messages)

            embed = discord.Embed(
                title="🚮 ANOTHER ONE BITES THE DUST 🚮",
                description=selected_message,
                color=0x8B0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            embed.add_field(
                name="💀 STK DON'T NEED WEAK LINKS",
                value="**ONLY THE STRONGEST SURVIVE IN OUR GANG**\n\nThey probably went crying to their mommy! 😭",
                inline=False
            )

            embed.add_field(
                name="📊 Gang Stats",
                value=f"**Real Members Left:** {len(member.guild.members)}\n**They Joined:** Recently\n**Lasted:** Not long enough! 💀",
                inline=True
            )

            embed.add_field(
                name="🔥 Message to Leavers",
                value="**DON'T COME BACK UNLESS YOU CAN HANDLE THE STREETS!**\n\nSTK is for REAL ONES ONLY! 💯",
                inline=False
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url="https://media.tenor.com/images/trash-can.gif")
            embed.set_footer(text="STK (Shoot to Kill) • We Don't Miss The Weak", icon_url=member.guild.me.display_avatar.url)

            # Send to general channel
            log_channel = None
            for channel in member.guild.text_channels:
                if channel.name.lower() in ['general', 'logs', 'chat', 'welcome']:
                    log_channel = channel
                    break

            if log_channel:
                await log_channel.send("**BREAKING NEWS:** 🗞️", embed=embed)

            logger.info(f"Member left: {member.display_name} ({member.id})")

        except Exception as e:
            logger.error(f"Error in member remove event: {e}")

    async def send_welcome_to_member(self, member):
        """Send welcome message when a member joins"""
        try:
            embed = discord.Embed(
                title="💀 STK (SHOOT TO KILL) 💀",
                description="**THE MOST FEARED GANG IN THE STREETS**",
                color=0xFF0000,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

            embed.add_field(
                name="🏙️ WHO WE ARE",
                value="STK (Shoot to Kill) is the most elite and respected gang operating in Tha Bronx 3. We provide premium undetected services, fast dupes, and maintain our reputation through elite operations and unmatched street credibility.",
                inline=False
            )

            embed.add_field(
                name="👑 OUR LEADERSHIP",
                value="💎 **ZPOFE** - Chief Architect & Elite Developer\n⚡ **ASAI** - Operations General\n🔥 **DROW** - Multi-Role Elite\n\n🪖 Professional hierarchy with proven results",
                inline=True
            )

            embed.add_field(
                name="🎯 WHAT WE PROVIDE",
                value="• Elite quality undetected services\n• Fast dupes with infinite money supply\n• Premium weapons & luxury items\n• 24/7 business operations\n• Most trusted connects in the game\n• Response time: 2-5 minutes\n• 99.9% success rate",
                inline=True
            )

            embed.add_field(
                name="📍 OUR TERRITORY",
                value="🏙️ **Primary Base:** Tha Bronx 3\n🌍 **Expanding:** New territories coming soon\n💯 **Reputation:** 50+ satisfied customers\n⚡ **Business Hours:** 24/7 grinding",
                inline=False
            )

            embed.add_field(
                name="💀 THE STK CODE",
                value="• Respect the gang hierarchy\n• Elite members only - no weak links\n• Business first, always professional\n• Undetected services guaranteed\n• Fast delivery, no delays",
                inline=True
            )

            embed.add_field(
                name="🔥 JOIN THE ELITE",
                value="We don't just run the streets, we own them. Welcome to STK territory - where elite quality meets undetected services and infinite supply.",
                inline=True
            )

            embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
            embed.set_footer(text="STK Supply • Elite Quality • Undetected Services • Fast Dupes • Infinite Money Supply", icon_url=member.guild.me.display_avatar.url)

            # Find appropriate channel
            welcome_channel = None
            for channel in member.guild.text_channels:
                if channel.name.lower() in ['general', 'welcome', 'chat']:
                    welcome_channel = channel
                    break

            if not welcome_channel:
                welcome_channel = member.guild.text_channels[0] if member.guild.text_channels else None

            if welcome_channel:
                await welcome_channel.send(f"🚨 **STK TERRITORY** 🚨\n\n{member.mention} **WELCOME TO THE GANG!** 💀🔥", embed=embed)
                logger.info(f"Sent welcome message for {member.display_name}")

        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def send_stk_board_message(self):
        """Send STK Board message to specified channel on startup"""
        try:
            target_channel_id = 1398741781331447890
            channel = self.get_channel(target_channel_id)

            if not channel:
                logger.error(f"Could not find channel with ID {target_channel_id}")
                return

            view = STKBoardView()
            embed = view.create_board_embed()

            await channel.send(embed=embed, view=view)
            logger.info(f"Sent STK Board message to channel {channel.name}")

        except Exception as e:
            logger.error(f"Error sending STK Board message: {e}")

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
            value="💀 **ZPOFE** • Main connect • 3+ years • Lightning delivery\n⚡ **DROW** • Specialist • Premium connections • Trusted",
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
            title="💀 STK (SHOOT TO KILL) 💀",
            description="**THE MOST FEARED GANG IN THE STREETS**",
            color=0xFF0000
        )

        # Add images
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif?ex=68a1c8a6&is=68a07726&hm=1a990b57e6e70e8c31978e9d90aba07b1607e688f610331dddd8b42d4ccb88dd&")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif?ex=68a1c8a6&is=68a07726&hm=a73756ad78ccbf90f487df0045bc1ce19d558842ea8527d1444691fd4a29dc74&")

        embed.add_field(
            name="🚨 SHOP NO LONGER AVAILABLE HERE 🚨",
            value="**STK has moved to a new location!**\n\n🔗 **NEW DISCORD:** https://discord.gg/89j5c2SEK3\n\n⚡ **Join our new server for all STK services!**",
            inline=False
        )

        embed.add_field(
            name="👑 OUR LEADERSHIP",
            value="💎 **ZPOFE** - Chief Architect & Elite Developer\n⚡ **ASAI** - Operations General\n🔥 **DROW** - Multi-Role Elite\n🏛️ **AVERY** - STK Founder\n\n🪖 Professional hierarchy with proven results",
            inline=True
        )

        embed.add_field(
            name="🎯 WHAT WE PROVIDE",
            value="• Elite quality undetected services\n• Fast dupes with infinite money supply\n• Premium weapons & luxury items\n• 24/7 business operations\n• Most trusted connects in the game\n• Response time: 2-5 minutes\n• 99.9% success rate",
            inline=True
        )

        embed.add_field(
            name="📍 OUR TERRITORY",
            value="🏙️ **Primary Base:** Tha Bronx 3\n🌍 **Expanding:** New territories coming soon\n💯 **Reputation:** 50+ satisfied customers\n⚡ **Business Hours:** 24/7 grinding",
            inline=False
        )

        embed.add_field(
            name="💰 WHERE TO BUY",
            value="🛒 **JOIN OUR NEW DISCORD:** https://discord.gg/89j5c2SEK3\n\n🔥 **All premium services available**\n💎 **Elite quality guaranteed**\n⚡ **Fast delivery & professional service**",
            inline=True
        )

        embed.add_field(
            name="💀 THE STK CODE",
            value="• Respect the gang hierarchy\n• Elite members only - no weak links\n• Business first, always professional\n• Undetected services guaranteed\n• Fast delivery, no delays",
            inline=True
        )

        embed.set_footer(text="STK Supply • Elite Quality • Undetected Services • Fast Dupes • Infinite Money Supply")
        return embed

    @discord.ui.button(label='📞 CONTACT', style=discord.ButtonStyle.secondary, emoji='📱', row=1)
    async def contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📞 **CONTACT STK**\n\nDM **Zpofe** or **Drow** for business inquiries.\n\n⚡ **Response time:** Usually within a few hours\n💀 **We're always grinding!**", ephemeral=True)

    @discord.ui.button(label='👥 MEET THE TEAM', style=discord.ButtonStyle.primary, emoji='👑', row=1)
    async def meet_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = STKBoardView()
        embed = view.create_board_embed()
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
            # Set proper permissions for category - default deny all
            category_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }

            # Add staff role permissions
            staff_roles = ['staff', 'mod', 'admin', 'owner', 'stk', 'management', 'manager']
            for role in guild.roles:
                if any(keyword in role.name.lower() for keyword in staff_roles):
                    category_overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

            # Add admin role permissions if configured
            if BotConfig.ADMIN_ROLE_ID:
                admin_role = guild.get_role(BotConfig.ADMIN_ROLE_ID)
                if admin_role:
                    category_overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

            category = await guild.create_category("🥊・STK TRYOUTS", overwrites=category_overwrites)
        except discord.Forbidden:
            logger.error("No permission to create category")
            return None

    # Create ticket channel
    ticket_name = f"stk-tryout-{interaction.user.name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"

    # Set strict permissions - deny everyone by default, then allow specific users/roles
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
    }

    # Add staff role permissions - only specific staff roles can see tryouts
    staff_roles = ['staff', 'mod', 'admin', 'owner', 'stk', 'management', 'manager', 'support']
    for role in guild.roles:
        if any(keyword in role.name.lower() for keyword in staff_roles):
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

    # Add admin role permissions if configured
    if BotConfig.ADMIN_ROLE_ID:
        admin_role = guild.get_role(BotConfig.ADMIN_ROLE_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

    # Add specific permissions for STK members
    stk_member_ids = [1385239185006268457, 954818761729376357, 1394285950464426066]  # Zpofe, Asai, Drow
    for member_id in stk_member_ids:
        member = guild.get_member(member_id)
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

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
        color=0xFF0000
    )

    embed.add_field(
        name="👤 Applicant",
        value=f"{user.mention}\n`{user.id}`",
        inline=True
    )

    embed.add_field(
        name="⏰ Tryout Created",
        value="Just now",
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
            # Set proper permissions for category - default deny all
            category_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }

            # Add staff role permissions
            staff_roles = ['staff', 'mod', 'admin', 'owner', 'stk', 'management', 'manager']
            for role in guild.roles:
                if any(keyword in role.name.lower() for keyword in staff_roles):
                    category_overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

            # Add admin role permissions if configured
            if BotConfig.ADMIN_ROLE_ID:
                admin_role = guild.get_role(BotConfig.ADMIN_ROLE_ID)
                if admin_role:
                    category_overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

            category = await guild.create_category("🎫・TICKETS", overwrites=category_overwrites)
        except discord.Forbidden:
            logger.error("No permission to create category")
            return None

    # Create ticket channel
    ticket_name = f"ticket-{interaction.user.name}-{datetime.datetime.now().strftime('%m%d-%H%M')}"

    # Set strict permissions - deny everyone by default, then allow specific users/roles
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, embed_links=True, attach_files=True)
    }

    # Add staff role permissions - only specific staff roles can see tickets
    staff_roles = ['staff', 'mod', 'admin', 'owner', 'stk', 'management', 'manager', 'support']
    for role in guild.roles:
        if any(keyword in role.name.lower() for keyword in staff_roles):
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

    # Add specific STK members permissions
    stk_member_ids = [1385239185006268457, 954818761729376357, 1394285950464426066]  # Zpofe, Asai, Drow
    for member_id in stk_member_ids:
        member = guild.get_member(member_id)
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

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
        description=f"**Customer:** {user.mention} (`{user.id}`)\n**Order Time:** Just now",
        color=0x00ff00
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

# STK Tryout Management View
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
            title="❌ STK TRYOUT REJECTED",
            description="**Better luck next time.**\n\nYou didn't meet our standards.",
            color=0xff0000,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label='🔒 CLOSE', style=discord.ButtonStyle.secondary, custom_id='close_tryout')
    async def close_tryout(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK members can do this.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 **Closing tryout channel in 5 seconds...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# Ticket Management View
class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ COMPLETE', style=discord.ButtonStyle.success, custom_id='complete_order')
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK staff can do this.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ ORDER COMPLETED",
            description="**Thank you for your business!**\n\nOrder has been marked as completed.",
            color=0x00ff00,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label='🔒 CLOSE', style=discord.ButtonStyle.secondary, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        has_permission = False
        if BotConfig.ADMIN_ROLE_ID and any(role.id == BotConfig.ADMIN_ROLE_ID for role in interaction.user.roles):
            has_permission = True
        elif interaction.user.guild_permissions.manage_channels:
            has_permission = True

        if not has_permission:
            await interaction.response.send_message("❌ Only STK staff can do this.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 **Closing ticket in 5 seconds...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# Shop Entry View - For setup command
class ShopEntryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🛒 OPEN SHOP', style=discord.ButtonStyle.success, emoji='🔥', row=1)
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create a personal shop for the user
        view = PersonalSTKShopView(interaction.user.id)
        embed = view.create_personal_shop_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label='🏪 VIEW ALL SHOPS', style=discord.ButtonStyle.primary, emoji='🌍', row=1)
    async def view_all_shops(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ShopSelectorView()
        embed = view.create_selector_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label='ℹ️ ABOUT STK', style=discord.ButtonStyle.secondary, emoji='💀', row=1)
    async def about_stk(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = STKBoardView()
        embed = view.create_board_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

        # Create the shop moved embed
        embed = discord.Embed(
            title="💀 STK (SHOOT TO KILL) 💀",
            description="**THE MOST FEARED GANG IN THE STREETS**",
            color=0xFF0000
        )

        # Add the gif images
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif")

        embed.add_field(
            name="🚨 SHOP NO LONGER AVAILABLE HERE 🚨",
            value="**STK has moved to a new location!**\n\n🔗 **NEW DISCORD:** https://discord.gg/89j5c2SEK3\n\n⚡ **Join our new server for all STK services!**",
            inline=False
        )

        embed.add_field(
            name="👑 OUR LEADERSHIP",
            value="💎 **ZPOFE** - Chief Architect & Elite Developer\n⚡ **ASAI** - Operations General\n🔥 **DROW** - Multi-Role Elite\n🏛️ **AVERY** - STK Founder\n\n🪖 Professional hierarchy with proven results",
            inline=True
        )

        embed.add_field(
            name="🎯 WHAT WE PROVIDE",
            value="• Elite quality undetected services\n• Fast dupes with infinite money supply\n• Premium weapons & luxury items\n• 24/7 business operations\n• Most trusted connects in the game\n• Response time: 2-5 minutes\n• 99.9% success rate",
            inline=True
        )

        embed.add_field(
            name="💰 WHERE TO BUY - NEW DISCORD SERVER",
            value="🔗 **https://discord.gg/89j5c2SEK3**\n\n🔥 **All premium services available**\n💎 **Elite quality guaranteed**\n⚡ **Fast delivery & professional service**\n\n**🛒 ALL PURCHASES MUST BE MADE IN THE NEW DISCORD SERVER**",
            inline=False
        )

        embed.add_field(
            name="💀 THE STK CODE",
            value="• Respect the gang hierarchy\n• Elite members only - no weak links\n• Business first, always professional\n• Undetected services guaranteed\n• Fast delivery, no delays",
            inline=True
        )

        embed.add_field(
            name="🔥 JOIN THE ELITE",
            value="We don't just run the streets, we own them. Join our new Discord server - where elite quality meets undetected services and infinite supply.",
            inline=True
        )

        embed.set_footer(text="STK Supply • Elite Quality • Undetected Services • Fast Dupes • Infinite Money Supply")

        # Create button to redirect to new Discord
        view = discord.ui.View(timeout=None)
        discord_button = discord.ui.Button(
            label='🔗 JOIN NEW DISCORD',
            style=discord.ButtonStyle.link,
            url='https://discord.gg/89j5c2SEK3',
            emoji='💀'
        )
        view.add_item(discord_button)

        # Send the shop interface with redirect button
        await interaction.channel.send(embed=embed, view=view)

        # Respond to the interaction
        await interaction.response.send_message("✅ **STK Shop setup complete!**", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in setup_shop command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)



# Auto-send STK info message (prevent duplicates)
sent_messages = set()

async def send_stk_info_if_needed(channel):
    """Send STK info message if not already sent in this channel"""
    if channel.id in sent_messages:
        return

    try:
        embed = discord.Embed(
            title="💀 STK (SHOOT TO KILL) 💀",
            description="**THE MOST FEARED GANG IN THE STREETS**",
            color=0xFF0000,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="🏙️ WHO WE ARE",
            value="STK (Shoot to Kill) is the most elite and respected gang operating in Tha Bronx 3. We provide premium undetected services, fast dupes, and maintain our reputation through elite operations and unmatched street credibility.",
            inline=False
        )

        embed.add_field(
            name="👑 OUR LEADERSHIP",
            value="💎 **ZPOFE** - Chief Architect & Elite Developer\n⚡ **ASAI** - Operations General\n🔥 **DROW** - Multi-Role Elite\n\n🪖 Professional hierarchy with proven results",
            inline=True
        )

        embed.add_field(
            name="🎯 WHAT WE PROVIDE",
            value="• Elite quality undetected services\n• Fast dupes with infinite money supply\n• Premium weapons & luxury items\n• 24/7 business operations\n• Most trusted connects in the game\n• Response time: 2-5 minutes\n• 99.9% success rate",
            inline=True
        )

        embed.add_field(
            name="📍 OUR TERRITORY",
            value="🏙️ **Primary Base:** Tha Bronx 3\n🌍 **Expanding:** New territories coming soon\n💯 **Reputation:** 50+ satisfied customers\n⚡ **Business Hours:** 24/7 grinding",
            inline=False
        )

        embed.add_field(
            name="💀 THE STK CODE",
            value="• Respect the gang hierarchy\n• Elite members only - no weak links\n• Business first, always professional\n• Undetected services guaranteed\n• Fast delivery, no delays",
            inline=True
        )

        embed.add_field(
            name="🔥 JOIN THE ELITE",
            value="We don't just run the streets, we own them. Welcome to STK territory - where elite quality meets undetected services and infinite supply.",
            inline=True
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
        embed.set_footer(text="STK Supply • Elite Quality • Undetected Services • Fast Dupes • Infinite Money Supply", icon_url=channel.guild.me.display_avatar.url)

        await channel.send("🚨 **STK TERRITORY** 🚨", embed=embed)
        sent_messages.add(channel.id)

    except Exception as e:
        logger.error(f"Error sending STK info: {e}")

# STK Board data - Now editable by members
STK_BOARD_MEMBERS = {
    "zpofe": {
        "id": 1385239185006268457,
        "name": "ZPOFE",
        "title": "#1 SELLER",
        "roles": ["#1 Coder", "#1 Seller for Tha Bronx", "#1 Seller for SB", "#1 Seller for Philly"],
        "description": "Chief Architect & Elite Developer",
        "emoji": "💎",
        "custom_fields": {},
        "achievements": ["💎 Elite Coding Skills", "🔥 Multi-Territory Domination", "⚡ 3+ Years Experience", "💯 Unmatched Success Rate"],
        "specialties": ["🏙️ Tha Bronx 3", "🌆 South Bronx (SB)", "🏢 Philadelphia", "🌍 Expanding Worldwide"]
    },
    "asai": {
        "id": 954818761729376357,
        "name": "ASAI",
        "title": "OWNER",
        "roles": ["Operations General", "STK Owner"],
        "description": "STK Operations Leader",
        "emoji": "👑",
        "custom_fields": {},
        "achievements": ["👑 STK Leadership", "⚡ Operations Master", "💼 Business Strategy", "🔥 Gang Coordination"],
        "specialties": ["🎯 Gang Operations", "💰 Business Management", "⚔️ Territory Control", "🛡️ Member Protection"]
    },
    "drow": {
        "id": 1394285950464426066,
        "name": "DROW",
        "title": "THA BRONX 3 SELLER",
        "roles": ["Multi-Role Elite", "Tha Bronx 3 Specialist"],
        "description": "Elite Street Operations",
        "emoji": "⚡",
        "custom_fields": {},
        "achievements": ["⚡ Tha Bronx 3 Expert", "🔫 Street Operations", "💯 Elite Performance", "🎯 Multi-Role Master"],
        "specialties": ["🏙️ Tha Bronx 3 Operations", "💀 Premium Connections", "⚡ Fast Delivery", "🔥 Street Knowledge"]
    },
    "avery": {
        "id": 666394721039417346,
        "name": "AVERY",
        "title": "STK FOUNDER",
        "roles": ["Founder", "Original Gang Leader"],
        "description": "The one who started it all",
        "emoji": "🏛️",
        "custom_fields": {},
        "achievements": ["🏛️ Founded STK Gang", "👑 Original Leader", "💀 Street Legend", "🔥 Gang Pioneer"],
        "specialties": ["💯 Created the Empire", "🌟 Established the Code", "⚔️ Built the Reputation", "🏆 STK Foundation"]
    }
}

# STK Board member IDs for permission checking
STK_BOARD_IDS = [1385239185006268457, 1394285950464426066, 666394721039417346, 954818761729376357]

# STK Board View
class STKBoardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def create_board_embed(self):
        embed = discord.Embed(
            title="💀 STK (SHOOT TO KILL) 💀",
            description="**THE MOST FEARED GANG IN THE STREETS**\n\n🔥 **WELCOME TO STK TERRITORY** 🔥",
            color=0xFF0000,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(
            name="🏙️ WHO WE ARE",
            value="STK (Shoot to Kill) is the most elite and respected gang operating in Tha Bronx 3. We provide premium undetected services, fast dupes, and maintain our reputation through elite operations and unmatched street credibility.",
            inline=False
        )

        embed.add_field(
            name="👑 OUR LEADERSHIP",
            value="💎 **ZPOFE** - Chief Architect & Elite Developer\n⚡ **ASAI** - Operations General\n🔥 **DROW** - Multi-Role Elite\n🏛️ **AVERY** - STK Founder\n\n🪖 Professional hierarchy with proven results",
            inline=True
        )

        embed.add_field(
            name="🎯 WHAT WE PROVIDE",
            value="• Elite quality undetected services\n• Fast dupes with infinite money supply\n• Premium weapons & luxury items\n• 24/7 business operations\n• Most trusted connects in the game\n• Response time: 2-5 minutes\n• 99.9% success rate",
            inline=True
        )

        embed.add_field(
            name="📍 OUR TERRITORY",
            value="🏙️ **Primary Base:** Tha Bronx 3\n🌍 **Expanding:** New territories coming soon\n💯 **Reputation:** 50+ satisfied customers\n⚡ **Business Hours:** 24/7 grinding",
            inline=False
        )

        embed.add_field(
            name="💰 WHERE TO BUY",
            value=f"🛒 **SHOP NOW:** <#{1398576146441965629}>\n\n🔥 **All premium services available**\n💎 **Elite quality guaranteed**\n⚡ **Fast delivery & professional service**",
            inline=True
        )

        embed.add_field(
            name="💀 THE STK CODE",
            value="• Respect the gang hierarchy\n• Elite members only - no weak links\n• Business first, always professional\n• Undetected services guaranteed\n• Fast delivery, no delays",
            inline=True
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069644812357753/standard.gif")
        embed.set_footer(text="STK Supply • Elite Quality • Undetected Services • Fast Dupes • Infinite Money Supply", icon_url="https://cdn.discordapp.com/attachments/1398907047734673500/1406069645164937368/standard_2.gif")
        return embed

    @discord.ui.button(label='◀️ BACK TO MAIN', style=discord.ButtonStyle.secondary, emoji='🏠', row=1)
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PersistentSTKShopView()
        embed = view.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💎 MEET ZPOFE', style=discord.ButtonStyle.primary, emoji='💎', row=1)
    async def zpofe_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_member_profile(interaction, "zpofe")

    @discord.ui.button(label='👑 MEET ASAI', style=discord.ButtonStyle.success, emoji='👑', row=1)
    async def asai_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_member_profile(interaction, "asai")

    @discord.ui.button(label='⚡ MEET DROW', style=discord.ButtonStyle.danger, emoji='⚡', row=2)
    async def drow_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_member_profile(interaction, "drow")

    @discord.ui.button(label='🏛️ MEET AVERY', style=discord.ButtonStyle.secondary, emoji='🏛️', row=2)
    async def avery_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_member_profile(interaction, "avery")

    @discord.ui.button(label='📞 CONTACT TEAM', style=discord.ButtonStyle.primary, emoji='📱', row=3)
    async def contact_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📞 CONTACT STK TEAM",
            description="**Get in touch with our elite team**",
            color=0x00FF00
        )

        embed.add_field(
            name="💀 ZPOFE",
            value="**Main Connect & Developer**\nDM for business inquiries\nResponse: Usually within hours",
            inline=True
        )

        embed.add_field(
            name="⚡ DROW",
            value="**Premium Specialist**\nDM for premium services\nResponse: Fast turnaround",
            inline=True
        )

        embed.add_field(
            name="👑 ASAI",
            value="**Operations Leader**\nDM for gang business\nResponse: Leadership matters",
            inline=True
        )

        embed.add_field(
            name="📋 General Guidelines",
            value="• Business inquiries welcome\n• Be respectful and professional\n• Response time: 2-24 hours\n• We're always grinding!",
            inline=False
        )

        embed.set_footer(text="STK Supply • Always ready for business")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def show_member_profile(self, interaction: discord.Interaction, member_key: str):
        member = STK_BOARD_MEMBERS[member_key]

        embed = discord.Embed(
            title=f"{member['emoji']} {member['name']} {member['emoji']}",
            description=f"**{member['title']}**\n\n{member['description']}",
            color=0xFF0000 if member_key == "zpofe" else 0x00FF00 if member_key == "asai" else 0xFFFF00 if member_key == "drow" else 0x800080,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Add roles field
        roles_text = "\n".join([f"• {role}" for role in member['roles']])
        embed.add_field(
            name="🎯 ROLES & SPECIALTIES",
            value=roles_text,
            inline=False
        )

        # Add achievements and specialties from editable data
        achievements_text = "\n".join([f"• {achievement}" for achievement in member['achievements']])
        specialties_text = "\n".join([f"• {specialty}" for specialty in member['specialties']])

        embed.add_field(
            name="🏆 ACHIEVEMENTS",
            value=achievements_text,
            inline=True
        )

        embed.add_field(
            name="🎯 SPECIALTIES",
            value=specialties_text,
            inline=True
        )

        # Add custom fields if any
        if member['custom_fields']:
            for field_name, field_value in member['custom_fields'].items():
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )

        # Add contact info if member has Discord ID
        if member['id']:
            discord_member = interaction.guild.get_member(member['id'])
            if discord_member:
                embed.set_thumbnail(url=discord_member.display_avatar.url)
                embed.add_field(
                    name="📞 CONTACT",
                    value=f"💬 **Discord:** {discord_member.mention}\n🎯 **Status:** Active\n⚡ **Response:** Fast",
                    inline=False
                )

        embed.set_footer(text=f"STK Supply • {member['title']} • Elite Member", icon_url=interaction.guild.me.display_avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)

# Card Editor Modal
class CardEditorModal(discord.ui.Modal):
    def __init__(self, member_key: str):
        self.member_key = member_key
        member = STK_BOARD_MEMBERS[member_key]

        super().__init__(title=f"Edit {member['name']}'s Card", timeout=300)

        # Title field
        self.title_field = discord.ui.TextInput(
            label="Title",
            placeholder="Your title (e.g., #1 SELLER, OWNER, etc.)",
            default=member.get('title', ''),
            max_length=50,
            required=False
        )
        self.add_item(self.title_field)

        # Description field
        self.description_field = discord.ui.TextInput(
            label="Description",
            placeholder="Brief description of your role",
            default=member.get('description', ''),
            max_length=100,
            required=False
        )
        self.add_item(self.description_field)

        # Achievements field (multiline)
        achievements_text = "\n".join(member.get('achievements', []))
        self.achievements_field = discord.ui.TextInput(
            label="Achievements (one per line)",
            placeholder="💎 Elite Skills\n🔥 Multi-Territory Domination",
            default=achievements_text,
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.achievements_field)

        # Specialties field (multiline)
        specialties_text = "\n".join(member.get('specialties', []))
        self.specialties_field = discord.ui.TextInput(
            label="Specialties (one per line)",
            placeholder="🏙️ Tha Bronx 3\n💀 Premium Connections",
            default=specialties_text,
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.specialties_field)

        # Emoji field
        self.emoji_field = discord.ui.TextInput(
            label="Card Emoji",
            placeholder="💎",
            default=member.get('emoji', ''),
            max_length=2,
            required=False
        )
        self.add_item(self.emoji_field)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Update the member data
            member = STK_BOARD_MEMBERS[self.member_key]

            if self.title_field.value.strip():
                member['title'] = self.title_field.value.strip()

            if self.description_field.value.strip():
                member['description'] = self.description_field.value.strip()

            if self.achievements_field.value.strip():
                member['achievements'] = [line.strip() for line in self.achievements_field.value.strip().split('\n') if line.strip()]

            if self.specialties_field.value.strip():
                member['specialties'] = [line.strip() for line in self.specialties_field.value.strip().split('\n') if line.strip()]

            if self.emoji_field.value.strip():
                member['emoji'] = self.emoji_field.value.strip()

            embed = discord.Embed(
                title="✅ CARD UPDATED",
                description=f"**{member['name']}'s card has been updated!**\n\nChanges will appear on the STK Board.",
                color=0x00FF00
            )

            embed.add_field(
                name="Updated Information",
                value=f"**Title:** {member['title']}\n**Description:** {member['description']}\n**Emoji:** {member['emoji']}",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"{interaction.user.display_name} updated {member['name']}'s card")

        except Exception as e:
            logger.error(f"Error updating card: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error updating card.", ephemeral=True)

# Edit card command
@bot.tree.command(name="editcard", description="Edit your STK board card (STK members only)")
async def edit_card(interaction: discord.Interaction):
    """Edit your STK board member card"""
    try:
        # Check if user is STK board member
        if interaction.user.id not in STK_BOARD_IDS:
            await interaction.response.send_message("❌ Only STK board members can edit cards.", ephemeral=True)
            return

        # Find which member this user is
        member_key = None
        for key, member in STK_BOARD_MEMBERS.items():
            if member['id'] == interaction.user.id:
                member_key = key
                break

        if not member_key:
            await interaction.response.send_message("❌ Could not find your card in the system.", ephemeral=True)
            return

        # Show the modal
        modal = CardEditorModal(member_key)
        await interaction.response.send_modal(modal)

    except Exception as e:
        logger.error(f"Error in edit_card command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

# Preview card command
@bot.tree.command(name="previewcard", description="Preview your STK board card (STK members only)")
async def preview_card(interaction: discord.Interaction):
    """Preview your STK board member card"""
    try:
        # Check if user is STK board member
        if interaction.user.id not in STK_BOARD_IDS:
            await interaction.response.send_message("❌ Only STK board members can preview cards.", ephemeral=True)
            return

        # Find which member this user is
        member_key = None
        for key, member in STK_BOARD_MEMBERS.items():
            if member['id'] == interaction.user.id:
                member_key = key
                break

        if not member_key:
            await interaction.response.send_message("❌ Could not find your card in the system.", ephemeral=True)
            return

        member = STK_BOARD_MEMBERS[member_key]

        embed = discord.Embed(
            title=f"{member['emoji']} {member['name']} {member['emoji']}",
            description=f"**{member['title']}**\n\n{member['description']}",
            color=0xFF0000 if member_key == "zpofe" else 0x00FF00 if member_key == "asai" else 0xFFFF00 if member_key == "drow" else 0x800080,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        # Add roles field
        roles_text = "\n".join([f"• {role}" for role in member['roles']])
        embed.add_field(
            name="🎯 ROLES & SPECIALTIES",
            value=roles_text,
            inline=False
        )

        # Add achievements and specialties
        achievements_text = "\n".join([f"• {achievement}" for achievement in member['achievements']])
        specialties_text = "\n".join([f"• {specialty}" for specialty in member['specialties']])

        embed.add_field(
            name="🏆 ACHIEVEMENTS",
            value=achievements_text,
            inline=True
        )

        embed.add_field(
            name="🎯 SPECIALTIES",
            value=specialties_text,
            inline=True
        )

        # Add custom fields if any
        if member['custom_fields']:
            for field_name, field_value in member['custom_fields'].items():
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )

        # Add contact info
        discord_member = interaction.guild.get_member(member['id'])
        if discord_member:
            embed.set_thumbnail(url=discord_member.display_avatar.url)
            embed.add_field(
                name="📞 CONTACT",
                value=f"💬 **Discord:** {discord_member.mention}\n🎯 **Status:** Active\n⚡ **Response:** Fast",
                inline=False
            )

        embed.set_footer(text=f"STK Supply • {member['title']} • Elite Member", icon_url=interaction.guild.me.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in preview_card command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Some shit went wrong.", ephemeral=True)

# Setup STK Join command (Tryout/Joining System)
@bot.tree.command(name="setupjoinstk", description="Setup the STK Join/Tryout system for new members")
async def setup_stk_join(interaction: discord.Interaction):
    """Setup the STK Join interface for tryouts and joining the gang"""
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

        view = STKJoinView()
        embed = view.create_join_embed()

        # Send the join interface
        await interaction.channel.send(embed=embed, view=view)

        # Respond to the interaction
        await interaction.response.send_message("✅ **STK Join/Tryout system live!**", ephemeral=True)

    except Exception as e:
        logger.error(f"Error in setup_stk_join command: {e}")
        if not interaction.response.is_done():
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




