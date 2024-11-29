import logging
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext
)
import aiohttp
from aiohttp import BasicAuth

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states
NAME, WHATSAPP, GMAIL, CHOOSE_CRYPTO, SELECT_PLAN, WALLET, GETUPI, PAYMENT_CONFIRMATION, USERDETAILS, FINAL = range(10)

# Owner's UPI ID for validation
OWNER_UPI_ID = "kspgpraveen157@ybl"

# Async function to send email using Mailgun
async def send_email(details: str):
    API_KEY = "c40b4cf176d8b7848047f78af43181d2-c02fd0ba-2d74e556"
    DOMAIN = "sandbox9e42961865ff435daea67c7af5b358eb.mailgun.org"
    sender_email = "bot@yourdomain.com"
    recipient_email = "fimcryptobot@gmail.com"
    subject = "New Transaction Alert"
    body = details

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.mailgun.net/v3/{DOMAIN}/messages",
                auth=BasicAuth("api", API_KEY),
                data={
                    "from": f"FIM Bot <{sender_email}>",
                    "to": [recipient_email],
                    "subject": subject,
                    "text": body,
                },
            ) as response:
                if response.status == 200:
                    logger.info("Email sent successfully.")
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to send email. Status code: {response.status}, Error: {response_text}")
    except Exception as e:
        logger.error(f"Error occurred while sending email: {e}")

# Step 1: Start command
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome to FIM CRYPTO EXCHANGE! Please provide your name (letters only):")
    return NAME

# Step 2: Validate Name
async def validate_name(update: Update, context: CallbackContext) -> int:
    name = update.message.text
    if re.match(r"^[a-zA-Z\s]+$", name):
        context.user_data['name'] = name
        await update.message.reply_text("Name saved! Please enter your WhatsApp number (10 digits):")
        return WHATSAPP
    else:
        await update.message.reply_text("Invalid name. Please enter only letters.")
        return NAME

# Step 3: Validate WhatsApp Number
async def validate_whatsapp(update: Update, context: CallbackContext) -> int:
    whatsapp = update.message.text
    if re.match(r"^\d{10}$", whatsapp):
        context.user_data['whatsapp'] = whatsapp
        await update.message.reply_text("WhatsApp number saved! Please enter your Gmail address:")
        return GMAIL
    else:
        await update.message.reply_text("Invalid WhatsApp number. Enter a 10-digit number.")
        return WHATSAPP

# Step 4: Validate Gmail
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

