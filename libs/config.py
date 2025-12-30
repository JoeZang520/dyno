import json
import os


def get_accounts():
    return get_env('accounts', {})


def get_account(user_id):
    return get_accounts().get(str(user_id), {})


def is_scheduler_running():
    return get_env('run_scheduler', False) is True


def is_axie_pal_enabled(user_id=None):
    if user_id is not None:
        # 只有用户ID为1和2时才启用axie_pal功能
        return user_id in []
    else:
        # 如果没有传入用户ID，默认返回False
        return False


def get_process_limit():
    return get_env('process_limit', {})


def get_exclude_accounts():
    return get_env('exclude_accounts', [])


def is_clay_enabled():
    return get_env('clay', False) is True


def is_sand_enabled():
    return get_env('sand', False) is True


def is_copper_enabled():
    return get_env('copper', False) is True


def get_sleep_configs():
    accounts = get_accounts()
    sleep_configs = {}
    for user_id in accounts:
        account = accounts.get(user_id)
        if 'sleep' in account:
            sleep_configs[user_id] = account.get('sleep')
    return sleep_configs


def get_env(key, default=None):
    try:
        user_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
        with open(user_data_path, 'r') as f:
            env = json.load(f)
    except json.JSONDecodeError as e:
        print('ENV JSON格式错误')
        raise e
    except FileNotFoundError:
        env = {}
    return env.get(key, default)

def get_account_status():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/account_status.json')
        with open(path, 'r') as f:
            status_list = json.load(f)
    except json.JSONDecodeError:
        status_list = {}
    except FileNotFoundError:
        status_list = {}
    return status_list


def save_account_status(data):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/account_status.json')
    status_list_sorted = {k: data[k] for k in sorted(data, key=int)}
    with open(path, 'w') as f:
        json.dump(status_list_sorted, f, indent=4)
