import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import aiohttp
from aiohttp import BasicAuth
from aiohttp import web

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states
NAME, WHATSAPP, GMAIL, CHOOSE_CRYPTO, SELECT_PLAN, WALLET, GETUPI, PAYMENT_CONFIRMATION, USERDETAILS, FINAL = range(10)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_UPI_ID = os.getenv('OWNER_UPI_ID')
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Async function to send email using Mailgun
async def send_email(details: str, user_email: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=BasicAuth("api", MAILGUN_API_KEY),
                data={
                    "from": f"FIM Bot <{user_email}>",
                    "to": [RECIPIENT_EMAIL],
                    "subject": "New Transaction Alert",
                    "text": details,
                },
            ) as response:
                if response.status == 200:
                    logger.info("Email sent successfully.")
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to send email. Status code: {response.status}, Error: {response_text}")
    except Exception as e:
        logger.error(f"Error occurred while sending email: {e}")

# Command handlers
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome to FIM CRYPTO EXCHANGE! Please provide your name (letters only):")
    return NAME

async def validate_name(update: Update, context: CallbackContext) -> int:
    name = update.message.text
    if re.match(r"^[a-zA-Z\s]+$", name):
        context.user_data['name'] = name
        await update.message.reply_text("Name saved! Please enter your WhatsApp number (10 digits):")
        return WHATSAPP
    else:
        await update.message.reply_text("Invalid name. Please enter only letters.")
        return NAME

# ... [rest of the command handlers remain the same] ...

# Set up the application
def setup_application():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_name)],
            WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_whatsapp)],
            GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_gmail)],
            CHOOSE_CRYPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_crypto)],
            SELECT_PLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_plan)],
            WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet)],
            GETUPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_upi)],
            PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
            USERDETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_details)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    return application

# Webhook handler
async def webhook_handler(request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return web.Response(status=500)

# Main function to set up the webhook
async def main():
    global application
    application = setup_application()
    
    # Set up webhook
    webhook_path = f"/webhook/{BOT_TOKEN}"
    webhook_url = f"https://fimbot.onrender.com{webhook_path}"
    await application.bot.set_webhook(url=webhook_url)
    
    # Set up web application
    app = web.Application()
    app.router.add_post(webhook_path, webhook_handler)
    
    return app

if __name__ == '__main__':
    web.run_app(main())

