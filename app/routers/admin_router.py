from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.filters.admin_filter import IsAdminFilter
from app.middlewares import TestMiddleWare

import app.keyboards.admin_keyboards as akb
import app.database.requests as rq
import app.routers.States as States

admin_router = Router()
admin_router.message.middleware(TestMiddleWare())

admin_router.message.filter(IsAdminFilter())

# In this file the handlers that are handling menu commands (specifically from admin
# keyboard) must be defined in the top (before all the functions with the
# states. It ensures, that when admin clicks the button in the menu while being in
# the middle of another multistep task (e.g: broadcasting), current task
# will be aborted and new task will be started (this is done to prevent
# broadcasting 'Изменить исходные дожимающие сообщения' by mistake by admin.
# Same with the cancel function - must be defined before handlers that
# work with states.


@admin_router.message(Command('admin'))
async def admin_panel(message: Message, bot : Bot):
    keyboard = akb.admin_keyboard

    await message.reply("Admin Panel:", reply_markup=keyboard)

# order matters
@admin_router.message(F.text.lower() == "отмена")
async def cancel(message: Message, state : FSMContext):
    if await state.get_state() is not None:
        await state.clear()
        await message.answer("Процедура отменена", reply_markup=akb.admin_keyboard)


@admin_router.message(F.text == "Рассылка Сообщения")
async def initialize_broadcast(message: Message, state: FSMContext):
    # important, set_state() method doesnt clear the prev state
    await state.clear()
    await state.set_state(States.BroadcastState.waiting_for_message)
    reply = await message.reply("Пожалуйста, напишите сообщение, которое вы хотите разослать всем пользователям:\n"
                                " (Или напишите ОТМЕНА для отмены рассылки)")

    await state.set_state(States.BroadcastState.waiting_for_message)

# order matters
# @admin_router.message(F.text == "Изменить исходные дожимающие сообщения")
# async def change_selling_messages_texts(message : Message, state: FSMContext):
#     await state.clear()
#     # current_state = await state.get_state()
#     # if current_state and current_state.split(':')[0] == 'BroadcastState':
#     #     await message.answer("Задача рассылки прервана")
#     #     await state.clear()
#     # elif await state.get_state():
#
#     await message.answer("Выберите номер сообщения, которое вы хотите изменить",
#                          reply_markup=akb.selling_message_options_keyboard)
#     await state.set_state(States.ChangingSellingMessagesState.waiting_for_message_order_choice)


@admin_router.message(States.BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):

    # made it more universal - there is a function in the start for all
    # cancelling now
    # if message.text.lower() == 'отмена':
    #     await state.clear()
    #     await message.answer("Рассылка отменена!")
    #     return
    if message.text == "Подсчет пользователей бота":
        await state.clear()
        await countUsers(message, state)
        return

    await state.update_data(message=message.text)
    States.BroadcastState.broadcast_message = message.text
    await state.set_state(States.BroadcastState.waiting_for_confirmation)

    await message.answer(
        f"Подтверждаем рассылку?\n\nСообщение:\n{message.text}",
        reply_markup=akb.confirmation_keyboard, parse_mode=ParseMode.HTML
    )


@admin_router.message(F.text == "Подтвердить ✅",
                      States.BroadcastState.waiting_for_confirmation)
async def broadcast(message: Message, state: FSMContext, bot : Bot):
    broadcast_message = await state.get_data()
    print(f'{broadcast_message}\n\n')

    await message.answer(f"Рассылаем всем завершившим воронку пользователям сообщение:\n\n{message.text}")
    users = (await rq.get_all_done_users_ids()).all()
    print(f'Users: {users}')
    length = len(users)
    success_am = length

    for user_id in users:
        try :
            # print("member" + States.BroadcastState.broadcast_message)
            # await bot.send_message(chat_id=user_id, text=BroadcastStates.broadcast_message)
            await bot.send_message(chat_id=user_id, text=broadcast_message['message'], parse_mode=ParseMode.HTML)
        except Exception as e:
            success_am -= 1
            print(f'Failed to send message to user {user_id}: {e}')
    await message.answer(f'Рассылка успешно отправлена {success_am} из {length} пользователей',
                         reply_markup=akb.admin_keyboard)
    await state.clear()

