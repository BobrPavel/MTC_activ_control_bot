from aiogram import Router, types
from aiogram.filters import Command
from filters.chat_types import ChatTypeFilter, IsAdmin
from kbds.reply import get_keyboard, del_reply_kd

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB = get_keyboard(
    "Карточки", "Игроки", "Отчёты", "Контроль",
    placeholder="Выберите действие", sizes=(2, 2)
)

@admin_router.message(Command("admin"))
async def admin_on(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)

@admin_router.message(Command("off"))
async def admin_off(message: types.Message):
    await message.answer("Админ клавиатура удалена", reply_markup=del_reply_kd)
