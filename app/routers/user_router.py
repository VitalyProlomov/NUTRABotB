from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram import Bot

import app.utils
import app.keyboards.general_keyboards as gkb
import app.database.requests as rq
import config
from app import utils
from app.middlewares import TestMiddleWare
from texts import WELCOME_MESSAGE, GREETINGS_SUBSCRIBED_MESSAGE

# ORDER OF METHODS MATTER - for example with the method above - if one handler is satisfied, then
# message will be answered => all the other handlers won`t be looked at.

from app.logger import bot_logger  # Import the logger

scheduler = utils.scheduler

router1 = Router()
router1.message.middleware(TestMiddleWare())


class Reg(StatesGroup):
    name = State()
    number = State()


@router1.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    bot_logger.user_action(user_id=message.chat.id, action="cmd_start")
    if await rq.does_user_exist(message.chat.id):
        await bot.send_message(message.chat.id, "Чтобы перезапустить бота, напишите /restart")
        bot_logger.message_sent(user_id=message.chat.id, message_type="restart_instruction")
        return
    # Since bot can only be started with /start command
    # await bot.send_message(message.chat.id, "Message sent")
    await rq.set_user(message)
    bot_logger.job_scheduled(user_id=message.chat.id, job_name="set_user", execution_time="immediate")

    # await bot.send_message(message.chat.id,
    #                         text="<b>Bold</b>, <i>italic</i>, <u>underline</u>",
    #                         parse_mode=ParseMode.HTML)

    if message.chat.id in config.ADMIN_IDS:
        await message.reply("Добро пожаловать, Админ! Используйте /admin для доступа к панели админа")
        bot_logger.message_sent(user_id=message.chat.id, message_type="admin_welcome")
        return

    # TODO Change video_note
    await bot.send_video_note(message.chat.id, video_note=FSInputFile("assets/videos/welcome_video_note_new.mp4"))
    bot_logger.message_sent(user_id=message.chat.id, message_type="welcome_video_note")

    #if not await app.utils.check_user_subscription(message.chat.id, bot):
    await message.answer(WELCOME_MESSAGE,
                     reply_markup=gkb.choose_time_keyboard,
                     parse_mode=ParseMode.HTML)
    bot_logger.message_sent(user_id=message.chat.id, message_type="welcome_message")
    await app.utils.add_subscription_reminder(bot, message)
    bot_logger.job_scheduled(user_id=message.chat.id, job_name="subscription_reminder", execution_time="future")
    # return #must be in the if statement

    # these must be if subscription check is necessary
    # await print_greet_message(message, bot)
    # await app.utils.add_timer_for_lessons_message(1, message, bot)


@router1.message(Command('restart'))
async def restart(message: Message, bot: Bot):
    bot_logger.user_action(user_id=message.chat.id, action="restart")
    app.utils.remove_all_user_jobs(message.chat.id)
    bot_logger.job_executed(user_id=message.chat.id, job_name="remove_all_user_jobs")

    if await rq.does_user_exist(message.chat.id):
        res = await rq.remove_user(message.chat.id)
        bot_logger.job_executed(user_id=message.chat.id, job_name="remove_user", status="success" if res else "failed")
        if res:
            await app.routers.user_router.cmd_start(message, bot)
        else:
            await bot.send_message(message.chat.id, "Cannot restart currently")
            bot_logger.message_sent(user_id=message.chat.id, message_type="restart_error")
    else:
        await app.routers.user_router.cmd_start(message, bot)


async def print_greet_message(message: Message, bot: Bot):
    image_path = Path("assets/images/1.jpg")
    bot_logger.debug(f"Checking image path: {image_path}")  # Debug log

    if image_path.exists():
        # await bot.send_video_note()
        await bot.send_photo(message.chat.id,
                         photo= FSInputFile(image_path),
                         caption = GREETINGS_SUBSCRIBED_MESSAGE,
                           reply_markup=gkb.lesson_1_keyboard,
                           parse_mode=ParseMode.HTML)
        bot_logger.message_sent(user_id=message.chat.id, message_type="greetings_photo")
    else:
        await bot.send_message(message.chat.id, GREETINGS_SUBSCRIBED_MESSAGE,
                               reply_markup=gkb.lesson_1_keyboard,
                           parse_mode=ParseMode.HTML)
        bot_logger.message_sent(user_id=message.chat.id, message_type="greetings_message")
        bot_logger.warning(user_id=message.chat.id, context="image_not_found", details=f"Image path: {image_path}")
        print("ERROR: Photo not found")


# asyncio.get_event_loop().run_until_complete() ?? dont know how to fix event loop is closed error


@router1.callback_query(F.data.startswith("next_lesson"))
async def send_lesson_message_from_button_click(callback: CallbackQuery, bot : Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="next_lesson_click")
    index = callback.data.split("_")[-1]
    utils.remove_all_user_jobs(callback.from_user.id)
    bot_logger.job_executed(user_id=callback.from_user.id, job_name="remove_all_user_jobs")
    user_tg_id = callback.from_user.id
    await rq.add_did_press_lesson_himself_metric(tg_id=user_tg_id, lesson_index=int(index))
    bot_logger.job_scheduled(user_id=user_tg_id, job_name="add_did_press_lesson_metric", execution_time="immediate")
    await utils.send_lesson_message(int(index), message=callback.message, bot=bot)
    bot_logger.message_sent(user_id=user_tg_id, message_type=f"lesson_message_{index}")


