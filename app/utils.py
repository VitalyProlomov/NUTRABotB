from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import Message, User, InlineKeyboardMarkup, CallbackQuery, BufferedInputFile, FSInputFile
from datetime import datetime, time, timedelta
import json
from zoneinfo import ZoneInfo

from apscheduler.job import Job
from sqlalchemy.testing import not_in_

import app.database.models
import main
import texts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import app.keyboards.general_keyboards as gkb
import app.database.requests as rq
import timings

# Import logger
from app.logger import bot_logger

scheduler = AsyncIOScheduler()
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

import app.routers.user_router


# # order important due to circular imports - BULLSHIT, try through main
# # also, it is prob not needed in here
# from app.routers.user_router import router1


def log_lesson_message_error(e: Exception):
    red = "\033[91m"
    reset = "\033[0m"
    print(f'\n{red}ERROR{reset} happened while trying to send a lesson message:  + {e}\n')
    bot_logger.error(None, "Sending lesson message", e)


async def check_user_subscription(user_id: int, bot: Bot):
    bot_logger.user_action(user_id, "Checking subscription", f"Channel ID: {config.CHANNEL_ID}")
    member = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=user_id)
    # print(f'member status: {member.status}\n\n\n')

    is_subscribed = member.status in ['member', 'administrator', 'creator']
    bot_logger.user_action(user_id, "Subscription check result",
                           f"Status: {member.status}, Subscribed: {is_subscribed}")
    return is_subscribed


async def add_timer_for_lessons_message(lesson_mes_order: int, message: Message, bot: Bot):
    """
    :param bot: bot
    :param message: message that was sent in the chat
    :param lesson_mes_order: defines which selling message is being scheduled (1 or 2 is available as for 05.05.2025)
    """
    user_id = message.chat.id
    bot_logger.user_action(user_id, "Scheduling lesson message", f"Order: {lesson_mes_order}")

    try:
        lesson_message = await rq.get_lesson_message_info(lesson_mes_order)
        if not lesson_message:  # Optional: Explicitly check if None/empty
            # if there is no lesson message, it means that the number has exceeded the max value of
            # lesson_mes_order => no more lesson messages in database
            bot_logger.debug(f"No lesson message found for order {lesson_mes_order}, switching to webinar reminder")
            await add_timer_for_webinar_time_choice_reminder(bot, message)
            return
    except Exception as e:
        print(f"Error fetching message: {e}")
        bot_logger.error(user_id, "Fetching lesson message info", e)
        return

    # selling_message = await rq.get_lesson_message_info(selling_mes_order)

    delay_seconds = lesson_message.delay_time_seconds  # * 60
    job = add_job_by_delay(send_lesson_message,
                           delay_seconds=delay_seconds,
                           args=[lesson_mes_order, message, bot],
                           user_tg_id=message.chat.id)

    bot_logger.job_scheduled(user_id, f"send_lesson_message_{lesson_mes_order}", str(job.next_run_time),
                             f"Delay: {delay_seconds}s")


# The message is the one, that bot writes, so it is important to use chat_id when sending the selling message,
# NOT the message.chat.id
async def send_lesson_message(lesson_message_order: int, message: Message, bot: Bot):
    user_id = message.chat.id
    bot_logger.job_executed(user_id, f"send_lesson_message_{lesson_message_order}", "started")

    remove_all_user_jobs(message.chat.id)
    try:
        # if not await did_user_mark_purchase(message.chat.id):
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
                    # Need to test before uncommenting and releasing
                    # reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons_data["inline_keyboard"])
                else:  # If already a dict (SQLAlchemy JSON type)
                    buttons_data = lesson_info.buttons

                    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons_data["inline_keyboard"])
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                print(f"Error parsing buttons: {e}")
                bot_logger.error(user_id, "Parsing lesson message buttons", e)
        if lesson_info.image:
            image_file = get_photo_from_database(lesson_info)
            await send_message_with_photo(bot, message.chat.id, image_file, lesson_info.text, reply_markup)
            bot_logger.message_sent(user_id, f"lesson_message_{lesson_message_order}", "with photo")
        if lesson_message_order != 1:
            remove_all_user_jobs(message.chat.id)
            # await message.edit_reply_markup(reply_markup=None)

        await add_timer_for_lessons_message(int(lesson_message_order) + 1, message, bot)
        bot_logger.job_executed(user_id, f"send_lesson_message_{lesson_message_order}", "completed")
    except Exception as e:
        bot_logger.error(user_id, f"Sending lesson message {lesson_message_order}", e)
        bot_logger.job_executed(user_id, f"send_lesson_message_{lesson_message_order}", "failed")
        log_lesson_message_error(e)


