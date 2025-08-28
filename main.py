import asyncio
import logging


from aiogram import Bot, Dispatcher

from config import TOKEN
from app.routers.user_router import router1
from app.routers.admin_router import admin_router
from app.database.models import async_main
from app.utils import scheduler

import app.database.requests as rq

async def on_startup():

    await rq.initialize_broadcast_messages()
    await rq.initialize_webinar_messages()
    await rq.initialize_first_offer_messages()
    await rq.initialize_final_offer_messages()

    print("startup worked")

    # await rq.deleteTHIS()


# async def set_bot_commands(bot: Bot):
#     commands = [
#         BotCommand(command="start", description="🚀 Начать работу"),
#     ]
#     await bot.set_my_commands(commands)
#
#     # Устанавливаем описание бота (видно в чате до старта)
#     await bot.set_my_description(
#         description="🤖 Добро пожаловать! Я ваш помощник.\n\n"
#                     "Нажмите /start, чтобы начать."
#     )



async def main():
    await async_main()
    await on_startup()



    # await deleteTHIS()
    # print(await rq.get_selling_message(1))
    bot = Bot(token = TOKEN)
    # await set_bot_commands(bot)
    dp = Dispatcher()
    dp.include_router(router1)
    dp.include_router(admin_router)
    # removes menu
    # await bot.set_my_commands([])
    scheduler.start()

    #TODO
    # await app.utils.sendButtonMessageToChannel(bot)

    await dp.start_polling(bot, on_startup = on_startup)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try :
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
