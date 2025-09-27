import math
from subprocess import list2cmdline
from httpx import stream
from sqlalchemy import select, update, delete, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Cards, Statuses, Directions, Players



############################ Категории Statuses и Directions ######################################

async def orm_get_statuses(session: AsyncSession):
    query = select(Statuses)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_status(session: AsyncSession, status_id: int):
    query = select(Statuses).where(Statuses.id == status_id)
    result = await session.execute(query)
    return result.scalars()


async def orm_get_directions(session: AsyncSession):
    query = select(Directions)
    result = await session.execute(query)
    return result.scalars().all()





async def orm_create_statuses(session: AsyncSession, categories: list):
    query = select(Statuses)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Statuses(name=name) for name in categories])
    await session.commit()


async def orm_create_directions(session: AsyncSession, categories: list):
    query = select(Directions)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Directions(name=name) for name in categories])
    await session.commit()
  

############ Админка: добавить/изменить/удалить карточку ########################

async def orm_add_card(session: AsyncSession, data: dict):
    obj = Cards(
        name=data["name"],
        image=data["image"],
    )
    session.add(obj)
    await session.commit()


async def orm_update_card(session: AsyncSession, name: str, data):
    query = (
        update(Cards)
        .where(Cards.name == name)
        .values(
            name=data["name"],
            image=data["image"],
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_get_cards(session: AsyncSession):
    query = select(Cards)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_card(session: AsyncSession, name: str):
    query = select(Cards).where(Cards.name == name)
    result = await session.execute(query)
    return result.scalar()


async def orm_delete_card(session: AsyncSession, name: int):
    query = delete(Cards).where(Cards.name == name)
    await session.execute(query)
    await session.commit()


##################### Добавляем игрока в БД #####################################

async def orm_add_player(session: AsyncSession, data: dict):
    obj = Players(
        name=data["name"],
        count=0,
        direction_id=1,
        statuses_id=1,
    )
    session.add(obj)
    await session.commit()


async def orm_change_player(session: AsyncSession, player_name: str, data: dict):
    query = (
        update(Players)
        .where(Players.name == player_name)
        .values(
            name=data["name"])
    )
    await session.execute(query)
    await session.commit()



async def orm_update_player_plus(session: AsyncSession, player_names: list) -> None:
    query = (
        update(Players)
        .where(Players.name.in_(player_names))
        .values(
            count=Players.count + 1,
            statuses_id=case(
                (Players.count + 1 > 3, 3),
                else_=Players.statuses_id),
            direction_id=2
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_update_player_minus(session: AsyncSession, player_names: list) -> None:


    query = (
        update(Players)
        .where(Players.name.in_(player_names))
        .values(
            count=case(
                (Players.count - 1 < 0, 0),  # если после уменьшения меньше 0 — ставим 0
                else_=Players.count - 1),
            direction_id=case(
                (Players.count - 1 < 0, 1),  # если после уменьшения меньше 0 — ставим 1
                else_=3),
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_get_player(session: AsyncSession, player_names: str):
    query = select(Players).where(Players.name == player_names).options(joinedload(Players.statuses), joinedload(Players.direction))
    result = await session.execute(query)
    return result.scalar()





async def orm_get_players(session: AsyncSession, status_id: int | None = None):
    if status_id is None:
        query = select(Players).options(joinedload(Players.statuses))
    else:
        query = select(Players).where(Players.statuses_id == status_id).options(joinedload(Players.statuses), joinedload(Players.direction))

    result = await session.execute(query)
    return result.scalars().all()


async def orm_change_status_player(session: AsyncSession, player_name: str, status: int):
    query = (
        update(Players)
        .where(Players.name == player_name)
        .values(
            statuses_id=status,
            direction_id=case(
                (Players.statuses_id==2, 1),
                else_=Players.direction_id
            )
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_get_players2(session: AsyncSession):
    query = select(Players.name).where(Players.statuses_id==1 )
    result = await session.execute(query)
    return result.scalars().all()


async def orm_delete_player(session: AsyncSession, player_name: str):
    query = delete(Players).where(Players.name == player_name)
    await session.execute(query)
    await session.commit()



