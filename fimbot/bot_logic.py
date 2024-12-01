import os
import logging
import re
import json
from flask import Flask, request
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import telegram
import aiohttp
from aiohttp.client import BasicAuth
from concurrent.futures import ThreadPoolExecutor
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot setup
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telegram.Bot(token=BOT_TOKEN)

# Set up PostgreSQL connection using SQLAlchemy
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Set up Redis connection
REDIS_URL = os.getenv('REDIS_URL')
redis_client = redis.from_url(REDIS_URL)

# Load other environment variables
OWNER_UPI_ID = os.getenv('OWNER_UPI_ID')
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Define User model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    whatsapp_number = Column(String)
    gmail = Column(String)
    crypto = Column(String)
    amount = Column(Float)
    wallet = Column(String)
    upi = Column(String)
    transaction_id = Column(String)

# Create the tables if not exist
Base.metadata.create_all(engine)

# Define states
NAME, WHATSAPP, GMAIL, CHOOSE_CRYPTO, SELECT_PLAN, WALLET, GETUPI, PAYMENT_CONFIRMATION, USERDETAILS, FINAL = range(10)

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
    user_id = update.effective_user.id
    redis_client.set(f"user:{user_id}:state", NAME)
    await update.message.reply_text("Welcome to FIM CRYPTO EXCHANGE! Please provide your name (letters only):")
    return NAME

async def validate_name(update: Update, context: CallbackContext) -> int:
    name = update.message.text
    user_id = update.effective_user.id
    if re.match(r"^[a-zA-Z\s]+$", name):
        redis_client.hset(f"user:{user_id}", "name", name)
        redis_client.set(f"user:{user_id}:state", WHATSAPP)
        await update.message.reply_text("Name saved! Please enter your WhatsApp number (10 digits):")
        return WHATSAPP
    else:
        await update.message.reply_text("Invalid name. Please enter only letters.")
        return NAME

async def validate_whatsapp(update: Update, context: CallbackContext) -> int:
    whatsapp = update.message.text
    user_id = update.effective_user.id
    if re.match(r"^\d{10}$", whatsapp):
        redis_client.hset(f"user:{user_id}", "whatsapp", whatsapp)
        redis_client.set(f"user:{user_id}:state", GMAIL)
        await update.message.reply_text("WhatsApp number saved! Please enter your Gmail address:")
        return GMAIL
    else:
        await update.message.reply_text("Invalid WhatsApp number. Enter a 10-digit number.")
        return WHATSAPP

async def validate_gmail(update: Update, context: CallbackContext) -> int:
    gmail = update.message.text
    user_id = update.effective_user.id
    if re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", gmail):
        redis_client.hset(f"user:{user_id}", "gmail", gmail)
        redis_client.set(f"user:{user_id}:state", CHOOSE_CRYPTO)
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
    crypto = update.message.text
    user_id = update.effective_user.id
    redis_client.hset(f"user:{user_id}", "crypto", crypto)
    redis_client.set(f"user:{user_id}:state", SELECT_PLAN)
    if crypto == "USDT":
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

