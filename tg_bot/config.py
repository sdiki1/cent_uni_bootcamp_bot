import logging
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from environs import Env


@dataclass
class TgBot:
    token: str
    public_url: str
    local_url: str
    local_port: int


@dataclass
class YandexApiConfig:
    folder_id: str
    api_key: str


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str


@dataclass
class Config:
    tg_bot: TgBot
    yandex_api: YandexApiConfig
    db_config: DbConfig


def load_config(path: str = ".env") -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            public_url=env.str("PUBLIC_URL"),
            local_url=env.str("LOCAL_URL"),
            local_port=env.int("LOCAL_PORT")
        ),
        yandex_api=YandexApiConfig(
            folder_id=env.str("YANDEX_FOLDER_ID"), 
            api_key=env.str("YANDEX_API_KEY")
        ),
        db_config=DbConfig(
            host=env.str("DB_HOST"),
            password=env.str("DB_PASSWORD"),
            user=env.str("DB_USER"),
            database=env.str("DB_NAME"),
        ),
    )


def setup_logger(name: str = "bot") -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename="logs/bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