async def add_timer_for_webinar_time_choice_reminder(bot: Bot, message):
    user_id = message.chat.id
    delay_seconds = timings.WEBINAR_REMINDER_0_AUTO_TIME  # * 60
    bot_logger.user_action(user_id, "Scheduling webinar time choice reminder", f"Delay: {delay_seconds}s")

    job = add_job_by_delay(send_webinar_time_choice_reminder,
                           delay_seconds=delay_seconds,
                           args=[bot, message],
                           user_tg_id=message.chat.id)

    bot_logger.job_scheduled(user_id, "send_webinar_time_choice_reminder", str(job.next_run_time))


async def send_webinar_time_choice_reminder(bot: Bot, message: Message):
    user_id = message.chat.id
    bot_logger.job_executed(user_id, "send_webinar_time_choice_reminder", "started")

    await bot.send_message(chat_id=message.chat.id,
                           text=texts.WEBINAR_REMINDER_0,
                           reply_markup=gkb.webinar_time_choice_keyboard,
                           parse_mode=ParseMode.HTML)
    bot_logger.message_sent(user_id, "webinar_time_choice_reminder", "sent")

    chat_id: int = message.chat.id

    # Build the callback query
    callback_query = CallbackQuery(
        id=f'{chat_id}-{datetime.now()}',
        from_user=User(id=chat_id,
                       is_bot=False,
                       first_name="Fake_User_Callback",
                       last_name="Scheduled",
                       ),
        chat_instance="simulated_instance",
        data="selected_webinar_time_12:00",
        message=message
    )

    now = datetime.now(MOSCOW_TZ)

    deadline = datetime.combine(
        now.date(),
        time(23, 59),
        tzinfo=MOSCOW_TZ
    )
    if main.TEST_MODE:
        deadline = datetime.now() + timedelta(seconds=10)
    # Schedule the job
    add_job_by_date(
        app.routers.user_router.set_webinar_time_date,
        date_time=deadline,
        args=[callback_query, bot],
        user_tg_id=message.chat.id,
    )
    bot_logger.job_scheduled(user_id, "set_webinar_time_date", str(deadline))
    bot_logger.job_executed(user_id, "send_webinar_time_choice_reminder", "completed")


# Send message to channel
async def send_button_message_to_channel(bot: Bot, text: str):
    bot_logger.debug("Sending message to channel")
    await bot.send_message(
        chat_id=config.CHANNEL_ID,
        text=text,
        reply_markup=gkb.channel_link_keyboard,
        parse_mode=ParseMode.HTML  # Optional: Supports Markdown/HTML formatting
    )
    bot_logger.message_sent("CHANNEL", "channel_message", "sent")


async def add_subscription_reminder(bot: Bot, message):
    user_id = message.chat.id
    delay_seconds = timings.SUBSCRIPTION_REMINDER_1_TIME  # * 60
    bot_logger.user_action(user_id, "Scheduling subscription reminder", f"Delay: {delay_seconds}s")

    job = add_job_by_delay(send_subscription_reminder,
                           delay_seconds=delay_seconds,
                           args=(bot, 1, message),
                           user_tg_id=message.chat.id)
    bot_logger.job_scheduled(user_id, "send_subscription_reminder_1", str(job.next_run_time))


