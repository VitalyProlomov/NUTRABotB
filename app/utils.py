import string
from pathlib import Path
from typing import Any, Optional, Coroutine

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import Message, User, InlineKeyboardMarkup, CallbackQuery, BufferedInputFile, FSInputFile
from datetime import datetime, time, timedelta
import json
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.util import await_only

import app.database.models
import texts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import app.keyboards.general_keyboards as gkb
import app.database.requests as rq
import timings
from timings import FIRST_OFFER_MESSAGE_1_TIME, QUESTION_MESSAGE_1_TIME

scheduler = AsyncIOScheduler()
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

import app.routers.user_router


# # order important due to circular imports - BULLSHIT, try through main
# # also, it is prob not needed in here
# from app.routers.user_router import router1


def log_lesson_message_error(e: Exception):
    RED = "\033[91m"
    RESET = "\033[0m"
    print(f'\n{RED}ERROR{RESET} happened while trying to send a lesson message:  + {e}\n')


async def check_user_subscription(user_id: int, bot: Bot):
    member = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=user_id)
    # print(f'member status: {member.status}\n\n\n')

    return member.status in ['member', 'administrator', 'creator']


async def add_timer_for_lessons_message(lesson_mes_order: int, message: Message, bot: Bot):
    '''
    :param lesson_mes_order: defines which selling message is being scheduled (1 or 2 is available as for 05.05.2025)
    '''
    try:
        lesson_message = await rq.get_lesson_message_info(lesson_mes_order)
        if not lesson_message:  # Optional: Explicitly check if None/empty
            # if there is no lesson message, it means that the number has exceeded the max value of
            # lesson_mes_order => no more lesson messages in database
            await add_timer_for_webinar_time_choice_reminder(bot, message)
            return
    except Exception as e:
        print(f"Error fetching message: {e}")
        lesson_message = None  # or raise a custom exception
        return

    # selling_message = await rq.get_lesson_message_info(selling_mes_order)

    scheduler.add_job(send_lesson_message,
                      trigger='date',
                      run_date=datetime.now() + timedelta(seconds=lesson_message.delay_time_minutes),
                      args=(lesson_mes_order, message, bot))


# The message is the one, that bot writes, so it is important to use chat_id when sending the selling message,
# NOT the message.from_user.id
async def send_lesson_message(lesson_message_order: int, message: Message, bot: Bot):
    try:
        # if not await did_user_mark_purchase(message.from_user.id):
        #     t = await rq.get_lesson_message_info(lesson_message_order)
        #     await bot.send_message(chat_id=message.chat.id, text=t.text,
        #                            reply_markup=gkb.markPurchaseKeyBoard)

        lesson_info = await rq.get_lesson_message_info(lesson_message_order)

        reply_markup = None
        if lesson_info.buttons:
            try:
                # If buttons are stored as JSON string:
                if isinstance(lesson_info.buttons, str):
                    buttons_data = json.loads(lesson_info.buttons)
                else:  # If already a dict (SQLAlchemy JSON type)
                    buttons_data = lesson_info.buttons

                    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons_data["inline_keyboard"])
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                print(f"Error parsing buttons: {e}")
        if lesson_info.image:
            image_file = get_photo_from_database(lesson_info)
            await send_message_with_photo(bot, message.chat.id, image_file, lesson_info.text, reply_markup)
        if lesson_message_order != 1:
            scheduler.remove_all_jobs()
            # await message.edit_reply_markup(reply_markup=None)

        await add_timer_for_lessons_message(int(lesson_message_order) + 1, message, bot)
    except Exception as e:
        log_lesson_message_error(e)


async def add_timer_for_webinar_time_choice_reminder(bot: Bot, message):
    scheduler.add_job(send_webinar_time_choice_reminder, trigger='date',
                      run_date=datetime.now() + timedelta(seconds=timings.WEBINAR_REMINDER_0_AUTO_TIME),
                      args=(bot, message))


