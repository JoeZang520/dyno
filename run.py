import datetime
import time

import requests

import libs.config as config
from libs.scheduler import Scheduler
from libs.task_helper import TaskHelper

scheduler = Scheduler()

def local_active_check():
    try:
        check_resp = requests.get('http://127.0.0.1:50325/api/v1/browser/local-active').json()
        active_list = check_resp.get('data', {}).get('list')
        user_id_map = {}
        account_status = config.get_account_status()
        for user_sn in accounts:
            account = accounts.get(user_sn)
            user_id_map[account.get('user_id')] = user_sn

        active_user_ids = []
        for active_item in active_list:
            active_user_id = active_item.get('user_id')
            user_sn = user_id_map.get(active_user_id)
            active_user_ids.append(user_sn)

        for account_user_id in account_status:
            status = account_status.get(account_user_id)
            status['running'] = False
            if account_user_id in active_user_ids:
                status['running'] = True
        config.save_account_status(account_status)
    except:
        pass


def init_tasks():
    for user_id in accounts:
        account = accounts.get(user_id)
        # 检查是否有 delay_minutes 配置，如果有则启用 dyno 任务
        if 'delay_minutes' in account:
            # 立即添加任务，由 process_limit 控制并发数量
            TaskHelper(user_id).dyno(delay_seconds=0, ignore_running=False)


def check_and_recover_tasks():
    """检查并恢复丢失的任务"""
    scheduler.logger.debug('# check_and_recover_tasks')
    
    # 获取当前待执行的任务
    pending_tasks = scheduler.read_tasks()
    running_tasks = scheduler.read_running_tasks()
    
    # 获取所有应该运行 dyno 任务的账户
    dyno_accounts = []
    for user_id in accounts:
        account = accounts.get(user_id)
        if 'delay_minutes' in account:
            dyno_accounts.append(user_id)
    
    # 检查每个账户是否有对应的 dyno 任务
    for user_id in dyno_accounts:
        task_id = f"{user_id}_dyno"
        
        # 检查是否在待执行任务中
        has_pending_task = task_id in pending_tasks
        
        # 检查是否在运行中任务中
        has_running_task = False
        for running_task in running_tasks.values():
            if running_task.get('user_id') == str(user_id) and 'dyno.py' in running_task.get('command', ''):
                has_running_task = True
                break
        
        # 如果既没有待执行任务也没有运行中任务，则添加新任务
        if not has_pending_task and not has_running_task:
            # 立即添加任务，由 process_limit 控制并发数量
            scheduler.logger.info(f'恢复丢失的任务: 用户 {user_id} 的 dyno 任务')
            TaskHelper(user_id).dyno(delay_seconds=0, ignore_running=False)


if __name__ == "__main__":
    last_init_time = None
    last_check_time = None
    accounts = config.get_accounts()
    # 任务初始化
    init_tasks()
    
    # 任务检查间隔（秒），默认每10分钟检查一次
    task_check_interval = int(config.get_env('task_check_interval', 300))
    
    while True:
        if not config.is_scheduler_running():
            scheduler.logger.debug('scheduler is terminated, take no action')
        else:
            scheduler.run()
        # 检查窗口打开状态
        local_active_check()
        
        # 定期检查并恢复丢失的任务
        current_time = datetime.datetime.now()
        if last_check_time is None or (current_time - last_check_time).seconds >= task_check_interval:
            check_and_recover_tasks()
            last_check_time = current_time
        
        run_duration = int(config.get_env('run_duration', 30))
        time.sleep(run_duration)
