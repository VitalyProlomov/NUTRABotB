import asyncio
import logging
from app.logger import BotLogger  # Import logger
import logger_config  # This sets up logging configuration

from aiogram import Bot, Dispatcher

import app.utils
import texts
import timings
from config import TOKEN
from app.routers.user_router import router1
from app.routers.admin_router import admin_router
from app.database.models import async_main
from app.utils import scheduler

import app.database.requests as rq

from app.logger import bot_logger

async def on_startup():
    bot_logger.debug("Starting up application")

    try:
        await rq.initialize_lesson_messages()
        bot_logger.debug("Lesson messages initialized")

        await rq.initialize_webinar_messages()
        bot_logger.debug("Webinar messages initialized")

        await rq.initialize_first_offer_messages()
        bot_logger.debug("First offer messages initialized")

        await rq.initialize_final_offer_messages()
        bot_logger.debug("Final offer messages initialized")

        bot_logger.debug("Startup completed successfully")

    except Exception as e:
        bot_logger.error(None, "Startup initialization", e)
        raise


async def main():
    bot_logger.info("Starting Telegram bot application")

    try:
        # timings.test_mode()

        await async_main()
        bot_logger.debug("Database initialized")

        await on_startup()
        bot_logger.debug("Startup tasks completed")

        bot_logger.debug("Test mode activated")

        main_bot = Bot(token=TOKEN)
        bot_logger.debug("Bot instance created")

        dp = Dispatcher()
        dp.include_router(router1)
        dp.include_router(admin_router)
        bot_logger.debug("Routers configured")

        scheduler.start()
        bot_logger.debug("Scheduler started")

        bot_logger.info("Bot starting to poll...")
        await dp.start_polling(main_bot, on_startup=on_startup)

        # await app.utils.send_button_message_to_channel(main_bot, text=texts.PINNED_MESSAGE)


    except Exception as e:
        bot_logger.error(None, "Main application", e)
        raise


if __name__ == '__main__':
    try:
        # Logging is already setup by logger_config import
        bot_logger.info("Application starting")
        asyncio.run(main())
    except KeyboardInterrupt:
        bot_logger.info("Application stopped by user")
        print('Exit')
    except Exception as e:
        bot_logger.error(None, "Application crashed", e)
        print(f'Critical error: {e}')