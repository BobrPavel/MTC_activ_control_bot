from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, BigInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Cards(Base):
    __tablename__ = 'cards'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15), unique=True)
    image: Mapped[str] = mapped_column(String(150), nullable=True)


class Statuses(Base): # статус пользователя
    __tablename__ = 'statuses'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Directions(Base): # направдение статистики игрока, +1 пропуск или -1 пропуск
    __tablename__ = 'directions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Players(Base):
    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    count: Mapped[int]

    direction_id: Mapped[int] = mapped_column(ForeignKey('direction.id', ondelete='CASCADE'), nullable=False)
    statuses_id: Mapped[int] = mapped_column(ForeignKey('statuses.id', ondelete='CASCADE'), nullable=False)
    
    direction: Mapped['Statuses'] = relationship(backref='product')
    statuses: Mapped['Statuses'] = relationship(backref='product')
    


    