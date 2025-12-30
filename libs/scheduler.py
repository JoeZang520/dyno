import subprocess
import os
from datetime import datetime, timedelta

import psutil
import json

from libs import config
from libs.log import Log


class Scheduler:
    def __init__(self):
        self.logger = Log('scheduler')
        self.running_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../runtime/tasks.running')
        self.pending_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../runtime/tasks.pending')
        self.datetime_format = '%Y-%m-%d %H:%M:%S'

    # 检查进程是否仍在运行
    def is_process_running(self, pid):
        return psutil.pid_exists(int(pid))

    # 读取运行中的进程
    def read_running_tasks(self):
        try:
            with open(self.running_file_path, 'r') as f:
                # 使用 json.load() 方法加载数据
                tasks = json.load(f)
                running_tasks = {}
                for pid in tasks:
                    if self.is_process_running(pid):
                        running_tasks[pid] = tasks.get(pid)
        except FileNotFoundError:
            running_tasks = {}
        except json.JSONDecodeError:
            running_tasks = {}
        self.write_running_tasks(running_tasks)
        return running_tasks

    def write_running_tasks(self, tasks):
        with open(self.running_file_path, 'w') as f:
            json.dump(tasks, f, indent=4)

    # 获取任务列表
    def read_tasks(self):
        try:
            with open(self.pending_file_path, 'r') as f:
                # 使用 json.load() 方法加载数据
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = {}
        except json.JSONDecodeError:
            tasks = {}
        return tasks

    def add_task(self, script, user_id, args=None, execute_time: datetime = None, delay_seconds=0, ignore_running=True):
        if args is None:
            args = []
        new_id = self.get_task_id(user_id, script)
        if execute_time is None:
            execute_time = datetime.now()
        if delay_seconds is not None:
            execute_time = execute_time + timedelta(seconds=delay_seconds)
        time_str = execute_time.strftime(self.datetime_format)
        command = f"python {script} {user_id}"
        if len(args) > 0:
            # 处理重试参数
            if 'retry' in args:
                retry_count = args['retry']
                command += f" retry={retry_count}"
            else:
                command += f" {' '.join([f'{k}={v}' for k, v in args.items()])}"
        tasks = self.read_tasks()
        if new_id in tasks:
            # 如果是重试任务，更新执行时间
            if 'retry' in args:
                print(f"Task ID {new_id} already exists. Updating execute time for retry.")
                tasks[new_id]['execute_time'] = time_str
                tasks[new_id]['create_time'] = datetime.now().strftime(self.datetime_format)
                self.save_tasks(tasks)
                return 1
            else:
                print(f"Task ID {new_id} already exists. Skipping.")
                return 0
        running_tasks = self.read_running_tasks()
        is_running = False
        for running_task in running_tasks.values():
            if new_id == self.get_task_id(running_task.get('user_id'), running_task.get('command').split(' ')[1]):
                is_running = True
                break
        if not ignore_running and is_running:
            return 0
        self.logger.info('add_task ' + json.dumps({'command': command, 'execute_time': time_str}))
        tasks[new_id] = {'command': command, 'execute_time': time_str,
                         'create_time': datetime.now().strftime(self.datetime_format)}
        self.save_tasks(tasks)
        return 1

    def get_task_id(self, user_id, script):
        return f"{user_id}_{str(script).replace('.py', '')}"

    def get_channel_from_command(self, cmd):
        script = cmd.split(' ')[1].replace('.py', '')
        if script == 'farm':
            soil_id = cmd.split(' ')[3]
            channel = f"farm_{soil_id}"
        else:
            channel = script
        return channel

    def next_task(self):
        pending_tasks = self.read_tasks()
        running_tasks = self.read_running_tasks()
        account_status = config.get_account_status()
        process_limit = config.get_process_limit()
        exclude_accounts = config.get_exclude_accounts()
        channel_process_counts = {}
        running_users = []
        for pid in running_tasks:
            running_task = running_tasks.get(pid)
            running_users.append(str(running_task.get('user_id')))
            channel = self.get_channel_from_command(running_task.get('command'))
            channel_process_counts[channel] = channel_process_counts.get(channel, 0) + 1
            if channel.startswith('farm_'):
                channel_process_counts['farm'] = channel_process_counts.get('farm', 0) + 1
        running_ips = {}
        for user_id in account_status:
            status = account_status.get(user_id)
            ip = status.get('proxy_port')
            is_running = status.get('running', False)
            if is_running:
                user_ids = running_ips.get(ip, [])
                user_ids.append(user_id)
                running_ips[ip] = user_ids
        sleep_configs = config.get_sleep_configs()
        
        # 首先处理重试任务，然后处理普通任务
        retry_tasks = []
        normal_tasks = []
        
        for task_id in pending_tasks:
            pending_task = pending_tasks.get(task_id)
            command = pending_task.get('command', '')
            is_retry = 'retry' in command
            
            if is_retry:
                retry_tasks.append((task_id, pending_task))
            else:
                normal_tasks.append((task_id, pending_task))
        
        # 按执行时间排序
        retry_tasks.sort(key=lambda x: x[1]['execute_time'])
        normal_tasks.sort(key=lambda x: x[1]['execute_time'])
        
        # 合并任务列表，重试任务在前
        all_tasks = retry_tasks + normal_tasks
        
        for task_id, pending_task in all_tasks:
            user_id = task_id.split('_')[0]
            execute_time_str = pending_task['execute_time']
            execute_time = datetime.strptime(execute_time_str, self.datetime_format)
            current_time = datetime.now()
            is_expired = execute_time <= current_time  # 任务是否已过期或到执行时间
            
            # 检查账号是否在休息
            if user_id in sleep_configs:
                sleep_config = sleep_configs.get(user_id)
                start = sleep_config[0]
                end = sleep_config[1]
                hour = datetime.now().hour
                if end > start and start <= hour <= end:
                    continue
                if end < start and (hour >= start or hour <= end):
                    continue

            if int(user_id) in exclude_accounts:
                continue
            if str(user_id) in running_users:
                continue
            
            # 如果任务还没到执行时间，跳过
            if not is_expired:
                continue
            
            channel = self.get_channel_from_command(pending_task.get('command'))
            
            # 检查并发限制（所有任务都遵守process_limit配置）
            # 由于任务已按执行时间排序，过期任务会优先被检查，所以会优先执行
            channel_limit = process_limit.get(channel, 1)
            channel_running = channel_process_counts.get(channel, 0)
            if channel_running >= channel_limit:
                continue

            if channel.startswith('farm_'):
                channel = 'farm'
                channel_limit = process_limit.get(channel, 1)
                channel_running = channel_process_counts.get(channel, 0)
                if channel_running >= channel_limit:
                    continue

            pending_task['id'] = task_id
            pending_task['user_id'] = user_id
            return pending_task
        return None

    def get_next_task_info(self):
        """获取下一个即将执行的任务信息"""
        pending_tasks = self.read_tasks()
        if not pending_tasks:
            return None
        
        # 按执行时间排序，获取最早的任务
        sorted_tasks = sorted(pending_tasks.items(), key=lambda x: x[1]['execute_time'])
        
        for task_id, task_data in sorted_tasks:
            user_id = task_id.split('_')[0]
            execute_time = task_data['execute_time']
            command = task_data['command']
            
            # 解析脚本名称
            script_name = command.split(' ')[1].replace('.py', '') if len(command.split(' ')) > 1 else 'unknown'
            
            return {
                'user_id': user_id,
                'execute_time': execute_time,
                'script_name': script_name,
                'task_id': task_id
            }
        
        return None

    def save_tasks(self, tasks):
        # 按优先级排序：重试任务优先，然后按执行时间排序
        def sort_key(item):
            task_id, task_data = item
            command = task_data.get('command', '')
            is_retry = 'retry' in command
            execute_time = task_data.get('execute_time', '')
            
            # 重试任务优先级更高（返回较小的值）
            priority = 0 if is_retry else 1
            return (priority, execute_time)
        
        sorted_tasks = dict(sorted(tasks.items(), key=sort_key))
        with open(self.pending_file_path, 'w') as f:
            json.dump(sorted_tasks, f, indent=4)

    def remove_task(self, task_id):
        tasks = self.read_tasks()
        if task_id in tasks:
            tasks.pop(task_id)
            self.save_tasks(tasks)

    def run(self):
        running_tasks = self.read_running_tasks()
        # 读取待执行的任务列表
        task = self.next_task()
        if task is None:
            # 获取下一个即将执行的任务信息
            next_task_info = self.get_next_task_info()
            if next_task_info:
                self.logger.debug(
                    f"no_coming_tasks: waiting_count={len(self.read_tasks())}, running_count={len(running_tasks)}, "
                    f"下一个任务: 窗口{next_task_info['user_id']} 执行时间 {next_task_info['execute_time']}")
            else:
                self.logger.debug(
                    f"no_coming_tasks: waiting_count={len(self.read_tasks())}, running_count={len(running_tasks)}")
            return

        self.remove_task(task.get('id'))
        command = task.get('command')
        working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
        env = os.environ.copy()
        process = subprocess.Popen(
            command,
            shell=True,
            start_new_session=True,
            cwd=working_dir,
            env=env
        )
        task_pid = process.pid
        self.logger.info('run_task ' + json.dumps({'command': command}))
        running_tasks = self.read_running_tasks()
        running_tasks[task_pid] = {
            "start_time": datetime.now().strftime(self.datetime_format),
            "command": command,
            "user_id": task.get('user_id'),
        }
        self.write_running_tasks(running_tasks)
