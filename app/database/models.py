from sqlalchemy import BigInteger, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, Enum as SQLEnum
from datetime import date
from sqlalchemy import Date
from enum import Enum

# from sqlalchemy import create_engine
from sqlalchemy import LargeBinary
from sqlalchemy import JSON
from typing import Optional

engine = create_async_engine(url = 'sqlite+aiosqlite:///db.sqlite3')
# engine2 = create_engine(url = 'sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class UserStage(str, Enum):  # ← Inherit from str
    START = "start"
    CHOOSING_TIME = "choosing_time"
    WEBINAR = "webinar"
    FIRST_OFFERS = "first_offers"
    FINAL_OFFERS = "final_offers"
    DONE = "done"

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True) # auto increment is by deafult
    tg_id: Mapped[BigInteger] = mapped_column(BigInteger, unique=True)
    tg_username : Mapped[str] = mapped_column(String(256))
    didMarkPurchase: Mapped[bool] = mapped_column(Boolean, default=False)
    first_flag : Mapped[Boolean] = mapped_column(Boolean, default=False)
    second_flag: Mapped[Boolean] = mapped_column(Boolean, default=False)
    webinar_time: Mapped[str] = mapped_column(String(256), nullable=True, default=None)
    webinar_date: Mapped[date] = mapped_column(Date, nullable=True)
    cur_stage: Mapped[UserStage] = mapped_column(
        SQLEnum(UserStage),
        default=UserStage.START,
        nullable=False
    )

class LessonMessages(Base):
    __tablename__ = 'lesson_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    code_name: Mapped[str] = mapped_column(unique=True, nullable=True)
    text : Mapped[str] = mapped_column(String(3000))
    # 1-based counting (index 1 is the very first message)
    order_of_sending : Mapped[int] = mapped_column(Integer)
    delay_time_minutes : Mapped[BigInteger] = mapped_column(BigInteger, default=10)
    image: Mapped[String] = mapped_column(LargeBinary, nullable=True)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default = None)

class WebinarMessages(Base):
    __tablename__ = 'webinar_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    code_name: Mapped[str] = mapped_column(unique=True, nullable=True, default=None)
    text: Mapped[str] = mapped_column(String(3000))
    # 1-based counting (index 1 is the very first message)
    order_of_sending: Mapped[int] = mapped_column(Integer)
    delay_time_minutes: Mapped[BigInteger] = mapped_column(BigInteger, default=10)
    flag: Mapped[Boolean] = mapped_column(Boolean, default=False)
    image: Mapped[String] = mapped_column(LargeBinary, nullable=True, default=None)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default = None)

class FirstOfferMessages(Base):
    __tablename__ = 'first_offer_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    code_name: Mapped[str] = mapped_column(unique=True, nullable=True)
    text: Mapped[str] = mapped_column(String(3000))
    # 1-based counting (index 1 is the very first message)
    order_of_sending: Mapped[int] = mapped_column(Integer)
    delay_time_minutes: Mapped[BigInteger] = mapped_column(BigInteger, default=10)
    image: Mapped[String] = mapped_column(LargeBinary, nullable=True)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default = None)


class FinalOfferMessages(Base):
    __tablename__ = 'final_offer_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    code_name: Mapped[str] = mapped_column(unique=True, nullable=True)
    text: Mapped[str] = mapped_column(String(3000))
    # 1-based counting (index 1 is the very first message)
    order_of_sending: Mapped[int] = mapped_column(Integer)
    delay_time_minutes: Mapped[BigInteger] = mapped_column(BigInteger, default=10)
    image: Mapped[String] = mapped_column(LargeBinary, nullable=True)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default = None)

class UserMetrics(Base):
    __tablename__ = 'users_metrics'

    id: Mapped[int] = mapped_column(primary_key=True) # auto increment is by deafult
    tg_id: Mapped[BigInteger] = mapped_column(BigInteger, unique=True)
    # tg_username : Mapped[str] = mapped_column(String(256))
    first_flag : Mapped[Boolean] = mapped_column(Boolean, default=False)
    second_flag: Mapped[Boolean] = mapped_column(Boolean, default=False)
    # did_press_lesson_1_link: Mapped[bool] = mapped_column(Boolean, default=False)
    # did_press_lesson_2_link: Mapped[bool] = mapped_column(Boolean, default=False)
    # did_press_lesson_3_link: Mapped[bool] = mapped_column(Boolean, default=False)
    did_choose_time_himself: Mapped[Boolean] = mapped_column(Boolean, default=False)
    did_press_next_lesson_1 : Mapped[Boolean] = mapped_column(Boolean, default=False)
    did_press_next_lesson_2 : Mapped[Boolean] = mapped_column(Boolean, default=False)
    did_press_next_lesson_3 : Mapped[Boolean] = mapped_column(Boolean, default=False)
    # did_click_subscribe : Mapped[Boolean] = mapped_column(Boolean, default=False)
#
# class Item(Base):
#     __tablename__ = 'items'
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     name: Mapped[str] = mapped_column(String(25))
#     description: Mapped[str] = mapped_column(String(500))
#     price: Mapped[int] = mapped_column()
#
#     category: Mapped[int] = mapped_column(ForeignKey('categories.id'))

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)