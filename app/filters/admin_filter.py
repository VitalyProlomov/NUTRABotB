from typing import Optional
from aiogram import types
from aiogram.filters import BaseFilter

import config


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in config.ADMIN_IDS