async def send_subscription_reminder(bot: Bot, index: int, message: Message):
    user_id = message.chat.id
    bot_logger.job_executed(user_id, f"send_subscription_reminder_{index}", "started")

    if index == 1:
        await bot.send_message(chat_id=message.chat.id, text=texts.SUBSCRIPTION_REMINDER_1,
                               reply_markup=gkb.lesson_1_keyboard,
                               parse_mode=ParseMode.HTML)
        delay_seconds = timings.SUBSCRIPTION_REMINDER_2_TIME  # * 60
        add_job_by_delay(send_subscription_reminder,
                         delay_seconds=delay_seconds,
                         args=(bot, 2, message),
                         user_tg_id=message.chat.id)
        bot_logger.message_sent(user_id, "subscription_reminder_1", "sent")
        bot_logger.job_executed(user_id, "send_subscription_reminder_1", "completed")
        return
    if index == 2:
        await bot.send_message(chat_id=message.chat.id, text=texts.SUBSCRIPTION_REMINDER_2,
                               reply_markup=gkb.lesson_1_keyboard,
                               parse_mode=ParseMode.HTML)
        delay_seconds = await rq.get_lesson_message_info(1)
        delay_seconds = delay_seconds.delay_time_seconds  # * 60
        add_job_by_delay(send_lesson_message,
                         delay_seconds=delay_seconds,
                         args=(1, message, bot),
                         user_tg_id=message.chat.id)
        bot_logger.message_sent(user_id, "subscription_reminder_2", "sent")
        bot_logger.job_executed(user_id, "send_subscription_reminder_2", "completed")


async def add_timer_for_webinar_reminders(bot: Bot, callback: CallbackQuery, reminder_index: int):
    user_id = callback.from_user.id
    bot_logger.user_action(user_id, "Scheduling webinar reminder", f"Index: {reminder_index}")

    now = datetime.now(MOSCOW_TZ)

    # set the date of message for tomorrow
    if reminder_index == 2:
        time_chosen = await rq.get_user_webinar_time(callback.from_user.id)
        if time_chosen is None:
            time_chosen = "12:00"

        start_time = datetime.combine(
            now.date() + timedelta(days=1),  # Next day
            time(hour=6, minute=0),  # At 06:00
            tzinfo=MOSCOW_TZ
        )

        if time_chosen == "19:00":  # TO DO CHANGE to hours
            start_time = datetime.combine(
                now.date() + timedelta(days=1),  # Next day
                time(hour=19 - 6, minute=0),  # At 13:00 - 6 hours before the webinar
                tzinfo=MOSCOW_TZ
            )

        # This must necessarily be after 12:00 and 19:00 initialization cases
        if main.TEST_MODE:
            start_time = datetime.now() + timedelta(seconds=10)

        remove_all_user_jobs(user_id)
        bot_logger.job_executed(user_id=user_id, job_name="remove_all_user_jobs")

        job = add_job_by_date(
            send_webinar_reminder,
            date_time=start_time,
            args=[bot, callback, reminder_index],
            user_tg_id=callback.from_user.id
            # id=f"nextday9am_{chat_id}_{tomorrow_9am.timestamp()}"
        )
        bot_logger.job_scheduled(user_id, f"send_webinar_reminder_{reminder_index}", str(job.next_run_time))
    else:
        delay = await rq.get_webinar_reminder_info(reminder_index)
        delay_seconds = delay.delay_time_seconds  # * 60
        job = add_job_by_delay(
            send_webinar_reminder,
            delay_seconds=delay_seconds,
            args=[bot, callback, reminder_index],
            user_tg_id=callback.from_user.id
        )
        bot_logger.job_scheduled(user_id, f"send_webinar_reminder_{reminder_index}", str(job.next_run_time))


