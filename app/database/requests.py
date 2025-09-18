from datetime import timedelta, datetime

from aiogram.types import Message
from sqlalchemy.exc import NoResultFound

import texts
import timings
from app import utils
from app.database.models import *
from sqlalchemy import select, delete
from zoneinfo import ZoneInfo

from texts import MINI_COURSE_LINK, REQUEST_LINK, BODY_UP_LINK, WEBINAR_LINK, QUIZ_LINK, LESSON_1_LINK, \
    LESSON_2_LINK, CHANNEL_LINK

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


async def does_user_exist(tg_id: int) -> bool:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar()
        return user is not None


async def remove_user(tg_id: int) -> bool:
    async with async_session() as session:
        try:
            res = await session.execute(select(User).where(User.tg_id == tg_id))
            user = res.scalar_one_or_none()
            if user:
                await session.delete(user)
                await session.commit()
                print("User deleted successfully")
                return True
            else:
                print("User not found")
                return False

        except Exception as e:
            session.rollback()
            print(f"Error deleting user with tg_id: {tg_id}: {e}")
            return False


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

async def initialize_broadcast_messages():
    async with async_session() as session:
        # Check if any broadcast messages exist
        result = await session.execute(select(LessonMessages))
        if result.scalars().first() is None:
            initial_messages = [
                LessonMessages(
                    text=texts.LESSON_MESSAGE_1,
                    code_name="lesson1",
                    order_of_sending=1, delay_time_minutes=timings.LESSON_MESSAGE_1_AUTO_TIME,
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
                    order_of_sending=2, delay_time_minutes=timings.LESSON_MESSAGE_2_AUTO_TIME,
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
                    order_of_sending=3, delay_time_minutes=timings.LESSON_MESSAGE_3_AUTO_TIME,
                    image=utils.read_file_as_binary(r"assets/images/lesson_3_photo.jpg"),
                    buttons={
                        "inline_keyboard": [
                            [{"text": "12:00", "callback_data": "selected_webinar_time_12:00"}],
                            [{"text": "19:00", "callback_data": "selected_webinar_time_19:00"}]]
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
                                    "inline_keyboard": [[{"text": "Получить гайд",
                                                          "url": QUIZ_LINK}],
                                                        [{"text": "Подписаться на канал",
                                                          "url": CHANNEL_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_2,
                                order_of_sending=2, delay_time_minutes=0,
                                image=utils.read_file_as_binary(r"assets/images/webinar/final_lesson_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Подписаться на канал",
                                                          "url": CHANNEL_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_3,
                                order_of_sending=3, delay_time_minutes=timings.WEBINAR_REMINDER_3_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_4_hours_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Подписаться на канал",
                                                          "url": texts.CHANNEL_LINK}]]
                                }
                                ),

                WebinarMessages(text=texts.WEBINAR_REMINDER_4,
                                order_of_sending=4, delay_time_minutes=timings.WEBINAR_REMINDER_4_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_1_hour_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Подписаться на канал",
                                                          "url": texts.CHANNEL_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_5,
                                order_of_sending=5, delay_time_minutes=timings.WEBINAR_REMINDER_5_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_15_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Занять место",
                                                          "url": texts.WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_6,
                                order_of_sending=6, delay_time_minutes=timings.WEBINAR_REMINDER_6_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_live_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Перейти к мастер классу", "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_7,
                                order_of_sending=7, delay_time_minutes=timings.WEBINAR_REMINDER_7_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_post_15_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_8,
                                order_of_sending=8, delay_time_minutes=timings.WEBINAR_REMINDER_8_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_post_30_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_9,
                                order_of_sending=9, delay_time_minutes=timings.WEBINAR_REMINDER_9_TIME,
                                image=utils.read_file_as_binary(
                                    r"assets/images/webinar/webinar_reminder_post_45_minutes_photo.jpg"),
                                buttons={
                                    "inline_keyboard": [[{"text": "Иду на практикум",
                                                          "url": WEBINAR_LINK}]]
                                }
                                ),
                WebinarMessages(text=texts.WEBINAR_REMINDER_10,
                                order_of_sending=10, delay_time_minutes=timings.WEBINAR_REMINDER_10_TIME,
                                image=None,
                                buttons={
                                    "inline_keyboard": [[{"text": "Оплатить со скидкой",
                                                          "url": BODY_UP_LINK}],
                                                        [{"text": "🎁 Оставить заявку",
                                                          "url": REQUEST_LINK}]]
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
                                   order_of_sending=1, delay_time_minutes=timings.FIRST_OFFER_MESSAGE_1_TIME,  # + кружок
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_1_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Оплатить со скидкой",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "🎁 Оставить заявку",
                                                             "url": REQUEST_LINK}]

                                                           ]
                                   }
                                   ),
                FirstOfferMessages(text=texts.FIRST_OFFER_MESSAGE_2,
                                   order_of_sending=2, delay_time_minutes=timings.FIRST_OFFER_MESSAGE_2_TIME,
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_2_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Оплатить со скидкой",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "🎁 Оставить заявку",
                                                             "url": REQUEST_LINK}]
                                                           ]
                                   }
                                   ),
                FirstOfferMessages(text=texts.FIRST_OFFER_MESSAGE_3,
                                   order_of_sending=3, delay_time_minutes=timings.FIRST_OFFER_MESSAGE_3_TIME,
                                   image=utils.read_file_as_binary(
                                       r"assets/images/first_offer/first_offer_3_photo.jpg"),
                                   buttons={
                                       "inline_keyboard": [[{"text": "Оплатить со скидкой",
                                                             "url": BODY_UP_LINK}],
                                                           [{"text": "🎁 Оставить заявку",
                                                             "url": REQUEST_LINK}]
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
                                   order_of_sending=1, delay_time_minutes=timings.FINAL_OFFER_MESSAGE_1_TIME,
                                   image=None,
                                   buttons={
                                       "inline_keyboard": [
                                           [{"text": "Оплатить со скидкой", "url": BODY_UP_LINK}],
                                           [{"text": "🎁 Оставить заявку", "url": REQUEST_LINK}]]
                                   }
                                   ),
                FinalOfferMessages(text=texts.FINAL_OFFER_MESSAGE_2,
                                   order_of_sending=2, delay_time_minutes=timings.FINAL_OFFER_MESSAGE_2_TIME,
                                   image=None,
                                   buttons={
                                       "inline_keyboard": [
                                           [{"text": "Хочу мини-курс", "url": MINI_COURSE_LINK}],
                                           [{"text": "🎁 Оставить заявку",
                                             "url": REQUEST_LINK}]]
                                   }
                                   )
            ]
            session.add_all(initial_messages)
            await session.commit()
            print("Initial first offer messages created")
        else:
            print("First offer already exist - skipping initialization")


# async def initialize_metrics():
# async with async_session() as session:

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

        user = await session.scalar(select(User).where(User.tg_id == message.chat.id))
        if not user:
            username = message.from_user.username
            if message.from_user.username is None:
                username = message.chat.id
            session.add(User(tg_id=message.chat.id,
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


async def get_all_done_users_ids():
    async with async_session() as session:
        # Had mistake here - took User.id instead of User.tg_id
        result = await session.execute(select(User.tg_id).where(User.cur_stage == UserStage.DONE))
        return result.scalars()


async def set_stage(tg_id: int, stage: UserStage):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            user.cur_stage = stage
            await session.commit()
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found, hence could"
                                f"not set stage \'" + stage.value + "\'")


async def get_stage(tg_id: int) -> UserStage:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user:
            return user.cur_stage
        else:
            raise NoResultFound(f"User with tg_id {tg_id} not found")


async def add_choose_time_himself_metric(tg_id: int):
    async with async_session() as session:
        res = await session.execute(select(UserMetrics).where(UserMetrics.tg_id == tg_id))
        user_metric = res.scalar_one_or_none()
        if user_metric:
            user_metric.did_choose_time_himself = True
            await session.commit()
        else:
            session.add(UserMetrics(tg_id=tg_id, did_choose_time_himself=True))
            await session.commit()


async def add_did_press_lesson_himself_metric(tg_id: int, lesson_index: int):
    async with async_session() as session:
        res = await session.execute(select(UserMetrics).where(UserMetrics.tg_id == tg_id))
        user_metric = res.scalar_one_or_none()
        if user_metric:
            if lesson_index == 1:
                user_metric.did_press_next_lesson_1 = True
            elif lesson_index == 2:
                user_metric.did_press_next_lesson_2 = True
            elif lesson_index == 3:
                user_metric.did_press_next_lesson_3 = True
            await session.commit()
        else:
            if lesson_index == 1:
                session.add(UserMetrics(tg_id=tg_id, did_press_next_lesson_1=True))
            elif lesson_index == 2:
                session.add(UserMetrics(tg_id=tg_id, did_press_next_lesson_2=True))
            elif lesson_index == 3:
                session.add(UserMetrics(tg_id=tg_id, did_press_next_lesson_3=True))

            await session.commit()


async def count_users_who_did_press_lesson_himself_metric(lesson_index: int):
    async with async_session() as session:
        res = 0

        if lesson_index == 1:
            res = await session.execute(select(UserMetrics).where(UserMetrics.did_press_next_lesson_1 == True))

        if lesson_index == 2:
            res = await session.execute(select(UserMetrics).where(UserMetrics.did_press_next_lesson_2 == True))

        if lesson_index == 3:
            res = await session.execute(select(UserMetrics).where(UserMetrics.did_press_next_lesson_3 == True))
        count = (res.scalars().all())
        return len(count)


async def count_users_who_got_flag(flag_index: int):
    async with async_session() as session:
        res = []
        if flag_index == 1:
            res = await session.execute(select(User).where(User.first_flag == True))

        if flag_index == 2:
            res = await session.execute(select(User).where(User.second_flag == True))
        count = (res.scalars().all())
        return len(count)

async def count_users_with_chosen_time(time):
    async with async_session() as session:

        res = await session.execute(select(User).where(User.webinar_time == time))

        count = (res.scalars().all())
        return len(count)