@router1.callback_query(F.data.startswith("selected_webinar_time"))
async def set_webinar_time_date(callback: CallbackQuery, bot : Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="selected_webinar_time")
    time = callback.data.split("_")[-1]
    user_tg_id = callback.from_user.id
    webinar_date = await rq.get_user_webinar_date(user_tg_id)

    # Check for buttons to be active - must happen before or other logic
    # Removed button expiring

    # if webinar_date is not None and utils.did_webinar_date_come(webinar_date):
    #     return # buttons expired

    utils.remove_all_user_jobs(tg_id=callback.from_user.id)
    bot_logger.job_executed(user_id=user_tg_id, job_name="remove_all_user_jobs")

    if callback.from_user.first_name != "Fake_User_Callback" or callback.from_user.last_name != "Scheduled":
        await rq.add_choose_time_himself_metric(user_tg_id)
        bot_logger.job_scheduled(user_id=user_tg_id, job_name="add_choose_time_metric", execution_time="immediate")

    await rq.set_webinar_date_as_next_day(user_tg_id)
    bot_logger.job_scheduled(user_id=user_tg_id, job_name="set_webinar_date", execution_time="next_day")

    # if webinar_date is None or not utils.did_webinar_date_come(webinar_date):
    await rq.change_webinar_time(time, user_tg_id)
    bot_logger.job_scheduled(user_id=user_tg_id, job_name="change_webinar_time", execution_time="immediate")

    utils.remove_all_user_jobs(callback.from_user.id)
    await utils.add_timer_for_webinar_reminders(bot, callback, 1)
    bot_logger.job_scheduled(user_id=user_tg_id, job_name="add_webinar_reminder", execution_time="future")


# @router1.callback_query(F.data == 'check_subscription')
# async def check_subscription(callback: CallbackQuery, bot: Bot):
#     bot_logger.user_action(user_id=callback.from_user.id, action="check_subscription")
#     if not await app.utils.check_user_subscription(callback.from_user.id, bot):
#         await bot.send_message(callback.from_user.id, SUBSCRIPTION_NEEDED_MESSAGE,
#                            parse_mode=ParseMode.HTML,
#                                reply_markup=gkb.lesson_1_keyboard)
#         bot_logger.message_sent(user_id=callback.from_user.id, message_type="subscription_needed")
#         return False
#     else:
#         await print_greet_message(callback.message, bot)
#         await app.utils.add_timer_for_lessons_message(1, callback.message, bot)
#         bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="add_lessons_message_timer", execution_time="future")
#         return True


@router1.callback_query(F.data == 'chosen_at_1_questionary_no')
async def restart_webinar_reminders(callback: CallbackQuery, bot: Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="chosen_at_1_questionary_no")
    utils.remove_all_user_jobs(callback.from_user.id)
    bot_logger.job_executed(user_id=callback.from_user.id, job_name="remove_all_user_jobs")

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(callback.from_user.id)
    bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="reset_webinar_date_time", execution_time="immediate")
    await utils.send_lesson_message(1, message=callback.message, bot=bot)
    bot_logger.message_sent(user_id=callback.from_user.id, message_type="lesson_message_3")


@router1.callback_query(F.data.startswith("chosen_at_1_questionary_yes"))
async def continue_with_selling_offer(callback: CallbackQuery, bot : Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="chosen_at_1_questionary_yes")
    utils.remove_all_user_jobs(callback.from_user.id)
    bot_logger.job_executed(user_id=callback.from_user.id, job_name="remove_all_user_jobs")

    # For the 2nd question not to apper when user answers 'yes' in 1st question
    await utils.set_flag_2(callback.from_user.id)
    bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="set_flag_2", execution_time="immediate")

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    await rq.reset_webinar_date_time(callback.from_user.id)
    bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="reset_webinar_date_time", execution_time="immediate")
    await utils.send_first_offer_message(bot, callback, 1)
    bot_logger.message_sent(user_id=callback.from_user.id, message_type="first_offer_message")


@router1.callback_query(F.data == 'chosen_at_2_questionary_no')
async def restart_webinar_reminders(callback: CallbackQuery, bot: Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="chosen_at_2_questionary_no")
    utils.remove_all_user_jobs(callback.from_user.id)
    bot_logger.job_executed(user_id=callback.from_user.id, job_name="remove_all_user_jobs")

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(callback.from_user.id)
    bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="reset_webinar_date_time", execution_time="immediate")
    await utils.send_lesson_message(1, message=callback.message, bot=bot)
    bot_logger.message_sent(user_id=callback.from_user.id, message_type="lesson_message_3")


@router1.callback_query(F.data.startswith("chosen_at_2_questionary_yes"))
async def continue_with_final_selling_offer(callback: CallbackQuery, bot : Bot):
    bot_logger.user_action(user_id=callback.from_user.id, action="chosen_at_2_questionary_yes")
    utils.remove_all_user_jobs(callback.from_user.id)
    bot_logger.job_executed(user_id=callback.from_user.id, job_name="remove_all_user_jobs")

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    await rq.reset_webinar_date_time(callback.from_user.id)
    bot_logger.job_scheduled(user_id=callback.from_user.id, job_name="reset_webinar_date_time", execution_time="immediate")

    await utils.send_final_offer_message(bot, callback, 1)

# async def edit_subscribe_message(message: Message, bot: Bot):
#     await message.edit_text('Добро пожаловать в НУТРА Бот. Не забудьте заглянуть на наш сайт с лучшими нутрициологическими продуктами '
#                             'По данной ссылке специально для вас действует временная скидка',
#                             # 'Welcome to the NUTRA BOT. Here is a link to the website with the best nutrition plans for you.\n'
#                             # 'Make sure to check out current sale',
#                             reply_markup=gkb.lesson_1_keyboard)
#     await app.utils.add_timer_for_lessons_message(1, message, bot)


# @router1.message(F.text == 'Изменить исходные дожимающие сообщения')
# async def change_selling_messages_texts(message: Message, bot: Bot):