async def send_webinar_time_choice_reminder(bot: Bot, message: Message):
    await bot.send_message(chat_id=message.chat.id,
                           text=texts.WEBINAR_REMINDER_0,
                           reply_markup=gkb.webinar_time_choice_keyboard,
                           parse_mode=ParseMode.HTML)

    chat_id: int = message.chat.id
    now = datetime.now(MOSCOW_TZ)

    today_2359 = datetime.combine(
        now.date(),  # Today's date
        time(23, 59, ),  # 23:59 time
        tzinfo=MOSCOW_TZ  # Moscow timezone
    )

    # Build the callback query
    callback_query = CallbackQuery(
        id=f'{chat_id}-{datetime.now()}',
        from_user=User(id=chat_id,
                       is_bot=False,
                       first_name="Fake_User_Callback",
                       last_name="Scheduled",
                       ),
        chat_instance="simulated_instance",
        data="selected_webinar_time_19:00",
        message=message
    )

    # Schedule the job
    scheduler.add_job(
        app.routers.user_router.set_webinar_time_date,
        'date',
        run_date=today_2359,
        id="today_2359_auto_register",
        args=[callback_query, bot]
    )


# Send message to channel
async def send_button_message_to_channel(bot: Bot, text: string):
    await bot.send_message(
        chat_id=config.CHANNEL_ID,
        text=text,
        reply_markup=gkb.channel_link_key_board,
        parse_mode=ParseMode.HTML  # Optional: Supports Markdown/HTML formatting
    )


async def add_subscription_reminder(bot: Bot, message):
    scheduler.add_job(send_subscription_reminder,
                      trigger='date',
                      run_date=datetime.now() + timedelta(seconds=timings.SUBSCRIPTION_REMINDER_1_TIME),
                      args=(bot, 1, message))


async def send_subscription_reminder(bot: Bot, index: int, message: Message):
    if index == 1:
        await bot.send_message(chat_id=message.chat.id, text=texts.SUBSCRIPTION_REMINDER_1,
                               reply_markup=gkb.subscription_key_board,
                               parse_mode=ParseMode.HTML)
        scheduler.add_job(send_subscription_reminder,
                          trigger='date',
                          run_date=datetime.now() + timedelta(seconds=timings.SUBSCRIPTION_REMINDER_2_TIME),
                          args=(bot, 2, message))
        return
    if index == 2:
        await bot.send_message(chat_id=message.chat.id, text=texts.SUBSCRIPTION_REMINDER_2,
                               reply_markup=gkb.subscription_key_board,
                               parse_mode=ParseMode.HTML)


async def add_timer_for_webinar_reminders(bot: Bot, callback: CallbackQuery, reminder_index: int):
    # set the date of message for tomorrow
    if reminder_index == 3:
        time_chosen = await rq.get_user_webinar_time(callback.from_user.id)  # await  ?
        if time_chosen is None:
            time_chosen = "19:00"

        now = datetime.now(MOSCOW_TZ)
        # start_time = now + timedelta(seconds=10) # test line

        start_time = datetime.combine(
            now.date() + timedelta(days=1),  # Next day
            time(hour=6, minute=0),  # At 06:00
            tzinfo=MOSCOW_TZ
        )
        if time_chosen == "19:00":
            start_time += timedelta(hours=19 - 12)  # ? hours - need to check, prob 7

        scheduler.remove_all_jobs()

        scheduler.add_job(
            send_webinar_reminder,
            'date',
            run_date=start_time,
            args=[bot, callback, reminder_index],
            # id=f"nextday9am_{chat_id}_{tomorrow_9am.timestamp()}"
        )
    else:
        delay = await rq.get_webinar_reminder_info(reminder_index)
        delay = delay.delay_time_minutes
        scheduler.add_job(
            send_webinar_reminder,
            'date',
            run_date=datetime.now() + timedelta(seconds=delay),
            args=[bot, callback, reminder_index],
        )