@admin_router.message(F.text == "Отмена ❌",
                      States.BroadcastState.waiting_for_confirmation)
async def broadcast(message: Message, state: FSMContext, bot : Bot):
    await message.answer("Рассылка отменена", reply_markup=akb.admin_keyboard)
    await state.clear()

@admin_router.message(F.text == "Подсчет пользователей бота")
async def countUsers(message: Message, state: FSMContext):
    await state.clear()
    users = (await rq.get_all_users_ids()).all()
    await message.answer(f'Всего вашим ботом воспользовались: {len(users)}')



# @admin_router.callback_query(F.data == "selling_message_1_option",
#                              States.ChangingSellingMessagesState.waiting_for_message_order_choice)
# async def process_changing_selling_message_1_option(callback: CallbackQuery, state: FSMContext, bot : Bot):
#     await process_changing_selling_message(option_ind=1, state=state, bot=bot, chat_id=callback.from_user.id)
#
# @admin_router.callback_query(F.data == "selling_message_2_option", States.ChangingSellingMessagesState.waiting_for_message_order_choice)
# async def process_changing_selling_message_2_option(callback :CallbackQuery, state : FSMContext, bot : Bot):
#     await process_changing_selling_message(option_ind=2,state=state, bot=bot, chat_id=callback.from_user.id)
# #
# async def process_changing_selling_message(
#         option_ind : int,
#         bot : Bot,
#         state: FSMContext,
#         chat_id):
#     await bot.send_message(text=f'Напишите сообщение, на которое вы бы хотели заменить текущее {option_ind} дожимающее сообщение\n'
#                            f'Напишите ОТМЕНА для отмены изменений', chat_id=chat_id)
#
#     await state.update_data(option_ind=option_ind)
#     await state.set_state(States.ChangingSellingMessagesState.waiting_for_new_message)
#
#
# @admin_router.message(States.ChangingSellingMessagesState.waiting_for_new_message)
# async def get_new_message(message : Message, state : FSMContext):
#
#     await state.update_data(message=message.text)
#
#     data = await state.get_data()
#     await message.answer(
#         f'Подтвердите изменение {data['option_ind']} дожимающего сообщения на :\n\n{message.text}',
#         reply_markup=akb.confirmation_keyboard
#     )
#     await state.set_state(States.ChangingSellingMessagesState.waiting_for_confirmation)

#
# @admin_router.message(F.text == "Подтвердить ✅",
#                       States.ChangingSellingMessagesState.waiting_for_confirmation)
# async def change_message( message: Message, state: FSMContext, bot : Bot):
#     data = await state.get_data()
#     # try:
#     #TODO ADD delay time from user
#     result = await rq.edit_selling_message(data['option_ind'], data['message'], 8)
#     if result:
#         await message.answer(f'Успешно изменили {data['option_ind']} дожимающее сообщение на:'
#                                    f' \n\n{data["message"]}',
#                                    reply_markup=akb.admin_keyboard)
    # except Exception as e:
    #     print(e)
    #     await message.answer(f'Не удалось изменить дожимающее сообщение, попробуйте снова или обратитесь к программисту для уточнения проблемы. '
    #                          f'Покажите эту ошибку: {e.message}',
    #                          reply_markup=akb.admin_keyboard)
    await state.clear()

@admin_router.message(F.text == "Отмена ❌",
                      States.ChangingSellingMessagesState.waiting_for_confirmation)
async def broadcast(message: Message, state: FSMContext, bot : Bot):
    await message.answer("Изменение отменено", reply_markup=akb.admin_keyboard)
    await state.clear()