async def send_webinar_reminder(bot: Bot, callback: CallbackQuery, reminder_index: int):
    user_id = callback.from_user.id
    bot_logger.job_executed(user_id, f"send_webinar_reminder_{reminder_index}", "started")

    remove_all_user_jobs(user_id)
    bot_logger.job_executed(user_id=user_id, job_name="remove_all_user_jobs")

    text = await rq.get_webinar_reminder_text(reminder_index)
    if text is None:
        print("got None from get_webinar_reminder (Must be out of index for webinar messages)")
        bot_logger.warning(user_id, "Webinar reminder text not found", f"Index: {reminder_index}")
        return
    webinar_time = await rq.get_user_webinar_time(callback.from_user.id)
    text = text.format(webinar_time)
    message_info = await rq.get_webinar_reminder_info(reminder_index)
    image_file = get_photo_from_database(message_info)

    if reminder_index == 10:
        await bot.send_video_note(callback.from_user.id,
                                  video_note=FSInputFile("assets/videos/webinar_video_note.mp4"))
        bot_logger.message_sent(user_id, "webinar_video_note", "sent")
    if message_info.image:
        await send_message_with_photo(bot=bot,
                                      chat_id=callback.from_user.id,
                                      photo=image_file,
                                      text=text,
                                      mes_keyboard=get_keyboard_from_database(message_info))
        bot_logger.message_sent(user_id, f"webinar_reminder_{reminder_index}", "with photo")
    else:
        await bot.send_message(chat_id=callback.from_user.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )
        bot_logger.message_sent(user_id, f"webinar_reminder_{reminder_index}", "text only")

    if await rq.get_webinar_reminder_text(reminder_index + 1) is None:
        if not await rq.get_user_flag_1(callback.from_user.id):
            delay_seconds = timings.QUESTION_MESSAGE_1_TIME  # * 60
            add_job_by_delay(send_question_1_message,
                             delay_seconds=delay_seconds,  # 10 minutes
                             args=[bot, callback.message],
                             user_tg_id=callback.from_user.id
                             )
            bot_logger.job_scheduled(user_id, "send_question_1_message", f"Delay: {delay_seconds}s")
        else:  # not sending question about the webinar appearance 2nd time
            await add_timer_for_first_offer(bot, callback, 1)

        bot_logger.job_executed(user_id, f"send_webinar_reminder_{reminder_index}", "completed")
        return

    await add_timer_for_webinar_reminders(bot, callback, reminder_index + 1)
    bot_logger.job_executed(user_id, f"send_webinar_reminder_{reminder_index}", "completed")


async def set_flag_1(user_id: int):
    await rq.set_user_flag_1(user_id)
    bot_logger.database_operation(user_id, "set_flag_1", "User flag 1 set")


async def set_flag_2(user_id: int):
    await rq.set_user_flag_2(user_id)
    bot_logger.database_operation(user_id, "set_flag_2", "User flag 2 set")


async def send_question_1_message(bot: Bot, message: Message):
    user_id = message.chat.id
    bot_logger.job_executed(user_id, "send_question_1_message", "started")

    await set_flag_1(user_id)
    await bot.send_photo(chat_id=user_id,
                         photo=FSInputFile(r"assets/images/question_1_photo.jpg"),
                         caption=texts.QUESTION_MESSAGE_1,
                         reply_markup=gkb.question_1_keyboard,
                         parse_mode=ParseMode.HTML)
    bot_logger.message_sent(user_id, "question_1_message", "sent")

    delay_seconds = timings.RESTART_WEBINAR_MESSAGES_TIME  # * 60
    add_job_by_delay(restart_webinar_messages,
                     delay_seconds=delay_seconds,
                     args=[message, bot],
                     user_tg_id=message.chat.id)
    bot_logger.job_scheduled(user_id, "restart_webinar_messages", f"Delay: {delay_seconds}s")
    bot_logger.job_executed(user_id, "send_question_1_message", "completed")


async def restart_webinar_messages(message: Message, bot: Bot):
    user_id = message.chat.id
    bot_logger.job_executed(user_id, "restart_webinar_messages", "started")

    remove_all_user_jobs(message.chat.id)

    # I am setting it in send_question_1_message
    # await set_flag_1(callback.from_user.id)
    # Re-expires the buttons, also needed for setting 19:00 by default (if user doesn't choose anything)
    await rq.reset_webinar_date_time(user_id)
    await app.utils.send_lesson_message(3, message=message, bot=bot)
    bot_logger.job_executed(user_id, "restart_webinar_messages", "completed")


