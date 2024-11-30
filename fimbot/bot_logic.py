import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from aiohttp import web
import asyncio


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

async def validate_whatsapp(update: Update, context: CallbackContext) -> int:
    whatsapp = update.message.text
    if re.match(r"^\d{10}$", whatsapp):
        context.user_data['whatsapp'] = whatsapp
        await update.message.reply_text("WhatsApp number saved! Please enter your Gmail address:")
        return GMAIL
    else:
        await update.message.reply_text("Invalid WhatsApp number. Enter a 10-digit number.")
        return WHATSAPP

async def validate_gmail(update: Update, context: CallbackContext) -> int:
    gmail = update.message.text
    if re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", gmail):
        context.user_data['gmail'] = gmail
        await update.message.reply_text(
            "Gmail saved! Choose your cryptocurrency:",
            reply_markup=ReplyKeyboardMarkup(
                [['BNB', 'USDT', 'TON'], ['POL', 'SUI', 'NEAR'], ['LTC', 'ARB', 'TRX']],
                one_time_keyboard=True,
            ),
        )
        return CHOOSE_CRYPTO
    else:
        await update.message.reply_text("Invalid Gmail. Enter a valid Gmail address.")
        return GMAIL

async def choose_crypto(update: Update, context: CallbackContext) -> int:
    context.user_data['crypto'] = update.message.text
    plan_description = get_plan_description(context.user_data['crypto'])
    await update.message.reply_text(plan_description, reply_markup=ReplyKeyboardRemove())
    return SELECT_PLAN

async def choose_plan(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    plans = get_plans(context.user_data['crypto'])

    if text in plans and text != "8":
        context.user_data['amount'] = plans[text]
        await update.message.reply_text(f"Plan selected: {plans[text]}₹\nNow, enter your wallet address:")
        return WALLET
    elif text == "8":
        await update.message.reply_text("Enter your amount in dollars:")
        return SELECT_PLAN
    
    try:
        amount = float(text)
        amount_inr = calculate_amount_inr(amount, context.user_data['crypto'])
        if amount_inr:
            context.user_data['amount'] = amount_inr
            await update.message.reply_text(f"Custom amount selected: {amount} USD ({amount_inr:.2f}₹)\nNow, enter your wallet address:")
            return WALLET
        else:
            await update.message.reply_text("Invalid amount. Please enter a valid amount.")
            return SELECT_PLAN
    except ValueError:
        await update.message.reply_text("Invalid choice. Please choose a valid option (1-7 or 8 for Others).")
        return SELECT_PLAN

async def wallet(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text
    context.user_data['wallet'] = wallet
    await update.message.reply_text(f"Wallet address saved! Proceed to payment: Pay {context.user_data['amount']} to UPI ID: {OWNER_UPI_ID}.")
    await update.message.reply_text("Please enter your UPI ID:")
    return GETUPI

async def get_upi(update: Update, context: CallbackContext) -> int:
    upi = update.message.text
    context.user_data['upi'] = upi
    await update.message.reply_text("UPI ID Saved! Enter your Transaction ID:")
    return PAYMENT_CONFIRMATION

async def payment_confirmation(update: Update, context: CallbackContext) -> int:
    transaction_id = update.message.text
    context.user_data['transaction_id'] = transaction_id
    user_details = get_user_details(context.user_data)
    await update.message.reply_text(user_details)
    await update.message.reply_text("Confirm your details (yes/no):")
    return USERDETAILS

async def user_details(update: Update, context: CallbackContext) -> int:
    confirm = update.message.text.lower()
    if confirm == "yes":
        return await final(update, context)
    else:
        await update.message.reply_text("Please restart the bot and re-enter your details.")
        return ConversationHandler.END

async def final(update: Update, context: CallbackContext) -> int:
    user_details = get_user_details(context.user_data)
    await send_email(user_details, context.user_data['gmail'])
    await update.message.reply_text("Details submitted successfully!")
    await update.message.reply_text("For any issues, contact: @Praveenkumar157. For more inquiries, send an email to: fimcryptobot@gmail.com")
    await update.message.reply_text("THANK YOU! VISIT AGAIN...")
    return ConversationHandler.END

# Helper functions
def get_plan_description(crypto):
    if crypto == "USDT":
        return (
            "Now, choose a plan by entering the number (1-8):\n"
            "1. 1$ - 92₹\n"
            "2. 2$ - 184₹\n"
            "3. 3$ - 276₹\n"
            "4. 4$ - 368₹\n"
            "5. 5$ - 458₹\n"
            "8. Others (Enter your amount in dollars):"
        )
    else:
        return (
            "Now, choose a plan by entering the number (1-8):\n"
            "1. 0.5$ - 55₹\n"
            "2. 1$ - 97₹\n"
            "3. 2$ - 194₹\n"
            "4. 3$ - 291₹\n"
            "5. 4$ - 388₹\n"
            "6. 5$ - 485₹\n"
            "7. 7$ - 680₹\n"
            "8. Others (Enter your amount in dollars):"
        )

def get_plans(crypto):
    if crypto == "USDT":
        return {"1": 92, "2": 184, "3": 276, "4": 368, "5": 458, "8": None}
    else:
        return {"1": 55, "2": 97, "3": 194, "4": 291, "5": 388, "6": 485, "7": 680, "8": None}

def calculate_amount_inr(amount, crypto):
    if crypto == "USDT":
        return amount * 92 if amount >= 5 else None
    else:
        return amount * 97

def get_user_details(user_data):
    return (
        f"Name: {user_data['name']}\n"
        f"WhatsApp: {user_data['whatsapp']}\n"
        f"Gmail: {user_data['gmail']}\n"
        f"Cryptocurrency: {user_data['crypto']}\n"
        f"Plan: {user_data['amount']}\n"
        f"Wallet Address: {user_data['wallet']}\n"
        f"UPI ID: {user_data['upi']}\n"
        f"Transaction ID: {user_data['transaction_id']}"
    )

application = None

async def setup_application():
    app = Application.builder().token(BOT_TOKEN).build()

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

    app.add_handler(conv_handler)
    return app
async def webhook_handler(request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return web.Response(status=500)

async def main():
    global application
    application = await setup_application()
    
    # Set up webhook
    webhook_path = f"/webhook/{BOT_TOKEN}"
    webhook_url = f"https://fimbot.onrender.com{webhook_path}"
    await application.bot.set_webhook(url=webhook_url)
    
    # Set up web application
    app = web.Application()
    app.router.add_post(webhook_path, webhook_handler)
    
    return app  # Return the web.Application instance

if __name__ == '__main__':
    web.run_app(main())  # Remove the port argument
