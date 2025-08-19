import string

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

    broadcast_message : string

    # def all_states(self):
    #     return list(self.__states__.values())

class ChangingSellingMessagesState(StatesGroup):
    waiting_for_new_message = State()
    waiting_for_message_order_choice = State()
    waiting_for_confirmation = State()

    messages : Message
