import logging
import os.path


def setup_loggers():
    # telethon_logger = logging.getLogger("telethon")
    # telethon_logger.setLevel(logging.CRITICAL)

    base_path = os.path.join(os.getcwd(), "logs")

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                                  datefmt='%Y-%m-%d %H:%M:%S')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    errors = logging.getLogger("errors")
    file_error_handler = logging.FileHandler(os.path.join(base_path, "error_log.log"))
    errors.setLevel(level=logging.ERROR)
    errors.addHandler(file_error_handler)
    errors.addHandler(stream_handler)

    access = logging.getLogger("access")
    access_file_handler = logging.FileHandler(os.path.join(base_path, "access_log.log"))
    access_file_handler.setFormatter(formatter)
    access.setLevel(level=logging.INFO)
    access.addHandler(access_file_handler)
    # access.addHandler(stream_handler)

    debug_file_handler = logging.FileHandler(os.path.join(base_path, "debug_log.log"))

    logging.basicConfig(handlers=(debug_file_handler, stream_handler), level=logging.DEBUG)
    # httpcore_logger = logging.getLogger("httpcore")
    # httpcore_logger.setLevel(logging.CRITICAL)


class ToLog:

    error = logging.getLogger("error")
    access = logging.getLogger("access")
    basic = logging.getLogger("basic")

    @classmethod
    def write_error(cls, msg: str):
        cls.error.error(msg)

    @classmethod
    def write_basic(cls, msg: str):
        cls.basic.info(msg)

    @classmethod
    def write_access(cls, msg: str):
        cls.access.info(msg)
