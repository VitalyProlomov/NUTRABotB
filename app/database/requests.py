import json
import string
from datetime import timedelta

from aiogram.types import Message, InputFile, BufferedInputFile
from sqlalchemy.exc import NoResultFound
from io import BytesIO

import app.keyboards.general_keyboards as gkb
import texts
from app import utils
from app.database.models import *
from sqlalchemy import select, delete, literal
from zoneinfo import ZoneInfo

from texts import MINI_COURSE_LINK, CARE_CENTER_LINK, BODY_UP_LINK, WEBINAR_LINK, QUIZ_LINK, LESSON_1_LINK, \
    LESSON_2_LINK

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


async def deleteTHIS():
    async with async_session() as session:
        # res = await session.execute(select(User).where(User.tg_id == 580800721))
        #
        # user = res.scalars().all()
        # if user is not None:

        await session.execute(delete(User).where(User.tg_username == "diplocry"))

        await session.commit()


async def did_user_mark_purchase(tg_id) -> bool:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id and User.didMarkPurchase))
        user = res.scalar()
        if user is None:
            return False
        return user.didMarkPurchase


async def get_all_users_ids():
    async with async_session() as session:
        # Had mistake here - took User.id instead of User.tg_id
        result = await session.execute(select(User.tg_id))
        return result.scalars()


