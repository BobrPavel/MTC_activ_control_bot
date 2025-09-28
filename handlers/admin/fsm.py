from aiogram import Router, types, F
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_card,
    orm_add_player,
    orm_change_player,
    orm_update_card,
)
from states.admin_states import AddCard, AddUser
from kbds.reply import get_keyboard

from filters.chat_types import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard("Карточки", "Игроки", "Отчёты", "Контроль", sizes=(2, 2))



@admin_router.message(StateFilter("*"), F.text.casefold().in_(["отмена", "/отмена"]))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Действие отменено", reply_markup=ADMIN_KB)


@admin_router.message(StateFilter("*"), F.text.casefold().in_(["назад", "/назад"]))
async def back_step_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state:
        return

    all_states = AddCard.__all_states__ + AddUser.__all_states__
    previous = None
    for step in all_states:
        if step.state == current_state:
            if previous:
                await state.set_state(previous)
                state_texts = getattr(step.group, "text", {})
                text = state_texts.get(previous.state, "Вы вернулись назад.")
                await message.answer(text)
            else:
                await message.answer("Вы уже на первом шаге.")
            return
        previous = step


@admin_router.message(F.text, StateFilter(AddCard.name, AddUser.name))
async def handle_name_input(message: types.Message, state: FSMContext, session: AsyncSession):
    state_name = await state.get_state()
    is_card = state_name == AddCard.name
    data = await state.get_data()

    if message.text.strip() == ".":
        if "item_for_change" in data:
            await state.update_data(name=data["item_for_change"]["name"])
        else:
            await message.answer("Нельзя пропустить шаг при создании нового объекта.")
            return
    else:
        text = message.text.strip()
        if not (3 <= len(text) <= 150):
            await message.answer("Текст должен быть от 3 до 150 символов.")
            return
        await state.update_data(name=text)

    if is_card:
        await message.answer("Отправьте изображение карточки.")
        await state.set_state(AddCard.image)
    else:
        await save_entity(AddUser, message, state, session)


@admin_router.message(AddCard.image, or_f(F.photo, F.text == "."))
async def handle_card_image(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()

    if message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    elif message.text == ".":
        if "item_for_change" in data:
            await state.update_data(image=data["item_for_change"]["image"])
        else:
            await message.answer("Нельзя пропустить шаг при создании нового объекта.")
            return
    else:
        await message.answer("Отправьте изображение карточки.")
        return

    await save_entity(AddCard, message, state, session)


async def save_entity(state_group, message, state, session):
    data = await state.get_data()
    item_for_change = data.get("item_for_change")
    original_key = data.get("original_key")

    print(item_for_change)

    try:
        if item_for_change:
            if state_group is AddCard:
                await orm_update_card(session, original_key, data)
            elif state_group is AddUser:
                await orm_change_player(session, original_key, data)
        else:
            if state_group is AddCard:
                await orm_add_card(session, data)
            elif state_group is AddUser:
                await orm_add_player(session, data)

        await message.answer("Данные успешно сохранены.", reply_markup=ADMIN_KB)
    except IntegrityError:
        await message.answer("Объект с такими данными уже существует.")
        return
    except Exception as e:
        await message.answer(f"Ошибка при сохранении: {e}")
    finally:
        await state.clear()
