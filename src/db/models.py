from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Track(Base):
    __tablename__ = 'tracks'

    track_id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(Text, nullable=False, index=True)
    artist = Column(Text, nullable=False, index=True)

    telegram_file_id = Column('file_id', Text, nullable=False, unique=True)

    album = Column(Text, nullable=True, index=True)
    genre = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)
    tags = Column(Text, nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Track(id={self.track_id}, title='{self.title}', artist='{self.artist}')>"

    @property
    def file_id(self):
        return self.telegram_file_id

    @file_id.setter
    def file_id(self, value):
        self.telegram_file_id = value

    def to_dict(self) -> dict:
        return {
            'track_id': self.track_id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'file_id': self.telegram_file_id,
            'duration': self.duration,
            'tags': self.tags,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }

    def duration_formatted(self) -> str:
        if not self.duration:
            return "Unknown"
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"