async def change_webinar_time(time, tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            user.webinar_time = time
            await session.commit()


async def set_webinar_date_as_next_day(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()

        if user:
            user.webinar_date = (datetime.now(MOSCOW_TZ) + timedelta(days=1)).date()
            await session.commit()
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def get_user_webinar_time(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user.webinar_time
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def reset_webinar_date_time(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()

        if user:
            user.webinar_date = None
            user.webinar_time = None
            await session.commit()
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def get_user_webinar_date(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user.webinar_date
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def get_user_flag_1(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user.first_flag
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def set_user_flag_1(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            user.first_flag = True
            await session.commit()
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")
        return


async def get_user_flag_2(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user.second_flag

        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def set_user_flag_2(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            user.second_flag = True
            await session.commit()
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")
        return


async def mark_purchase(tg_id):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            user.didMarkPurchase = True
            await session.commit()


async def get_selling_message_text(selling_message_order: int):
    async with (async_session() as session):
        res = await session.execute(
            select(LessonMessages).
            where(LessonMessages.order_of_sending == selling_message_order)
        )

        res = res.scalar_one_or_none()
        return res.text


async def get_lesson_message_info(selling_message_order: int):
    async with (async_session() as session):
        res = await session.execute(
            select(LessonMessages).
            where(LessonMessages.order_of_sending == selling_message_order)
        )

        res = res.scalar_one_or_none()
        return res


async def edit_selling_message(selling_message_order: int, new_text: string,
                               delay_time_minutes: int):
    '''
    :param selling_message_order:
    :param new_text:
    :return: true if editing was successful, false - otherwise (example: didn`t find broadcast message with given selling_message_order)
    '''
    async with async_session() as session:
        res = await session.execute(
            select(LessonMessages).
            where(LessonMessages.order_of_sending == selling_message_order)
        )
        res = res.scalar_one_or_none()
        if res:
            res.text = new_text
            res.delay_time_minutes = delay_time_minutes
            await session.commit()
            return True
        else:
            return False


# Add this to your existing models.py file (or create a new file for initialization)

async def initialize_broadcast_messages():
    async with async_session() as session:
        # Check if any broadcast messages exist
        result = await session.execute(select(LessonMessages))
        if result.scalars().first() is None:
            initial_messages = [
                LessonMessages(
                    text=texts.LESSON_MESSAGE_1,
                    code_name="lesson1",
                    order_of_sending=1, delay_time_minutes=5,
                    image=utils.read_file_as_binary(r"assets/images/lesson_1_photo.jpg"),
                    buttons={
                        "inline_keyboard": [
                            [{"text": "Смотреть урок 1", "url": LESSON_1_LINK}],
                            [{"text": "Перейти к уроку 2", "callback_data": "next_lesson_2"}]
                        ]
                    },

                ),
                LessonMessages(
                    text=texts.LESSON_MESSAGE_2,
                    code_name="lesson2",
                    order_of_sending=2, delay_time_minutes=5,
                    image=utils.read_file_as_binary(r"assets/images/lesson_2_photo.jpg"),
                    buttons={
                        "inline_keyboard": [
                            [{"text": "Смотреть урок 2", "url": LESSON_2_LINK}],
                            [{"text": "Перейти к уроку 3", "callback_data": "next_lesson_3"}]
                        ]
                    }
                ),
                LessonMessages(
                    text=texts.LESSON_MESSAGE_3,
                    code_name="lesson3",
                    order_of_sending=3, delay_time_minutes=5,
                    image=utils.read_file_as_binary(r"assets/images/lesson_3_photo.jpg"),
                    buttons={
                        "inline_keyboard": [
                            [{"text": "12:00", "callback_data": "selected_webinar_time_12:00"}],
                             [{"text": "19:00", "callback_data": "selected_webinar_time_19:00"}]                        ]
                    }
                ),
            ]
            session.add_all(initial_messages)
            await session.commit()
            print("Initial broadcast messages created")
        else:
            print("Broadcast messages already exist - skipping initialization")


async def initialize_webinar_messages():
    async with async_session() as session:
        # Check if any broadcast messages exist
        result = await session.execute(select(WebinarMessages))

        if result.scalars().first() is None:
            initial_messages = [
                WebinarMessages(text=texts.WEBINAR_REMINDER_1,
                                order_of_sending=1, delay_time_minutes=0,
                                buttons={
                                    "inline_keyboard": [[{"text": "Пройти тест", "url": QUIZ_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_2,
                                order_of_sending=2, delay_time_minutes=0,
                                image=utils.read_file_as_binary(r"assets/images/webinar/final_lesson_photo.jpg")
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_3,
                                order_of_sending=3, delay_time_minutes=1,  # 180
                                image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_4_hours_photo.jpg")),
                WebinarMessages(text=texts.WEBINAR_REMINDER_4,
                                order_of_sending=4, delay_time_minutes=1,  # 45
                                image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_1_hour_photo.jpg")
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_5,
                                  order_of_sending=5, delay_time_minutes=1,  # 15
                                  image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_15_minutes_photo.jpg"),
                                  buttons={
                                      "inline_keyboard": [[{"text": "Занять место",
                                                            "url": "https://google.com"}]]
                                  }
                                  ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_6,
                                order_of_sending=6, delay_time_minutes=1,  # 30
                                image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_live_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Перейти к мастер классу", "url": "https://google.com"}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_7,
                                order_of_sending=7, delay_time_minutes=1,  # 15
                                image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_post_15_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_8,
                                order_of_sending=8, delay_time_minutes=3,  # 15
                                image=utils.read_file_as_binary(r"assets/images/webinar/webinar_reminder_post_45_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_9,
                                order_of_sending=9, delay_time_minutes=2,  # 120
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_post_1_hour_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_10,
                                order_of_sending=10, delay_time_minutes=5,  # 22 * 60
                                image= None,
                                buttons={
                                    "inline_keyboard": [[{"text": "Хочу в Body Up",
                                                          "url": BODY_UP_LINK}],
                                                        [{"text": "Написать в службу заботы",
                                                          "url": CARE_CENTER_LINK}]

                                                        ]
                                }
                                )

            ]
            session.add_all(initial_messages)
            await session.commit()
            print("Initial webinar messages created")
        else:
            print("Webinar messages already exist - skipping initialization")


async def initialize_first_offer_messages():
    async with async_session() as session:
        # Check if any broadcast messages exist
        result = await session.execute(select(FirstOfferMessages))

        if result.scalars().first() is None:
            initial_messages = [
                FirstOfferMessages(text=texts.FIRST_OFFER_MESSAGE_1,
                                   order_of_sending=1, delay_time_minutes=0,  # 0 + кружок
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_1_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Хочу в Body Up",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "Написать в службу заботы",
                                                             "url": CARE_CENTER_LINK}]

                                                           ]
                                   }
                                   ),
                FirstOfferMessages(text=texts.FIRST_OFFER_MESSAGE_2,
                                   order_of_sending=2, delay_time_minutes=5,  # 26 * 60
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_2_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Хочу в Body Up",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "Написать в службу заботы",
                                                             "url": CARE_CENTER_LINK}]
                                                           ]
                                   }
                                   ),
                FirstOfferMessages(text=texts.FIRST_OFFER_MESSAGE_3,
                                   order_of_sending=3, delay_time_minutes=4,  # 24 * 60
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_3_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Хочу в Body Up",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "Написать в службу заботы",
                                                             "url": CARE_CENTER_LINK}]
                                                           ]
                                   }
                                   ),
            ]
            session.add_all(initial_messages)
            await session.commit()
            print("Initial final offer messages created")
        else:
            print("Final offer messages already exist - skipping initialization")


async def initialize_final_offer_messages():
    async with async_session() as session:
        # Check if any broadcast messages exist
        result = await session.execute(select(FinalOfferMessages))

        if result.scalars().first() is None:
            initial_messages = [
                FinalOfferMessages(text=texts.FINAL_OFFER_MESSAGE_1,
                                   order_of_sending=1, delay_time_minutes=0,  # 0
                                   image=None,
                                   buttons={
                                       "inline_keyboard": [
                                           [{"text": "Хочу в Body Up", "url": BODY_UP_LINK}],
                                           [{"text": "Написать в службу заботы", "url": CARE_CENTER_LINK}]]
                                   }
                                   ),
                FinalOfferMessages(text=texts.FINAL_OFFER_MESSAGE_2,
                                   order_of_sending=2, delay_time_minutes=6,  # 180
                                   image=None,
                                   buttons={
                                       "inline_keyboard": [
                                           [{"text": "Хочу мини-курс", "url": MINI_COURSE_LINK}],
                                           [{"text": "Написать в службу заботы",
                                             "url": CARE_CENTER_LINK}]]
                                   }
                                   )
            ]
            session.add_all(initial_messages)
            await session.commit()
            print("Initial first offer messages created")
        else:
            print("First offer already exist - skipping initialization")


# async def add_purchase(tg_id):
#     async with async_session() as session:
#         res = await session.execute(select(User).where(User.tg_id == tg_id))
#         user = res.scalar_one_or_none()
#         print(f'{user}\n\n\n')
#         if user:
#             user.didPurchase = True
#             # print("User purchased\n\n")
#             await session.commit()
#             # print(user.didPurchase)

async def set_user(message: Message):
    async with async_session() as session:

        user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
        if not user:
            username = message.from_user.username
            if message.from_user.username is None:
                username = message.from_user.id
            session.add(User(tg_id=message.from_user.id,
                             tg_username=username,
                             didMarkPurchase=False))
            await session.commit()


async def get_webinar_reminder_text(message_order):
    async with async_session() as session:
        reminder = await session.scalar(select(WebinarMessages).
                                        where(WebinarMessages.order_of_sending == message_order))
        if reminder is None:
            return None
        else:
            return reminder.text


async def get_webinar_reminder_info(message_order):
    async with (async_session() as session):
        res = await session.execute(
            select(WebinarMessages).
            where(WebinarMessages.order_of_sending == message_order)
        )

        res = res.scalar_one_or_none()
        return res


async def get_first_offer_info(message_order):
    async with (async_session() as session):
        res = await session.execute(
            select(FirstOfferMessages).
            where(FirstOfferMessages.order_of_sending == message_order)
        )

        res = res.scalar_one_or_none()
        return res


async def get_first_offer_text(message_order):
    async with async_session() as session:
        reminder = await session.scalar(select(FirstOfferMessages).
                                        where(FirstOfferMessages.order_of_sending == message_order))
        if reminder is None:
            return None
        else:
            return reminder.text


async def get_final_offer_info(message_order):
    async with (async_session() as session):
        res = await session.execute(
            select(FinalOfferMessages).
            where(FinalOfferMessages.order_of_sending == message_order)
        )

        res = res.scalar_one_or_none()
        return res


async def get_final_offer_text(message_order):
    async with async_session() as session:
        reminder = await session.scalar(select(FinalOfferMessages).
                                        where(FinalOfferMessages.order_of_sending == message_order))
        if reminder is None:
            return None
        else:
            return reminder.text
