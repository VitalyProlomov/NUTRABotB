from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton)

from config import CHANNEL_NAME

subscription_check_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Подписаться', url=f'https://t.me/{CHANNEL_NAME[1:]}')],
    [InlineKeyboardButton(text='Готово', callback_data='check_subscription')]
])

simple_subscription_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Подписаться', url=f'https://t.me/{CHANNEL_NAME[1:]}')],
])

webinar_time_choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='12:00', callback_data="selected_webinar_time_12:00")],
    [InlineKeyboardButton(text='19:00', callback_data="selected_webinar_time_19:00")]
])

lesson_1_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Перейти к уроку 1', callback_data="next_lesson_1")],
])

mark_purchase_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Уже купил(а)', callback_data='mark_purchase')],
])

channel_link_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Click Me!", url="https://example.com")]
])

webinar_reminder_1_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Пройти тест", url="http://ekaterina-hodianok.ru/quiz")]
    ]
)

question_1_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Да, была", callback_data="chosen_at_1_questionary_yes")],
                     [InlineKeyboardButton(text="Нет, пропустила", callback_data="chosen_at_1_questionary_no")]
                     ]
)

question_2_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Да, была", callback_data="chosen_at_2_questionary_yes")],
                     [InlineKeyboardButton(text="Нет, пропустила", callback_data="chosen_at_2_questionary_no")]
                     ]
)


# def create_selling_message_keyboard(link, button_text):
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=button_text, url=link)],
#         [InlineKeyboardButton(text='Уже купил(а)', callback_data='mark_purchase')],
#     ])
