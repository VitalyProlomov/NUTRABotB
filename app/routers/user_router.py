from pathlib import Path

from aiogram import F, Router
from aiogram.client import bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram import Bot

import app.utils
import app.keyboards.general_keyboards as gkb
import app.database.requests as rq
import config
import texts
from app import utils
from app.middlewares import TestMiddleWare
from texts import SUBSCRIPTION_NEEDED_MESSAGE, WELCOME_MESSAGE, GREETINGS_SUBSCRIBED_MESSAGE

scheduler = utils.scheduler

router1 = Router()
router1.message.middleware(TestMiddleWare())



class Reg(StatesGroup):
    name = State()
    number = State()


@router1.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    if await rq.does_user_exist(message.from_user.id):
        await bot.send_message(message.from_user.id, "Чтобы перезапустить бота, напишите /restart")
        return
    # Since bot can only be started with /start command
    # await bot.send_message(message.from_user.id, "Message sent")
    await rq.set_user(message)
    # await bot.send_message(message.chat.id,
    #                         text="<b>Bold</b>, <i>italic</i>, <u>underline</u>",
    #                         parse_mode=ParseMode.HTML)



    # await bot.send_message(message.chat.id, text)
    if message.from_user.id in config.ADMIN_IDS:
        await message.reply("Добро пожаловать, Админ! Используйте /admin для доступа к панели админа")
        return

    await bot.send_video_note(message.chat.id, video_note=FSInputFile("assets/videos/welcome_video_note.mp4"))

    if not await app.utils.check_user_subscription(message.from_user.id, bot):
        await message.answer(WELCOME_MESSAGE,
                             reply_markup=gkb.subscription_key_board,
                             parse_mode=ParseMode.HTML)
        await app.utils.add_subscription_reminder(bot, message)
        return

    await print_greet_message(message, bot)
    await app.utils.add_timer_for_lessons_message(1, message, bot)

@router1.message(Command('restart'))
async def restart(message: Message, bot: Bot):
    if await rq.does_user_exist(message.from_user.id):
        res = await rq.remove_user(message.chat.id)

        if res:
            await cmd_start(message, bot)
        else:
            await bot.send_message(message.from_user.id, "Cannot restart currently")
    else:
        await cmd_start(message, bot)

async def print_greet_message(message: Message, bot: Bot):
    image_path = Path("assets/images/1.jpg")

    if image_path.exists():
        # await bot.send_video_note()
        await bot.send_photo(message.chat.id,
                         photo= FSInputFile(image_path),
                         caption = GREETINGS_SUBSCRIBED_MESSAGE,
                           reply_markup=gkb.lesson_1_keyboard,
                           parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(message.chat.id, GREETINGS_SUBSCRIBED_MESSAGE,
                               reply_markup=gkb.lesson_1_keyboard,
                           parse_mode=ParseMode.HTML)
        print("ERROR: Photo not found")


# asyncio.get_event_loop().run_until_complete() ?? dont know how to fix event loop is closed error


@router1.callback_query(F.data.startswith("next_lesson"))
async def send_lesson_message_from_button_click(callback: CallbackQuery, bot : Bot):
    index = callback.data.split("_")[-1]
    scheduler.remove_all_jobs()
    await utils.send_lesson_message(int(index), message=callback.message, bot=bot)


@router1.callback_query(F.data.startswith("selected_webinar_time"))
async def set_webinar_time_date(callback: CallbackQuery, bot : Bot):
    time = callback.data.split("_")[-1]
    user_tg_id = callback.from_user.id
    webinar_date = await rq.get_user_webinar_date(user_tg_id)

    if webinar_date is not None and utils.did_webinar_date_come(webinar_date):
        return

    await rq.set_webinar_date_as_next_day(user_tg_id)

    if webinar_date is not None and utils.did_webinar_date_come(webinar_date):
        return # buttons expired
    if webinar_date is None or not utils.did_webinar_date_come(webinar_date):
        await rq.change_webinar_time(time, user_tg_id)

        scheduler.remove_all_jobs()
        await utils.add_timer_for_webinar_reminders(bot, callback, 1)


#
# @router1.callback_query(F.data == "mark_purchase")
# async def markPurchase(message: Message):
#     await rq.mark_purchase(message.from_user.id)
#     await message.answer("Отлично, спасибо за покупку :)")


@router1.callback_query(F.data == 'check_subscription')
async def check_subscription(callback: CallbackQuery, bot: Bot):
    if not await app.utils.check_user_subscription(callback.from_user.id, bot):
        await bot.send_message(callback.message.chat.id, SUBSCRIPTION_NEEDED_MESSAGE,
                           parse_mode=ParseMode.HTML,
                               reply_markup=gkb.subscription_key_board)
        return False
    else:
        await print_greet_message(callback.message, bot)
        await app.utils.add_timer_for_lessons_message(1, callback.message, bot)

        return True



@router1.callback_query(F.data == 'chosen_at_1_questionary_no')
async def restart_webinar_reminders(callback: CallbackQuery, bot: Bot):
    scheduler.remove_all_jobs()

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(callback.from_user.id)
    await utils.send_lesson_message(3, message=callback.message, bot=bot)


@router1.callback_query(F.data.startswith("chosen_at_1_questionary_yes"))
async def continue_with_selling_offer(callback: CallbackQuery, bot : Bot):
    scheduler.remove_all_jobs()
    # For the 2nd question not to apper when user ansers 'yes' in 1st question
    await utils.set_flag_2(callback.from_user.id)

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    await rq.reset_webinar_date_time(callback.from_user.id)
    await utils.send_final_offer_message(bot, callback, 1)


@router1.callback_query(F.data == 'chosen_at_2_questionary_no')
async def restart_webinar_reminders(callback: CallbackQuery, bot: Bot):
    scheduler.remove_all_jobs()

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(callback.from_user.id)
    await utils.send_lesson_message(3, message=callback.message, bot=bot)


@router1.callback_query(F.data.startswith("chosen_at_2_questionary_yes"))
async def continue_with_final_selling_offer(callback: CallbackQuery, bot : Bot):
    scheduler.remove_all_jobs()

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    await rq.reset_webinar_date_time(callback.from_user.id)
    await utils.send_final_offer_message(bot, callback, 1)



# async def edit_subscribe_message(message: Message, bot: Bot):
#     await message.edit_text('Добро пожаловать в НУТРА Бот. Не забудьте заглянуть на наш сайт с лучшими нутрициологическими продуктами '
#                             'По данной ссылке специально для вас действует временная скидка',
#                             # 'Welcome to the NUTRA BOT. Here is a link to the website with the best nutrition plans for you.\n'
#                             # 'Make sure to check out current sale',
#                             reply_markup=gkb.lesson_1_keyboard)
#     await app.utils.add_timer_for_lessons_message(1, message, bot)

    #TODO sssaaa
# @router1.message(F.text == 'Изменить исходные дожимающие сообщения')
# async def change_selling_messages_texts(message: Message, bot: Bot):

# ORDER OF METHODS MATTER - for example with the method above - if one handler is satisfied, then
# message will be answered => all the other handlers won`t be looked at.