async def send_first_offer_message(bot: Bot, callback: CallbackQuery, order_index):
    user_id = callback.from_user.id
    bot_logger.job_executed(user_id, f"send_first_offer_message_{order_index}", "started")

    text = await rq.get_first_offer_text(order_index)
    if text is None:
        print("got None from get_first_offer_text (Must be out of index for first offer messages)")
        bot_logger.warning(user_id, "First offer text not found", f"Index: {order_index}")
        return

    message_info = await rq.get_first_offer_info(order_index)

    if order_index == 1:
        await bot.send_video_note(callback.from_user.id,
                                  video_note=FSInputFile("assets/videos/tamara_video_note.mp4"))
    if message_info.image:
        photo = get_photo_from_database(message_info)
        await send_message_with_photo(bot,
                                      callback.from_user.id,
                                      photo,
                                      message_info.text,
                                      get_keyboard_from_database(message_info))
        bot_logger.message_sent(user_id, f"first_offer_{order_index}", "with photo")
    else:
        await bot.send_message(chat_id=callback.from_user.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )
        bot_logger.message_sent(user_id, f"first_offer_{order_index}", "text only")

    if await rq.get_first_offer_text(order_index + 1) is None:
        if not await rq.get_user_flag_2(callback.from_user.id):
            delay_seconds = timings.QUESTION_MESSAGE_2_TIME  # * 60
            add_job_by_delay(send_question_2_message,
                             delay_seconds=delay_seconds,  # 7 days
                             args=[bot, callback.message],
                             user_tg_id=callback.from_user.id)
            bot_logger.job_scheduled(user_id, "send_question_2_message", f"Delay: {delay_seconds}s")
            # await rq.set_user_flag_2(callback.from_user.id)
            # done at another place - right after the choice in question 2
        else:  # not sending question about the webinar appearance 2nd time
            await add_timer_for_final_offer(bot, callback, 1)

        bot_logger.job_executed(user_id, f"send_first_offer_message_{order_index}", "completed")
        return

    await add_timer_for_first_offer(bot, callback, order_index + 1)
    bot_logger.job_executed(user_id, f"send_first_offer_message_{order_index}", "completed")


async def add_timer_for_first_offer(bot: Bot, callback: CallbackQuery, reminder_index):
    user_id = callback.from_user.id
    delay = await rq.get_first_offer_info(reminder_index)
    delay_seconds = delay.delay_time_seconds  # * 60
    job = add_job_by_delay(
        send_first_offer_message,
        delay_seconds=delay_seconds,
        args=[bot, callback, reminder_index],
        user_tg_id=callback.from_user.id
    )
    bot_logger.job_scheduled(user_id, f"send_first_offer_message_{reminder_index}", str(job.next_run_time))


async def send_question_2_message(bot: Bot, message: Message) -> None:
    user_id = message.chat.id
    bot_logger.job_executed(user_id, "send_question_2_message", "started")

    await set_flag_2(user_id)
    await bot.send_message(chat_id=user_id,
                           text=texts.QUESTION_MESSAGE_2,
                           reply_markup=gkb.question_2_keyboard,
                           parse_mode=ParseMode.HTML)
    bot_logger.message_sent(user_id, "question_2_message", "sent")

    delay_seconds = timings.RESTART_WEBINAR_MESSAGES_TIME  # * 60
    add_job_by_delay(restart_webinar_messages,
                     delay_seconds=delay_seconds,
                     args=[message, bot],
                     user_tg_id=message.chat.id)
    bot_logger.job_scheduled(user_id, "restart_webinar_messages", f"Delay: {delay_seconds}s")
    bot_logger.job_executed(user_id, "send_question_2_message", "completed")


