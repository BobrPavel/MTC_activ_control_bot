from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import orm_get_players, orm_get_status
from kbds.inline import get_callback_btns

from filters.chat_types import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

@admin_router.message(F.text == "Отчёты")
async def admin_reports(message: types.Message):
    await message.answer(
        "Выберите вариант",
        reply_markup=get_callback_btns(
            btns={"Норма": "report_1", "Отпуска": "report_2", "Казнь": "report_3"},
            sizes=(1, 2)
        )
    )

@admin_router.callback_query(F.data.startswith("report_"))
async def report_cmd(callback: types.CallbackQuery, session: AsyncSession):
    try:
        status_id = int(callback.data.removeprefix("report_"))
    except ValueError:
        await callback.message.answer("Неверный формат команды.")
        return
    status = await orm_get_status(session, status_id)
    header = f"📝 Отчёт по личному составу\nСтатус: {status.name}\n\n"
    players = await orm_get_players(session, status_id)
    if not players:
        await callback.message.answer(header + "Нет игроков с этим статусом.")
        return
    players_list = "\n".join(
        f"{p.name} | {p.count} | {p.direction.name}" for p in players
    )
    await callback.message.answer(header + players_list)
