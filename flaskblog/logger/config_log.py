from multipledispatch import dispatch
import logging.config
import os
from flaskblog.config import Config


LOG_DIR = Config.LOG_DIR  # "./log"
LOG_FILE = Config.LOG_FILE  # "FLASK.log"


class ConfigLogger:
    baseNameLogger = "Stdout"
    pathLoggerDir = LOG_DIR
    nameFileLogger = LOG_FILE
    isSetting = False  # для того чтобы не создавать новый файл каждый раз при запуске программы

    @staticmethod
    def __createLogDir(pathDir):
        """Создание папки для лог-файлов"""
        if not os.path.exists(pathDir):
            os.mkdir(pathDir)

    @staticmethod
    def settingLogger():
        """настройка логгера с использованием словаря"""
        if not ConfigLogger.isSetting:
            ConfigLogger.__createLogDir(pathDir=ConfigLogger.pathLoggerDir)
            logging.config.dictConfig(logging_config)
            logging.basicConfig(level=logging.INFO, handlers=[])
            ConfigLogger.isSetting = True

    @staticmethod
    @dispatch(str)
    def getLogger(nameMod):
        """получение базового логгера"""
        return logging.getLogger(ConfigLogger.baseNameLogger + "." + nameMod)

    @staticmethod
    @dispatch(str, str)
    def getLogger(nameBase, nameMod):
        """nameBase берётся из словаря = 'loggers'
        OnlyFile - логгер будет писать в файл, в консоль не будет
        Stdout - только в консоль
        FileStdout - и в консоль и в файл
        """
        if not ConfigLogger.isSetting:
            ConfigLogger.settingLogger()
        return logging.getLogger(nameBase + "." + nameMod)

    # def templates_logging():
    #     logFC = ConfigLogger.getLogger("FileStdout", "name1")
    #     logF = ConfigLogger.getLogger("OnlyFile", "name2")
    #     logFC.info("Пример использования запись в файл и консоль")
    #     logF.info("Пример использования запись только в файл")


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "form1": {
            "format": "/* %(asctime)s - %(module)s.%(funcName)s(%(lineno)d) - [%(threadName)s] - %(thread)d - [%(processName)s] - %(process)d */ -> \n%(levelname)s: %(message)s"
        },
        "form2": {
            "format": "/* %(asctime)s - %(module)s.%(funcName)s(%(lineno)d) - [%(threadName)s] - [%(thread)d] */  \n%(levelname)s: %(message)s"
        },
        "form3": {
            "format": "/* %(asctime)s - %(module)s.%(funcName)s(%(lineno)d) - %(name)s */ -> \n%(levelname)s: %(message)s"
        },
        "form4": {
            "format": "/* %(asctime)s - %(module)s.%(funcName)s(%(lineno)d) - [%(processName)s] - %(process)d */ -> \n%(levelname)s: %(message)s"
        },
        "con1": {
            "format": "%(asctime)s - %(module)s.%(funcName)s(%(lineno)d) - [%(threadName)s] - [%(thread)d] \n > %(levelname)s: %(message)s"
        },
        "con2": {"format": "%(message)s"},
    },
    "handlers": {
        "rotating_file1": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "form2",
            "filename": f"{ConfigLogger.pathLoggerDir}/{ConfigLogger.nameFileLogger}",
            "maxBytes": 1048576,
            "backupCount": 20,
        },
        "console1": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "con1",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "Stdout": {"handlers": ["console1"], "level": "DEBUG"},
        "FileStdout": {"handlers": ["rotating_file1", "console1"], "level": "DEBUG"},
        "OnlyFile": {"handlers": ["rotating_file1"], "level": "DEBUG"},
    },
}