async def send_webinar_reminder(bot: Bot, callback: CallbackQuery, reminder_index: int):
    # if
    text = await rq.get_webinar_reminder_text(reminder_index)
    if text is None:
        print("got None from get_webinar_reminder (Must be out of index for webinar messages)")
        return
    webinar_time = await rq.get_user_webinar_time(callback.from_user.id)
    text = text.format(webinar_time)
    message_info = await rq.get_webinar_reminder_info(reminder_index)
    image_file = get_photo_from_database(message_info)

    if reminder_index == 10:
        await bot.send_video_note(callback.message.chat.id,
                                  video_note=FSInputFile("assets/videos/webinar_video_note.mp4"))
    if message_info.image:
        await send_message_with_photo(bot,
                                      callback.message.chat.id,
                                      image_file,
                                      text,
                                      get_keyboard_from_database(message_info))
    else:
        await bot.send_message(chat_id=callback.message.chat.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )

    if await rq.get_webinar_reminder_text(reminder_index + 1) is None:
        if not await rq.get_user_flag_1(callback.from_user.id):
            scheduler.add_job(send_question_1_message,
                              run_date=datetime.now() + timedelta(seconds=timings.QUESTION_MESSAGE_1_TIME),  # 10 minutes
                              args=[bot, callback.message])
        else:  # not sending question about the webinar appearance 2nd time
            await add_timer_for_first_offer(bot, callback, 1)

        return

    await add_timer_for_webinar_reminders(bot, callback, reminder_index + 1)


async def set_flag_1(user_id: int):
    await rq.set_user_flag_1(user_id)


async def set_flag_2(user_id: int):
    await rq.set_user_flag_2(user_id)


async def send_question_1_message(bot: Bot, message: Message):
    user_id = message.chat.id
    await set_flag_1(user_id)
    await bot.send_photo(chat_id=user_id,
                         photo=FSInputFile(r"assets/images/question_1_photo.jpg"),
                         caption=texts.QUESTION_MESSAGE_1,
                         reply_markup=gkb.question_1_keyboard,
                         parse_mode=ParseMode.HTML)

    scheduler.add_job(restart_webinar_messages,
                      run_date=datetime.now() + timedelta(timings.RESTART_WEBINAR_MESSAGES_TIME),  # 120 minutes
                      args=[message, bot])


async def restart_webinar_messages(message: Message, bot: Bot):
    scheduler.remove_all_jobs()
    user_id = message.chat.id

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(user_id)
    await app.utils.send_lesson_message(3, message=message, bot=bot)


async def send_first_offer_message(bot: Bot, callback: CallbackQuery, order_index):
    text = await rq.get_first_offer_text(order_index)
    if text is None:
        print("got None from get_first_offer_text (Must be out of index for first offer messages)")
        return

    message_info = await rq.get_first_offer_info(order_index)

    if message_info.image:
        photo = get_photo_from_database(message_info)
        await send_message_with_photo(bot,
                                      callback.message.chat.id,
                                      photo,
                                      message_info.text,
                                      get_keyboard_from_database(message_info))
    else:
        await bot.send_message(chat_id=callback.message.chat.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )

    if await rq.get_first_offer_text(order_index + 1) is None:
        if not await rq.get_user_flag_2(callback.from_user.id):
            scheduler.add_job(send_question_2_message,
                              run_date=datetime.now() + timedelta(seconds=timings.QUESTION_MESSAGE_2_TIME),  # 7 days
                              args=[bot, callback.message])
            # await rq.set_user_flag_2(callback.from_user.id)
            # done at another place - right after the choice in question 2
        else:  # not sending question about the webinar appearance 2nd time
            await add_timer_for_final_offer(bot, callback, 1)

        return

    await add_timer_for_first_offer(bot, callback, order_index + 1)


async def add_timer_for_first_offer(bot: Bot, callback: CallbackQuery, reminder_index):
    delay = await rq.get_first_offer_info(reminder_index)
    delay = delay.delay_time_minutes
    scheduler.add_job(
        send_first_offer_message,
        'date',
        run_date=datetime.now() + timedelta(seconds=delay),
        args=[bot, callback, reminder_index]
    )


