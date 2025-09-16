from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from requests import session

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_card,
    orm_get_card,
    orm_get_cards,
    orm_update_card,
    orm_delete_card,
)

from filters.chat_types import ChatTypeFilter, IsAdmin

from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard, del_reply_kd


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard(
    "Карточки",
    "Пользователи",
    placeholder="Выберите действие",
    sizes=(2,),
)


@admin_router.message(Command("admin"))
async def admin_on(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


@admin_router.message(Command("off"))
async def admin_off(message: types.Message):
    await message.answer("Админ клавиатура удалена", reply_markup=del_reply_kd)


################# FSM для загрузки изменения карточек бронепробития ############################

class AddCard(StatesGroup):
    name = State()
    image = State()

    card_for_change = None

    text = {
        "AddCard:name": "Введите название заново:",
        "AddCard:image": "Этот стейт последний, поэтому...",
    }
    

# Хендлер отмены и сброса состояния должен быть всегда именно здесь,
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddCard.card_for_change:
        AddCard.card_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Вернутся на шаг назад (на прошлое состояние)
@admin_router.message(StateFilter("*"), Command("назад"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddCard.name:
        await message.answer(
            'Предидущего шага нет, или введите название техники или напишите "отмена"')
        return

    previous = None
    for step in AddCard.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                f"Ок, вы вернулись к прошлому шагу \n {AddCard.texts[previous.state]}"
            )
            return
        previous = step


# Ловим данные для состояние name и потом меняем состояние на image
@admin_router.message(AddCard.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddCard.card_for_change:
        await state.update_data(name=AddCard.card_for_change.name)
    else:
        # Здесь можно сделать какую либо дополнительную проверку
        # и выйти из хендлера не меняя состояние с отправкой соответствующего сообщения
        # например:
        if 4 >= len(message.text) >= 150:
            await message.answer(
                "Название товара не должно превышать 150 символов\nили быть менее 5ти символов. \n Введите заново"
            )
            return

        await state.update_data(name=message.text)
    await message.answer("Отправьте карточку")
    await state.set_state(AddCard.image)

# Хендлер для отлова некорректных вводов для состояния name
@admin_router.message(AddCard.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите текст названия техники")


# Ловим данные для состояние image и потом выходим из состояний
@admin_router.message(AddCard.image, or_f(F.photo, F.text == "."))
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text == "." and AddCard.card_for_change:
        await state.update_data(image=AddCard.card_for_change.image)

    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Отправьте карточку в виде картинки")
        return
    data = await state.get_data()
    try:
        if AddCard.card_for_change:
            await orm_update_card(session, AddCard.card_for_change.id, data)
        else:
            await orm_add_card(session, data)
        await message.answer("Карточка добавлена/изменена", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\nОбратись к программеру, он опять денег хочет",
            reply_markup=ADMIN_KB,
        )
        await state.clear()

    AddCard.card_for_change = None

# Ловим все прочее некорректное поведение для этого состояния
@admin_router.message(AddCard.image)
async def add_image2(message: types.Message, state: FSMContext):
    await message.answer("Отправьте фото пищи")


#########################################################################################


# Становимся в состояние ожидания ввода name
@admin_router.message(StateFilter(None), F.text.startswith("add-card"))
async def change_card_(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    await message.answer(
        "Введите название техники", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddCard.name)


# Становимся в состояние ожидания ввода name для изменения карточки
@admin_router.message(StateFilter(None), F.text.startswith("change-card_"))
async def change_card(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    name = message.text.split("_")[-1]

    card_for_change = await orm_get_card(session, name)

    AddCard.product_for_change = card_for_change

    # await callback.answer()
    await message.answer(
        "Введите название техникиа", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddCard.name)


@admin_router.message(StateFilter(None), F.data == "card-list")
async def list_of_cards_(message: types.Message, session: AsyncSession):
    cards = await orm_get_cards(session)
    text = ""
    for card in cards:
        text = text + f"{str(card.name)} \n"
    await message.answer(f"Вот список карточек: \n\n {text}")


@admin_router.message(StateFilter(None), F.text.startswith("delete_"))
async def delete_card(message: types.Message, session: AsyncSession):
    name = message.text.split("_")[-1]
    await orm_delete_card(session, name)
    await message.answer(f"Карточка {name} удалена")
    



    