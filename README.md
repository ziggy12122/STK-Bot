
# Discord Shop Bot

A comprehensive Discord bot for managing an online shop with product management, shopping cart functionality, order processing, and admin controls.

## Features

### 🛍️ Product Management
- Interactive product browser with embeds and navigation buttons
- Product images, descriptions, and pricing
- Real-time stock level tracking
- Dynamic "Add to Cart" functionality

### 🛒 Shopping System
- Persistent user carts that save between sessions
- Cart review with total calculation
- Secure checkout process with confirmation

### 📋 Order Processing
- Automatic order creation and tracking
- Support ticket generation in designated channel
- Customer role assignment upon purchase
- Order history and fulfillment tracking

### ⚙️ Admin Controls
- Add, update, and manage products
- Stock level management
- Product listing and administration
- Role-based permission system

## Setup Instructions

### Step 1: Fork and Set Up the Repl

1. Create a new Python Repl on Replit
2. Copy all the provided files into your Repl
3. Install dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token and save it securely
5. Enable the following bot permissions:
   - Send Messages
   - Use Slash Commands
   - Manage Roles
   - Embed Links
   - Attach Files
   - Read Message History

### Step 3: Configure Environment Variables

Set up these environment variables in your Replit Secrets:

**Required:**
- `DISCORD_BOT_TOKEN`: Your Discord bot token

**Optional (but recommended):**
- `ADMIN_ROLE_ID`: Role ID that can manage products
- `SHOP_CHANNEL_ID`: Channel where shop commands work
- `TICKET_CHANNEL_ID`: Channel for order notifications
- `CUSTOMER_ROLE_ID`: Role given to customers after purchase

To find role/channel IDs:
1. Enable Developer Mode in Discord Settings > Advanced
2. Right-click on roles/channels and select "Copy ID"

### Step 4: Invite Bot to Server

1. In Discord Developer Portal, go to OAuth2 > URL Generator
2. Select scopes: `bot` and `applications.commands`
3. Select permissions: `Manage Roles`, `Send Messages`, `Use Slash Commands`, `Embed Links`
4. Use the generated URL to invite the bot to your server

### Step 5: Set Up Channels and Roles

1. Create these channels (optional but recommended):
   - `#shop` - For product browsing
   - `#orders` - For order notifications/tickets

2. Create these roles:
   - `Shop Admin` - For product management
   - `Customer` - Given after first purchase

### Step 6: Run the Bot

1. Click the "Run" button in your Repl
2. The bot should come online and be ready to use

## Commands

### User Commands

- `!shop` - Browse all available products
- `!cart` - View your shopping cart
- `!checkout` - Purchase items in your cart

### Admin Commands (requires admin role)

- `!addproduct <name> <price> <stock> [description]` - Add a new product
- `!updatestock <product_id> <new_stock>` - Update product stock
- `!products` - List all products with IDs

## Usage Examples

### Adding a Product
```
!addproduct "Gaming Mouse" 49.99 10 Premium gaming mouse with RGB lighting
```
*Attach an image to include a product photo*

### Managing Stock
```
!updatestock 1 25
```
*Updates product ID 1 to have 25 units in stock*

### Customer Shopping Flow
1. User runs `!shop` to browse products
2. User clicks "Add to Cart" on desired items
3. User runs `!cart` to review their selections
4. User runs `!checkout` to purchase
5. Bot creates order ticket and assigns customer role

## Database Schema

The bot uses SQLite with these tables:

- **products**: Product information and stock levels
- **carts**: User shopping carts (persistent between sessions)
- **orders**: Completed orders with status tracking
- **order_items**: Individual items within each order

## Customization

### Changing Colors
Edit the color values in embeds (hex codes like `0x3498db`)

### Modifying Embeds
Update embed titles, descriptions, and fields in the respective functions

### Adding Features
The modular design makes it easy to add:
- Product categories
- Discount codes
- Payment integration
- Purchase history
- Inventory alerts

### Custom Buttons
Modify the `ProductView` and `CheckoutView` classes to add new buttons or functionality

## Troubleshooting

### Bot Not Responding
- Check if bot token is correct in Secrets
- Verify bot has necessary permissions
- Check console for error messages

### Commands Not Working
- Ensure bot has "Send Messages" permission
- Check if user has required role for admin commands
- Verify channel permissions

### Database Issues
- Bot automatically creates SQLite database
- Database file: `shop.db` (created automatically)
- Check file permissions if issues persist

### Role/Channel Issues
- Verify role/channel IDs are correct numbers
- Ensure bot has permission to assign roles
- Check if channels exist and bot can access them

## Security Notes

- Keep your bot token secure and never share it
- Use role-based permissions for admin commands
- Regularly backup your database file
- Monitor order processing for any issues

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify all configuration settings
3. Test commands in a development server first
4. Review Discord API documentation for advanced features

## License

This bot is provided as-is for educational and commercial use. Feel free to modify and distribute according to your needs.
