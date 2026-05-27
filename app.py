import os
import io
import textwrap
import asyncio
import threading
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont
import requests
from templates import TEMPLATES, get_all_templates, get_template

# === CONFIGURATION ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 5000))

# === FLASK APP for Render Health Checks ===
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "service": "Meme Bot"}), 200

# === MEME GENERATION FUNCTIONS ===
def download_image(url):
    """Download image from URL"""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content))

def wrap_text(text, font, max_width):
    """Wrap text to fit within max width"""
    lines = []
    words = text.split()
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def draw_text_with_outline(draw, text, position, font, fill='white', outline_color='black', outline_width=2):
    """Draw text with black outline for better visibility"""
    x, y = position
    
    # Draw outline
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill)

def create_meme(template_name, top_text, bottom_text):
    """Create meme image with text"""
    template = get_template(template_name)
    if not template:
        return None
    
    try:
        # Download and prepare image
        img = download_image(template["url"])
        img = img.convert('RGBA')
        
        # Create drawing context
        draw = ImageDraw.Draw(img)
        
        # Load fonts - use default with larger size
        try:
            # Try to use a standard font if available
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            # Fall back to default font
            font = ImageFont.load_default()
        
        img_width = img.width
        
        # Add top text
        if top_text:
            wrapped_top = textwrap.wrap(top_text.upper(), width=20)
            y_offset = template["top_y"]
            
            for line in wrapped_top:
                try:
                    bbox = font.getbbox(line)
                    text_width = bbox[2] - bbox[0]
                except:
                    text_width = len(line) * 15  # Approximate width
                
                x_position = (img_width - text_width) // 2
                draw_text_with_outline(draw, line, (x_position, y_offset), font, 'white')
                y_offset += 65
        
        # Add bottom text
        if bottom_text:
            wrapped_bottom = textwrap.wrap(bottom_text.upper(), width=20)
            y_offset = template["bottom_y"]
            
            for line in wrapped_bottom:
                try:
                    bbox = font.getbbox(line)
                    text_width = bbox[2] - bbox[0]
                except:
                    text_width = len(line) * 15
                
                x_position = (img_width - text_width) // 2
                draw_text_with_outline(draw, line, (x_position, y_offset), font, 'white')
                y_offset += 65
        
        # Convert back to RGB for saving
        img = img.convert('RGB')
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
        
    except Exception as e:
        print(f"Error creating meme: {e}")
        return None

# === TELEGRAM BOT HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_text = (
        "🎭 *Welcome to Meme Generator Bot!*\n\n"
        "I can turn any text into a custom meme.\n\n"
        "*How to use:*\n"
        "1️⃣ Select a meme template using /templates\n"
        "2️⃣ Send text like: `/meme template_name Your top text | Your bottom text`\n\n"
        "*Example:*\n"
        "`/meme drake No thanks | Take my upvote!`\n\n"
        "Available templates:\n"
        "• drake - Drake Hotline Bling\n"
        "• distracted - Distracted Boyfriend\n"
        "• two_buttons - Two Buttons\n"
        "• change_mind - Change My Mind\n"
        "• disaster_girl - Disaster Girl\n\n"
        "Use /templates to see all options with images!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available meme templates with preview buttons"""
    templates_list = "\n".join([f"• `{name}` - {data['name']}" for name, data in TEMPLATES.items()])
    
    message = (
        "*📸 Available Meme Templates:*\n\n"
        f"{templates_list}\n\n"
        "*How to use:*\n"
        "Send: `/meme template_name Top text | Bottom text`\n\n"
        "*Example:*\n"
        "`/meme distracted Me coding | The bug I'm fixing`\n\n"
        "*Tip:* Use the vertical bar `|` to separate top and bottom text!"
    )
    
    # Add preview buttons
    keyboard = []
    for name, data in TEMPLATES.items():
        keyboard.append([InlineKeyboardButton(f"📷 {data['name']}", url=data['url'])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def generate_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate meme from user command"""
    if not context.args:
        await update.message.reply_text(
            "❌ *Usage:* `/meme template_name text`\n"
            "or `/meme template_name Top text | Bottom text`\n\n"
            "Use /templates to see available templates!",
            parse_mode='Markdown'
        )
        return
    
    # Parse command
    args = ' '.join(context.args)
    
    # Check if user specified two texts with pipe
    if '|' in args:
        parts = args.split('|')
        first_part = parts[0].strip()
        words = first_part.split()
        if len(words) == 0:
            await update.message.reply_text("❌ Please specify a template name!")
            return
        
        template_name = words[0]
        top_text = ' '.join(words[1:])
        bottom_text = parts[1].strip() if len(parts) > 1 else ""
    else:
        # Simple format: /meme template text
        parts = args.split(' ', 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Please provide both template name and text!")
            return
        template_name = parts[0]
        top_text = parts[1]
        bottom_text = ""
    
    # Validate template
    if template_name not in TEMPLATES:
        await update.message.reply_text(
            f"❌ Unknown template: `{template_name}`\n\n"
            "Available templates: " + ", ".join(get_all_templates()),
            parse_mode='Markdown'
        )
        return
    
    # Limit text length
    if len(top_text) > 100 or len(bottom_text) > 100:
        await update.message.reply_text("⚠️ Text is too long! Keep it under 100 characters per line.")
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("🎨 Generating your meme...")
    
    try:
        # Generate meme
        meme_bytes = create_meme(template_name, top_text, bottom_text)
        
        if meme_bytes:
            # Send meme as photo
            caption = f"🎭 Template: {TEMPLATES[template_name]['name']}"
            if top_text:
                caption += f"\n📝 Top: {top_text}"
            if bottom_text:
                caption += f"\n📝 Bottom: {bottom_text}"
            
            await update.message.reply_photo(
                photo=meme_bytes,
                caption=caption
            )
            await processing_msg.delete()
        else:
            await update.message.reply_text("❌ Failed to generate meme. Please try again with different text.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: Could not generate meme. Please try again.")
        print(f"Error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "*🤖 Meme Generator Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/templates - List all meme templates\n\n"
        "*To generate a meme:*\n"
        "`/meme template_name Your top text | Your bottom text`\n\n"
        "*Examples:*\n"
        "• `/meme drake Music | Coding`\n"
        "• `/meme two_buttons Go to bed | Code all night`\n"
        "• `/meme distracted Me doing homework | My brain`\n\n"
        "*Pro tip:* Use the vertical bar `|` to separate top and bottom text!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again.")

# === MAIN FUNCTION ===
async def main():
    """Initialize and run the Telegram bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("templates", show_templates))
    application.add_handler(CommandHandler("meme", generate_meme))
    application.add_error_handler(error_handler)
    
    # Start bot with polling
    print("🤖 Meme Bot is starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ Meme Bot is running successfully!")
    
    # Keep bot running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# === ENTRY POINT ===
if __name__ == "__main__":
    # Run Flask in a separate thread for health checks
    def run_flask():
        flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run the bot
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
