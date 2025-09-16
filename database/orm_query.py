import math
from subprocess import list2cmdline
from sqlalchemy import select, update, delete, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Cards, Statuses, Directions, Players



############################ Категории Statuses и Directions ######################################

async def orm_get_statuses(session: AsyncSession):
    query = select(Statuses)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_directions(session: AsyncSession):
    query = select(Directions)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_create_statuses(session: AsyncSession, categories: list2cmdline()):
    query = select(Statuses)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Statuses(name=name) for name in categories])
    await session.commit()


async def orm_create_directions(session: AsyncSession, categories: list2cmdline()):
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


async def orm_update_player_plus(session: AsyncSession, player_names: list) -> None:
    query = (
        update(Players)
        .where(Players.name.in_(player_names))
        .values(score=Players.score + 1)
    )
    await session.execute(query)
    session.commit()


async def orm_update_player_minus(session: AsyncSession, player_names: list) -> None:

    new_pass = func.greatest(Players.score - 1, 0)

    new_status = case(
        (new_pass > 3, 2),
        else_=Players.status_id
    )

    query = (
        update(Players)
        .where(Players.name.in_(player_names))
        .values(
            score=new_pass,
            status_id=new_status
        )
    )
    await session.execute(query)
    session.commit()


async def orm_get_players(session: AsyncSession):
    query = select(Players)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_delete_player(session: AsyncSession, player_name: str):
    query = delete(Players).where(Players.name == player_name)
    result = await session.execute(query)
    await session.commit()