async def send_final_offer_message(bot: Bot, callback: CallbackQuery, order_index):
    user_id = callback.from_user.id
    bot_logger.job_executed(user_id, f"send_final_offer_message_{order_index}", "started")

    text = await rq.get_final_offer_text(order_index)
    if text is None:
        print("got None from get_final_offer_text (Must be out of index for final offer messages)")
        bot_logger.warning(user_id, "Final offer text not found", f"Index: {order_index}")
        return

    message_info = await rq.get_final_offer_info(order_index)

    if message_info.image:
        photo = get_photo_from_database(message_info)
        await send_message_with_photo(bot,
                                      callback.from_user.id,
                                      photo,
                                      message_info.text,
                                      get_keyboard_from_database(message_info))
        bot_logger.message_sent(user_id, f"final_offer_{order_index}", "with photo")
    else:
        await bot.send_message(chat_id=callback.from_user.id,
                               text=text,
                               reply_markup=get_keyboard_from_database(message_info),
                               parse_mode=ParseMode.HTML
                               )
        bot_logger.message_sent(user_id, f"final_offer_{order_index}", "text only")

    if await rq.get_final_offer_text(order_index + 1) is None:
        await rq.set_stage(callback.from_user.id, app.database.models.UserStage.DONE)
        bot_logger.database_operation(user_id, "set_stage", "User stage set to DONE")
        bot_logger.job_executed(user_id, f"send_final_offer_message_{order_index}", "completed")
        return

    await add_timer_for_final_offer(bot, callback, order_index + 1)
    bot_logger.job_executed(user_id, f"send_final_offer_message_{order_index}", "completed")


async def add_timer_for_final_offer(bot: Bot, callback: CallbackQuery, order_index):
    user_id = callback.from_user.id
    delay = await rq.get_final_offer_info(order_index)
    delay_seconds = delay.delay_time_seconds  # * 60

    job = add_job_by_delay(
        send_final_offer_message,
        delay_seconds=delay_seconds,
        args=[bot, callback, order_index],
        user_tg_id=callback.from_user.id
    )
    bot_logger.job_scheduled(user_id, f"send_final_offer_message_{order_index}", str(job.next_run_time))


# def did_webinar_date_come(user_webinar_date: date) -> bool:
#     """Check if current Moscow date is AFTER webinar date"""
#     return datetime.now(MOSCOW_TZ).date() >= user_webinar_date


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
            bot_logger.error(None, "Parsing keyboard JSON", json.JSONDecodeError("Invalid JSON"))
            return None

    if not isinstance(buttons_data, dict):
        return None

    try:
        return InlineKeyboardMarkup(inline_keyboard=buttons_data.get("inline_keyboard", []))
    except (TypeError, ValueError) as e:
        bot_logger.error(None, "Creating inline keyboard", e)
        return None


async def send_message_with_photo(bot, chat_id, photo, text, mes_keyboard):
    try:
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
    except Exception as e:
        bot_logger.error(chat_id, "Sending message with photo", e)


def read_file_as_binary(path: str) -> bytes | None:
    """Reads a PDF file and returns its binary content"""
    full_path = "cures_path_not_found_vp"
    try:
        # Convert to absolute path if needed
        full_path = Path(__file__).parent.parent / path
        with open(full_path, "rb") as pdf_file:
            return pdf_file.read()
    except FileNotFoundError:
        print(f"Error: JPG file not found at {full_path}")
        bot_logger.error(None, f"File not found: {full_path}", FileNotFoundError(f"File not found: {full_path}"))
        return None
    except Exception as e:
        print(f"Error reading JPG: {e}")
        bot_logger.error(None, f"Reading file: {path}", e)
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
        bot_logger.error(None, "Creating photo from database", e)
        return None
    return jpg_file


