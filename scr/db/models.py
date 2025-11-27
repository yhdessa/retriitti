from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column, Integer, String, DateTime, Text
)

Base = declarative_base()


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False, index=True)
    genre = Column(String(100))
    tags = Column(Text)
    file_id = Column(String(255), nullable=False, unique=True)
    file_name = Column(String(255))
    duration = Column(Integer)
    uploaded_by = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Track(title='{self.title}', artist='{self.artist}')>"


class BotLog(Base):
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255))
    action = Column(String(100), nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BotLog(user_id={self.user_id}, action='{self.action}')>"


def init_db(engine):
    Base.metadata.create_all(bind=engine)
