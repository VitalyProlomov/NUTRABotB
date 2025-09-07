from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)

admin_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Рассылка Сообщения")],
    [KeyboardButton(text="Подсчет пользователей бота")],
    [KeyboardButton(text="Метрики")],
    # [KeyboardButton(text="Изменить исходные дожимающие сообщения")],
], resize_keyboard=True)

confirmation_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Подтвердить ✅")],
    [KeyboardButton(text="Отмена ❌")],
])

selling_message_options_keyboard = InlineKeyboardMarkup(
    inline_keyboard = [
        [InlineKeyboardButton(text="1", callback_data="selling_message_1_option"),
        InlineKeyboardButton(text="2", callback_data="selling_message_2_option")]
    ]
)