async def send_question_2_message(bot: Bot, message: Message) -> None:
    user_id = message.chat.id
    await set_flag_2(user_id)
    await bot.send_message(chat_id=user_id,
                           text=texts.QUESTION_MESSAGE_2,
                           reply_markup=gkb.question_2_keyboard,
                           parse_mode=ParseMode.HTML)

    scheduler.add_job(restart_webinar_messages,
                      run_date=datetime.now() + timedelta(seconds=timings.RESTART_WEBINAR_MESSAGES_TIME),  # 120 minutes
                      args=[message, bot])


async def send_final_offer_message(bot: Bot, callback: CallbackQuery, order_index):
    text = await rq.get_final_offer_text(order_index)
    if text is None:
        print("got None from get_final_offer_text (Must be out of index for final offer messages)")
        return

    message_info = await rq.get_final_offer_info(order_index)

    if message_info.image:
        photo = get_photo_from_database(message_info)
        await send_message_with_photo(bot,
                                      callback.message.chat.id,
                                      photo,
                                      message_info.text,
                                      get_keyboard_from_database(message_info))
    else:
        await bot.send_message(chat_id=callback.message.chat.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )

    if await rq.get_final_offer_text(order_index + 1) is None:
        await rq.set_stage(callback.message.chat.id, app.database.models.UserStage.DONE)
        return

    await add_timer_for_final_offer(bot, callback, order_index + 1)


async def add_timer_for_final_offer(bot: Bot, callback: CallbackQuery, order_index):
    delay = await rq.get_final_offer_info(order_index)
    delay = delay.delay_time_minutes
    scheduler.add_job(
        send_final_offer_message,
        'date',
        run_date=datetime.now() + timedelta(seconds=delay),
        args=[bot, callback, order_index]
    )


def did_webinar_date_come(user_webinar_date: date) -> bool:
    """Check if current Moscow date is AFTER webinar date"""
    return datetime.now(MOSCOW_TZ).date() >= user_webinar_date


def get_keyboard_from_database(row: Any) -> Optional[InlineKeyboardMarkup]:
    """
    Safely converts database row's 'buttons' JSON to InlineKeyboardMarkup.
    Handles:
    - Missing 'buttons' column/attribute
    - None/empty values
    - Invalid JSON structures
    """
    # Check if row has buttons attribute/column
    if not hasattr(row, 'buttons'):
        return None

    buttons_data = row.buttons

    if not buttons_data:
        return None

    if isinstance(buttons_data, str):
        try:
            buttons_data = json.loads(buttons_data)
        except json.JSONDecodeError:
            return None

    if not isinstance(buttons_data, dict):
        return None

    try:
        return InlineKeyboardMarkup(inline_keyboard=buttons_data.get("inline_keyboard", []))
    except (TypeError, ValueError):
        return None


async def send_message_with_photo(bot, chat_id, photo, text, mes_keyboard):
    if len(text) > 1020:
        await bot.send_photo(chat_id=chat_id,
                             photo=photo)
        await bot.send_message(chat_id=chat_id,
                               text=text,
                               reply_markup=mes_keyboard,
                               parse_mode=ParseMode.HTML)
    else:
        await bot.send_photo(chat_id=chat_id,
                             photo=photo,
                             caption=text,
                             reply_markup=mes_keyboard,
                             parse_mode=ParseMode.HTML)


def read_file_as_binary(path: str) -> bytes | None:
    """Reads a PDF file and returns its binary content"""
    try:
        # Convert to absolute path if needed
        full_path = Path(__file__).parent.parent / path
        with open(full_path, "rb") as pdf_file:
            return pdf_file.read()
    except FileNotFoundError:
        print(f"Error: JPG file not found at {full_path}")
        return None
    except Exception as e:
        print(f"Error reading JPG: {e}")
        return None


def get_photo_from_database(row: Any):
    if not row.image:
        return None
    try:
        # Create a file-like object from binary data
        jpg_file = BufferedInputFile(
            file=row.image,
            filename="file.jpg"
        )
    except Exception as e:
        print(f"Failed to send PDF: {e}")
        return None
    return jpg_file