def add_job_by_delay(func: Any, delay_seconds: int, args: list | tuple, user_tg_id: int) -> Job:
    """
    Adds a job to scheduler and creates an id correlated to the user telegram id
    :param func: function that will be called
    :param delay_seconds: delay of the trigger in seconds
    :param args: arguments needed for the chosen function
    :param user_tg_id: telegram id of a user, who initiated the task
    :return: Job
    """
    # print ( f'{func.__name__}|{datetime.now().strftime('%d-%m-%Y_%H:%M:%S')}|{user_tg_id}')
    # remove_all_user_jobs(user_tg_id)
    job_id = f"{func.__name__}|{datetime.now().strftime('%d-%m-%Y_%H:%M:%S')}|{user_tg_id}"
    bot_logger.debug(f"Adding delayed job: {job_id} for user {user_tg_id}")

    return scheduler.add_job(func=func,
                             trigger='date',
                             next_run_time=datetime.now() + timedelta(seconds=delay_seconds),
                             args=args,
                             id=job_id,
                             replace_existing=True)


def add_job_by_date(func: Any, date_time: datetime, args: list | tuple, user_tg_id: int) -> Job:
    """
      Adds a job to scheduler and creates an id correlated to the user telegram id
      :param func: function that will be called
      :param date_time: date and time of executing the task
      :param args: arguments needed for the chosen function
      :param user_tg_id: telegram id of a user, who initiated the task
      :return: Job
      """
    # remove_all_user_jobs(user_tg_id)
    job_id = f"{func.__name__}|{datetime.now().strftime('%d-%m-%Y_%H:%M:%S')}|{user_tg_id}"
    bot_logger.debug(f"Adding dated job: {job_id} for user {user_tg_id}")

    return scheduler.add_job(func=func,
                             trigger='date',
                             next_run_time=date_time,
                             args=args,
                             id=job_id,
                             replace_existing=True)


def remove_all_user_jobs(tg_id: int):
    """
    Remove all jobs for a specific user
    :param tg_id: telegram id o the user whose jobs need to be removed
    """
    jobs_to_remove = []

    for job in scheduler.get_jobs():
        if job.id and str(tg_id) in job.id:
            jobs_to_remove.append(job.id)

    if jobs_to_remove:
        bot_logger.debug(f"Removing {len(jobs_to_remove)} jobs for user {tg_id}")
        for job_id in jobs_to_remove:
            scheduler.remove_job(job_id)
            bot_logger.debug(f"Removed job: {job_id}")
    else:
        bot_logger.debug(f"No jobs found to remove for user {tg_id}")


def remove_job(job_id):
    try:
        scheduler.remove_job(job_id=job_id)
        bot_logger.debug(f"Removed specific job: {job_id}")
    except Exception as e:
        bot_logger.error(None, f"Removing job {job_id}", e)



async def emergency_scheduler_restart(bot: Bot):
    """
    Function to start the scheduler of webinar reminder for all not done users when the bot is restarted
    :return:
    """
    reminder_index = 2

    not_done_users_id = await rq.get_all_not_done_users_ids()

    now = datetime.now()
    for done_id in not_done_users_id:
        try:
            callback = CallbackQuery(
                id=f'{done_id}-{datetime.now()}',
                from_user=User(id=done_id,
                               is_bot=False,
                               first_name="Fake_User_Callback",
                               last_name="Scheduled",
                               ),
                chat_instance="simulated_instance",
                data="selected_webinar_time_12:00"
            )
            time_chosen = await rq.get_user_webinar_time(done_id)
            if time_chosen is None:
                time_chosen = "12:00"

            start_time = datetime.combine(
                # TODO
                now.date(), # THIS DAY
                time(hour=6, minute=0),  # At 06:00
                tzinfo=MOSCOW_TZ
            )

            if time_chosen == "19:00":
                start_time = datetime.combine(
                    now.date(),  # THIS DAY
                    time(hour=19 - 6, minute=0),  # At 13:00 - 6 hours before the webinar
                    tzinfo=MOSCOW_TZ
                )
            job = add_job_by_date(
                send_webinar_reminder,
                date_time=start_time,
                args=[bot, callback, reminder_index],
                user_tg_id=callback.from_user.id
                # done_id=f"nextday9am_{chat_id}_{tomorrow_9am.timestamp()}"
            )
            bot_logger.job_scheduled(done_id, f"send_webinar_reminder_{reminder_index}", str(job.next_run_time))
        except Exception as ex:
            bot_logger.error(user_id= done_id, context="emergency startup", error= ex)



