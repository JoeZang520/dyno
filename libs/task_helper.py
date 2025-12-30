import argparse
import time

from libs import config
from libs.scheduler import Scheduler
# from libs.scheduler_v2 import SchedulerV2, TaskStatus
from libs.window import AdsWindow


class TaskHelper:
    def __init__(self, user_id):
        self.scheduler = Scheduler()
        self.user_id = user_id
        self.task_id = None
        self.retry = 0

    @staticmethod
    def default_args_parser(description):
        # 解析参数
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument('--user_id', type=int, required=True, help="用户ID")
        parser.add_argument('--task_id', type=int, help="任务ID")
        parser.add_argument('--retry', type=int, help="重试次数")
        return parser

    @staticmethod
    def from_args(args):
        task_helper = TaskHelper(args.user_id)
        task_helper.task_id = args.task_id
        if args.retry:
            task_helper.retry = args.retry
        return task_helper


    def dyno(self, delay_seconds=0, ignore_running=True, retry=False):
        self.add_task(f'dyno.py', delay_seconds, ignore_running, retry)


    def add_task(self, script, delay_seconds, ignore_running, retry=False, args=None):
        if args is None:
            args = {}
        if retry:
            if self.retry == 0:
                delay_seconds = 10  # 第一次10秒后重试
            elif self.retry == 1:
                delay_seconds = 60 * 10  # 第二次10分钟后重试
            elif self.retry == 2:
                delay_seconds = 60 * 60 * 1  # 第三次1小时后重试
            elif self.retry == 3:
                delay_seconds = 60 * 60 * 10  # 第四次10小时后重试
            else:
                return
            args['retry'] = self.retry + 1

        self.scheduler.add_task(
            script,
            self.user_id,
            args=args,
            delay_seconds=delay_seconds,
            ignore_running=ignore_running
        )