# Step 5: Choose Cryptocurrency
async def choose_crypto(update: Update, context: CallbackContext) -> int:
    context.user_data['crypto'] = update.message.text
    if context.user_data['crypto'] == "USDT":
        plan_description = (
            "Now, choose a plan by entering the number (1-8):\n"
            "1. 1$ - 92₹\n"
            "2. 2$ - 184₹\n"
            "3. 3$ - 276₹\n"
            "4. 4$ - 368₹\n"
            "5. 5$ - 458₹\n"
            "8. Others (Enter your amount in dollars):"
        )
    else:
        plan_description = (
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
    await update.message.reply_text(plan_description, reply_markup=ReplyKeyboardRemove())
    return SELECT_PLAN


# ... (previous code remains unchanged)

# Step 6: Choose Plan or Enter Amount
async def choose_plan(update: Update, context: CallbackContext) -> int:
    text = update.message.text

    if context.user_data['crypto'] == "USDT":
        usdt_plans = {
            "1": 92, "2": 184, "3": 276, "4": 368, "5": 458, "8": None
        }
        plans = usdt_plans
        plan_description = (
            "Now, choose a plan by entering the number (1-8):\n"
            "1. 1$ - 92₹\n"
            "2. 2$ - 184₹\n"
            "3. 3$ - 276₹\n"
            "4. 4$ - 368₹\n"
            "5. 5$ - 458₹\n"
            "8. Others (Enter your amount in dollars):"
        )
    else:
        plans = {
            "1": 55, "2": 97, "3": 194, "4": 291, "5": 388, "6": 485, "7": 680, "8": None
        }
        plan_description = (
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

    if text in plans and text != "8":
        context.user_data['amount'] = plans[text]
        await update.message.reply_text(f"Plan selected: {plans[text]}₹\nNow, enter your wallet address:")
        return WALLET
    elif text == "8":
        await update.message.reply_text("Enter your amount in dollars:")
        return SELECT_PLAN
    

    try:
        amount = float(text)
        if context.user_data['crypto'] == "USDT":
            amount_inr = amount * 92
            if amount >= 5:
                context.user_data['amount'] = amount_inr
                await update.message.reply_text(f"Custom amount selected: {amount} USD ({amount_inr:.2f}₹)\nNow, enter your wallet address:")
                return WALLET
            else:
                await update.message.reply_text("For USDT, the amount should be at least 5 USD. Please enter a valid amount.")
                return SELECT_PLAN
        else:
            amount_inr = amount * 97
            context.user_data['amount'] = amount_inr
            await update.message.reply_text(f"Custom amount selected: {amount} USD ({amount_inr:.2f}₹)\nNow, enter your wallet address:")
            return WALLET
    except ValueError:
        await update.message.reply_text("Invalid choice. Please choose a valid option (1-7 or 8 for Others).")
        return SELECT_PLAN

# Step 7: Wallet Address
async def wallet(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text
    context.user_data['wallet'] = wallet
    await update.message.reply_text(f"Wallet address saved! Proceed to payment: Pay {context.user_data['amount']} to UPI ID: {OWNER_UPI_ID}.")
    await update.message.reply_text("Please enter your UPI ID:")
    return GETUPI

# Step 8: Get UPI ID
async def get_upi(update: Update, context: CallbackContext) -> int:
    upi = update.message.text
    context.user_data['upi'] = upi
    await update.message.reply_text("UPI ID Saved! Enter your Transaction ID:")
    return PAYMENT_CONFIRMATION

# Step 9: Payment Confirmation
async def payment_confirmation(update: Update, context: CallbackContext) -> int:
    transaction_id = update.message.text
    context.user_data['transaction_id'] = transaction_id
    user_details = (
        f"Name: {context.user_data['name']}\n"
        f"WhatsApp: {context.user_data['whatsapp']}\n"
        f"Gmail: {context.user_data['gmail']}\n"
        f"Cryptocurrency: {context.user_data['crypto']}\n"
        f"Plan: {context.user_data['amount']}\n"
        f"Wallet Address: {context.user_data['wallet']}\n"
        f"UPI ID: {context.user_data['upi']}\n"
        f"Transaction ID: {context.user_data['transaction_id']}"
    )
    await update.message.reply_text(user_details)
    await update.message.reply_text("Confirm your details (yes/no):")
    return USERDETAILS

# User details confirmation
async def user_details(update: Update, context: CallbackContext) -> int:
    confirm = update.message.text.lower()
    if confirm == "yes":
        return await final(update, context)
    else:
        await update.message.reply_text("Please restart the bot and re-enter your details.")
        return ConversationHandler.END

# Final function to send email and end conversation
async def final(update: Update, context: CallbackContext) -> int:
    user_details = (
        f"Name: {context.user_data['name']}\n"
        f"WhatsApp: {context.user_data['whatsapp']}\n"
        f"Gmail: {context.user_data['gmail']}\n"
        f"Cryptocurrency: {context.user_data['crypto']}\n"
        f"Plan: {context.user_data['amount']}\n"
        f"Wallet Address: {context.user_data['wallet']}\n"
        f"UPI ID: {context.user_data['upi']}\n"
        f"Transaction ID: {context.user_data['transaction_id']}"
    )
    await send_email(user_details)
    await update.message.reply_text("Details submitted successfully!")
    await update.message.reply_text("For any issues, contact: @Praveenkumar157. For more inquiries, send an email to: fimcryptobot@gmail.com")
    await update.message.reply_text("THANK YOU! VISIT AGAIN...")
    return ConversationHandler.END

def main() -> None:
    # Your bot token from BotFather
    BOT_TOKEN = "7225698093:AAFp1tuE6O0JRZpCglNuCVfeCgfYowdGxmw"

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

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()

