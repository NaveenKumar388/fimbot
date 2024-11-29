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
NAME, WHATSAPP, GMAIL, CHOOSE_CRYPTO, SELECT_PLAN, WALLET, GETUPI, PAYMENT_CONFIRMATION = range(8)

# Owner's UPI ID for validation
OWNER_UPI_ID = "kspgpraveen157@ybl"

# Async function to send email using Mailgun
async def send_email(details: str):
    API_KEY = "f0ba9eea684836864cae3256414c0b3f-c02fd0ba-481e7eb0"
    DOMAIN = "sandbox9e42961865ff435daea67c7af5b358eb.mailgun.org"
    sender_email = "bot@yourdomain.com"
    recipient_email = "fimcryptobot@gmail.com"
    subject = "New Transaction Alert"
    body = details

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.mailgun.net/v3/{DOMAIN}/messages",
                auth=BasicAuth("api", API_KEY),  # Use BasicAuth here
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
                    logger.error(f"Failed to send email. Status code: {response.status}")
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
    await update.message.reply_text(
        "Now, choose a plan by entering the number (1-8):\n"
        "1. 0.5$ - 55₹\n"
        "2. 1$ - 97₹\n"
        "3. 2$ - 194₹\n"
        "4. 3$ - 291₹\n"
        "5. 4$ - 388₹\n"
        "6. 5$ - 485₹\n"
        "7. 7$ - 680₹\n"
        "8. Others (Enter your amount in dollars):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return SELECT_PLAN


#Step 6: Choose Plan or Enter Amount (for USDT)
async def choose_plan(update: Update, context: CallbackContext) -> int:
    text = update.message.text

    if context.user_data['crypto'] == "USDT":
        # USDT plans mapping
        usdt_plans = {
            "1": "92₹ (1 USDT)",
            "2": "184₹ (2 USDT)",
            "3": "276₹ (3 USDT)",
            "4": "368₹ (4 USDT)",
            "5": "458₹ (5 USDT)",
        }

        if text in usdt_plans:  # If the user selects a predefined USDT plan
            context.user_data['amount'] = usdt_plans[text]
            logger.info(f"USDT Plan selected: {usdt_plans[text]}")
            await update.message.reply_text(f"Plan selected: {usdt_plans[text]}\nNow, enter your wallet address:")
            return WALLET

        elif text == "8":  # If the user selects "Others" for USDT
            await update.message.reply_text("Enter your amount in dollars (Minimum 5 USD):")
            return SELECT_PLAN  # Stay in this state to accept the custom input

        else:
            logger.warning(f"Invalid plan selection for USDT: {text}")
            await update.message.reply_text("Invalid choice. Please choose a valid option (1-7 or 8 for Others).")
            return SELECT_PLAN

    else:
        # Handle non-USDT plans (same as before)
        plans = {
            "1": "55₹ (0.5$)",
            "2": "97₹ (1$)",
            "3": "194₹ (2$)",
            "4": "291₹ (3$)",
            "5": "388₹ (4$)",
            "6": "485₹ (5$)",
            "7": "680₹ (7$)"
        }

        if text in plans:  # If the user selects a predefined plan
            context.user_data['amount'] = plans[text]
            logger.info(f"Plan selected: {plans[text]}")
            await update.message.reply_text(f"Plan selected: {plans[text]}\nNow, enter your wallet address:")
            return WALLET

        elif text == "8":  # Custom amount
            await update.message.reply_text("Enter your amount in dollars :")
            return SELECT_PLAN  # Stay in this state to accept the custom input

        else:
            logger.warning(f"Invalid plan selection: {text}")
            await update.message.reply_text("Invalid choice. Please choose a valid option (1-7 or 8 for Others).")
            return SELECT_PLAN


# Step 6.1: Handle Custom Amount (only for USDT and plan 8)
async def handle_custom_amount(update: Update, context: CallbackContext) -> int:
    # Ensure this only runs if the selected crypto is USDT and the plan is 8
    if context.user_data.get('crypto') == "USDT" and context.user_data.get('amount') == "8":
        amount = update.message.text
        try:
            # Check if the input is a valid number and greater than or equal to 5
            amount = float(amount)
            if amount >= 5:
                context.user_data['amount'] = f"{amount} USD"
                logger.info(f"Custom amount selected: {amount} USD")
                await update.message.reply_text(f"Custom amount selected: {amount} USD\nNow, enter your wallet address:")
                return WALLET
            else:
                await update.message.reply_text("Amount should be at least 5 USD. Please enter a valid amount.")
                return SELECT_PLAN
        except ValueError:
            await update.message.reply_text("Invalid amount. Please enter a numeric value.")
            return SELECT_PLAN
    else:
        # If it's not USDT or plan 8, just proceed to the next step without handling custom amount
        await update.message.reply_text("Please select a valid plan or try again.")
        return SELECT_PLAN

        


# Step 7: Wallet Address
async def wallet(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text
    context.user_data['wallet'] = wallet
    await update.message.reply_text("Wallet address saved! Please enter your UPI ID:")
    return GETUPI


# Step 8: Get UPI ID
async def get_upi(update: Update, context: CallbackContext) -> int:
    upi_id = update.message.text
    context.user_data['upi_id'] = upi_id
    await update.message.reply_text("UPI ID saved! Please enter your transaction ID:")
    return PAYMENT_CONFIRMATION


# Step 9: Payment Confirmation
async def payment_confirmation(update: Update, context: CallbackContext) -> int:
    transaction_id = update.message.text
    context.user_data['transaction_id'] = transaction_id

    details = (
        f"Name: {context.user_data['name']}\n"
        f"WhatsApp: {context.user_data['whatsapp']}\n"
        f"Gmail: {context.user_data['gmail']}\n"
        f"Crypto: {context.user_data['crypto']}\n"
        f"Amount: {context.user_data['amount']}\n"
        f"Wallet: {context.user_data['wallet']}\n"
        f"UPI ID: {context.user_data['upi_id']}\n"
        f"Transaction ID: {transaction_id}\n"
    )

    try:
        await send_email(details)
        await update.message.reply_text(
            "Details submitted successfully! Please kindly wait. We will send crypto within 1 hour and inform you via email!"
        )
        await update.message.reply_text(
            "Any issues - Contact: @Praveenkumar157 ")
        await update.message.reply_text("For more inquiries,send mail to: fimcryptobot@gmail.com \n THANK YOU! VISIT AGAIN!"       )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")
        logger.error(f"Error in payment_confirmation: {e}")
        return ConversationHandler.END


# Cancel command
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation canceled. You can restart with /start.")
    return ConversationHandler.END


# Main function
def main():
    application = Application.builder().token('7556988669:AAEAswtPq7xG4Z5zhB78_FBgmqKDRKvg990').build()

    conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_name)],
        WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_whatsapp)],
        GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_gmail)],
        CHOOSE_CRYPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_crypto)],
        SELECT_PLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_plan)],
        WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet)],
        GETUPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_upi)],
        PAYMENT_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_confirmation)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
   )
  

    application.add_handler(conversation_handler)
    application.run_polling()


if __name__ == '__main__':
    main()

