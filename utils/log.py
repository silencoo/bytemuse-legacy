import datetime
import logging
import inspect
import colorama
from colorama import Fore, Style
from app.settings import log_path

colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    LEVEL_COLOR = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA
    }

    def format(self, record):
        log_color = self.LEVEL_COLOR.get(record.levelno, Fore.WHITE)
        # 当前时间
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_format = f'{current_time} {log_color}%(levelname)s - %(pathname)s:%(lineno)d - %(message)s{Style.RESET_ALL}'
        formatter = logging.Formatter(log_format)
        return formatter.format(record)


class Logger:
    def __init__(self):
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Create file handler
        log_file = log_path
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)

        # Create formatters
        console_formatter = ColoredFormatter()
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')

        # Set formatters
        ch.setFormatter(console_formatter)
        fh.setFormatter(file_formatter)

        # Add handlers to logger
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def _log(self, level, msg):
        frame = inspect.currentframe().f_back.f_back

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn=frame.f_code.co_filename,
            lno=frame.f_lineno,
            msg=msg,
            args=(),
            exc_info=None,
            func=frame.f_code.co_name
        )
        self.logger.handle(record)

    def debug(self, msg):
        self._log(logging.DEBUG, msg)

    def info(self, msg):
        self._log(logging.INFO, msg)

    def warning(self, msg):
        self._log(logging.WARNING, msg)

    def error(self, msg):
        self._log(logging.ERROR, msg)

    def critical(self, msg):
        self._log(logging.CRITICAL, msg)


logger = Logger()
