import asyncio
from datetime import datetime, time
import logging
from aiogram import Bot, Dispatcher

import timings
from config import TOKEN
from app.routers.user_router import router1
from app.routers.admin_router import admin_router
from app.database.models import async_main
from app.utils import scheduler, emergency_scheduler_restart, daily_message_sending_shift, MOSCOW_TZ

from app.logger import bot_logger

# DO NOT REMOVE THE import logger_config IMPORT - IT SETS UP THE LOGGER_INFO WHEN BEING IMPORTED
import logger_config

import app.database.requests as rq

TEST_MODE = False

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

        now = datetime.now(MOSCOW_TZ)
        deadline = datetime.combine(
            now.date(),
            time(hour=23, minute=10),
            tzinfo=MOSCOW_TZ
        )
        # scheduler.add_job(func=func,
        #                   trigger='date',
        #                   next_run_time=date_time,
        #                   args=args,
        #                   id=job_id,
        #                   replace_existing=True)
        scheduler.add_job(func=daily_message_sending_shift, trigger="date",next_run_time=deadline)
        bot_logger.info(f"[Custom log] scheduled job daily_message_sending_shift for {deadline}")

    except Exception as ex:
        bot_logger.error(None, "Startup initialization", ex)
        raise



async def main():
    bot_logger.info("Starting Telegram bot application")

    try:
        # timings.test_mode()
        bot_logger.info("Test mode turned on")

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

        try:
            a = await rq.get_all_not_done_users_ids()

            bot_logger.info(f"Not done Users in db: {len(a)}")
            await emergency_scheduler_restart(bot=main_bot)
        except Exception as ex:
            bot_logger.error(None, "emergency scheduler failed", ex)
        # await app.utils.send_button_message_to_channel(main_bot, text=texts.PINNED_MESSAGE)

        bot_logger.info("Bot starting to poll...")
        await dp.start_polling(main_bot, on_startup=on_startup)



    except Exception as ex:
        bot_logger.error(None, "Main application", ex)
        raise


if __name__ == '__main__':
    try:
        logger_config.setup_logging()
        # Logging is already setup by logger_config import
        bot_logger.info("Application starting")
        asyncio.run(main())
    except KeyboardInterrupt:
        bot_logger.info("Application stopped by user")
        print('Exit')
    except Exception as e:
        bot_logger.error(None, "Application crashed", e)
        print(f'Critical error: {e}')