import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from aiohttp import web
import asyncio

# ... (keep all the existing imports and global variables)

async def setup_application():
    # ... (keep the existing setup_application function)

async def webhook_handler(request):
    update = await request.json()
    await application.update_queue.put(Update.de_json(update, application.bot))
    return web.Response()

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
    
    return app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = asyncio.get_event_loop().run_until_complete(main())
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

