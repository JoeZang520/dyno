import datetime
import os


class Log:
    def __init__(self, logger_name):
        self._logger_name = logger_name
        if str(logger_name).isdigit():
            self._log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../runtime/log/{logger_name}.log")
        else:
            self._log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../runtime/{logger_name}.log")
    def current(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def info(self, msg):
        colored_msg = f"[{self._logger_name}] {self.current()} {msg}"
        print(colored_msg, flush=True)

        with open(self._log_file, 'a') as f:
            f.write(f"[{self._logger_name}] {self.current()} {msg}" + '\n')

    def debug(self, msg):
        msg = f"[{self._logger_name}] {self.current()} {msg}"
        print(msg, flush=True)

    def debug_start(self, msg):
        start_msg = f"[{self._logger_name}] {msg}"
        print(start_msg, end='', flush=True)

    def debug_append(self, msg='.'):
        print(msg, end='', flush=True)

    def debug_end(self, msg=''):
        print(msg, flush=True)