async def choose_plan(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    crypto = redis_client.hget(f"user:{user_id}", "crypto").decode('utf-8')

    if crypto == "USDT":
        plans = {
            "1": 92, "2": 184, "3": 276, "4": 368, "5": 458, "8": None
        }
    else:
        plans = {
            "1": 55, "2": 97, "3": 194, "4": 291, "5": 388, "6": 485, "7": 680, "8": None
        }

    if text in plans and text != "8":
        amount = plans[text]
        redis_client.hset(f"user:{user_id}", "amount", amount)
        redis_client.set(f"user:{user_id}:state", WALLET)
        await update.message.reply_text(f"Plan selected: {amount}₹\nNow, enter your wallet address:")
        return WALLET
    elif text == "8":
        await update.message.reply_text("Enter your amount in dollars:")
        return SELECT_PLAN
    
    try:
        amount = float(text)
        if crypto == "USDT":
            amount_inr = amount * 92
            if amount >= 5:
                redis_client.hset(f"user:{user_id}", "amount", amount_inr)
                redis_client.set(f"user:{user_id}:state", WALLET)
                await update.message.reply_text(f"Custom amount selected: {amount} USD ({amount_inr:.2f}₹)\nNow, enter your wallet address:")
                return WALLET
            else:
                await update.message.reply_text("For USDT, the amount should be at least 5 USD. Please enter a valid amount.")
                return SELECT_PLAN
        else:
            amount_inr = amount * 97
            redis_client.hset(f"user:{user_id}", "amount", amount_inr)
            redis_client.set(f"user:{user_id}:state", WALLET)
            await update.message.reply_text(f"Custom amount selected: {amount} USD ({amount_inr:.2f}₹)\nNow, enter your wallet address:")
            return WALLET
    except ValueError:
        await update.message.reply_text("Invalid choice. Please choose a valid option (1-7 or 8 for Others).")
        return SELECT_PLAN

async def wallet(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text
    user_id = update.effective_user.id
    redis_client.hset(f"user:{user_id}", "wallet", wallet)
    redis_client.set(f"user:{user_id}:state", GETUPI)
    amount = redis_client.hget(f"user:{user_id}", "amount").decode('utf-8')
    await update.message.reply_text(f"Wallet address saved! Proceed to payment: Pay {amount} to UPI ID: {OWNER_UPI_ID}.")
    await update.message.reply_text("Please enter your UPI ID:")
    return GETUPI

async def get_upi(update: Update, context: CallbackContext) -> int:
    upi = update.message.text
    user_id = update.effective_user.id
    redis_client.hset(f"user:{user_id}", "upi", upi)
    redis_client.set(f"user:{user_id}:state", PAYMENT_CONFIRMATION)
    await update.message.reply_text("UPI ID Saved! Enter your Transaction ID:")
    return PAYMENT_CONFIRMATION

async def payment_confirmation(update: Update, context: CallbackContext) -> int:
    transaction_id = update.message.text
    user_id = update.effective_user.id
    redis_client.hset(f"user:{user_id}", "transaction_id", transaction_id)
    redis_client.set(f"user:{user_id}:state", USERDETAILS)
    user_data = redis_client.hgetall(f"user:{user_id}")
    user_details = get_user_details(user_data)
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
    user_id = update.effective_user.id
    user_data = redis_client.hgetall(f"user:{user_id}")
    user_details = get_user_details(user_data)
    await send_email(user_details, user_data[b'gmail'].decode('utf-8'))
    
    # Save user data to PostgreSQL database
    session = Session()
    try:
        user = User(
            name=user_data[b'name'].decode('utf-8'),
            whatsapp_number=user_data[b'whatsapp'].decode('utf-8'),
            gmail=user_data[b'gmail'].decode('utf-8'),
            crypto=user_data[b'crypto'].decode('utf-8'),
            amount=float(user_data[b'amount'].decode('utf-8')),
            wallet=user_data[b'wallet'].decode('utf-8'),
            upi=user_data[b'upi'].decode('utf-8'),
            transaction_id=user_data[b'transaction_id'].decode('utf-8')
        )
        session.add(user)
        session.commit()
        logger.info(f"User data saved to database: {user.id}")
    except Exception as e:
        logger.error(f"Error saving user data to database: {e}")
        session.rollback()
    finally:
        session.close()

    # Clear user data from Redis
    redis_client.delete(f"user:{user_id}")
    redis_client.delete(f"user:{user_id}:state")

    await update.message.reply_text(f"Thank you, {user_data[b'name'].decode('utf-8')}! Your information has been saved.")
    await update.message.reply_text("For any issues, contact: @Praveenkumar157. For more inquiries, send an email to: fimcryptobot@gmail.com")
    await update.message.reply_text("THANK YOU! VISIT AGAIN...")
    return ConversationHandler.END

def get_user_details(user_data):
    return (
        f"Name: {user_data[b'name'].decode('utf-8')}\n"
        f"WhatsApp: {user_data[b'whatsapp'].decode('utf-8')}\n"
        f"Gmail: {user_data[b'gmail'].decode('utf-8')}\n"
        f"Cryptocurrency: {user_data[b'crypto'].decode('utf-8')}\n"
        f"Plan: {user_data[b'amount'].decode('utf-8')}\n"
        f"Wallet Address: {user_data[b'wallet'].decode('utf-8')}\n"
        f"UPI ID: {user_data[b'upi'].decode('utf-8')}\n"
        f"Transaction ID: {user_data[b'transaction_id'].decode('utf-8')}"
    )

# Set up the application
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

# Webhook route for Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram."""
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json.loads(json_str), bot)
    
    # Use ThreadPoolExecutor to handle updates asynchronously
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.submit(application.process_update, update)
    
    return 'ok'

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render."""
    return 'OK', 200

@app.before_first_request
def setup_webhook():
    """Set the Telegram bot webhook when the application starts."""
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL')}/webhook"
    try:
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook successfully set to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
</ReactProject>
