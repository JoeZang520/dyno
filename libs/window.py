import json
import os
import random
import time
from urllib.parse import urlencode

import requests
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium import webdriver
import sys
import libs.config as data
from libs import config
from libs.log import Log
from libs.window_gpm import GpmWindow


class AdsWindow:
    def __init__(self, ads_id):
        self.api_host = 'http://127.0.0.1:50325'
        self.ads_id = str(ads_id)
        self.log = Log(self.ads_id)
        self.proxy_pool = self.get_proxy_pool()

    def update_window(self, proxy_config=None):
        update_url = f"{self.api_host}/api/v1/user/update"
        self.log.debug_start('update_window...')
        user_id = self.ads_id
        if str(self.ads_id).isdigit():
            accounts = data.get_accounts()
            user_id = accounts.get(str(self.ads_id)).get('user_id')
        max_try_times = 3
        try:
            # 固定窗口尺寸
            payload = {
                "user_id": user_id,
                "fingerprint_config": {
                    "screen_resolution": "920_1100",
                }
            }
            if proxy_config is not None:
                payload['name'] = f"{proxy_config['proxy_host']}:{proxy_config['proxy_port']}"
                payload['user_proxy_config'] = proxy_config
            headers = {
                'Content-Type': 'application/json'
            }
            resp = requests.request("POST", update_url, headers=headers, json=payload).json()
            self.log.debug_end('done')
        except ConnectionError:
            if ++max_try_times < 3:
                self.update_window()
            self.log.debug_end('fail')

    def open(self, close_before_open=True, headless=False):
        user_id = config.get_account(self.ads_id).get('user_id', '')
        if len(user_id) > 10:
            return GpmWindow(self.ads_id).open(close_before_open)

        if close_before_open:
            self.close()
            time.sleep(2)

        account_status = config.get_account_status()

        proxy_port = account_status.get(self.ads_id, {}).get('proxy_port')
        if proxy_port is None:
            proxy_port = self.get_proxy_from_window_name()
            time.sleep(1)
        if proxy_port not in self.proxy_pool:
            proxy_port = None
        if proxy_port is None:
            proxy_port = self.choose_proxy_port()
        proxy = self.proxy_pool.get(proxy_port)
        proxy_country = proxy.get('country')
        proxy_config = {
            "proxy_soft": "other",
            "proxy_type": "socks5",
            "proxy_host": str(proxy_port).split(':')[0],
            "proxy_port": str(proxy_port).split(':')[1],
            "proxy_user": proxy.get('user_name'),
            "proxy_password": proxy.get('password')
        }
        self.update_window(proxy_config=proxy_config)
        time.sleep(1)

        open_resp = self.open_window(headless)
        if open_resp["code"] != 0:
            print(open_resp["msg"])
            print("please check ads_id")
            sys.exit()
        account_status[str(self.ads_id)] = {'proxy_port': proxy_port, 'country': proxy_country, 'running': True}
        config.save_account_status(account_status)
        web_driver = open_resp["data"]["webdriver"]
        is_chrome = True
        if is_chrome:
            service = ChromeService(executable_path=web_driver)
            chrome_options = ChromeOptions()
            chrome_options.add_experimental_option("debuggerAddress", open_resp["data"]["ws"]["selenium"])
            self.log.info(f"start user_id={self.ads_id} with proxy_port={proxy_port}[{proxy_country}]")
            return webdriver.Chrome(service=service, options=chrome_options)
        else:
            port = open_resp["data"]["marionette_port"]
            # driver 实际路径
            firefox_services = FirefoxService(executable_path=web_driver,
                                              service_args=['--marionette-port', port, '--connect-existing'])
            return webdriver.Firefox(service=firefox_services)

    def open_window(self, headless=False):
        user_key = 'user_id'
        if str(self.ads_id).isdigit():
            user_key = 'serial_number'
        query = {
            'open_tabs': 1,
            'ip_tab': 0,
            'launch_args': '["--disable-blink-features=UserAgentClientHint"]',
            user_key: self.ads_id
        }
        if headless:
            query['headless'] = 1
        open_url = f"{self.api_host}/api/v1/browser/start?{urlencode(query)}"
        print('open_window', end='', flush=True)
        max_try_times = 3
        try:
            print('.', end='', flush=True)
            open_resp = requests.get(open_url).json()
            print('done', flush=True)
            return open_resp
        except ConnectionError:
            if ++max_try_times < 3:
                self.open_window()
            print('fail', flush=True)

    def close(self):
        user_id = config.get_account(self.ads_id).get('user_id', '')
        if len(user_id) > 10:
            return GpmWindow(self.ads_id).close()

        user_key = 'user_id'
        if str(self.ads_id).isdigit():
            user_key = 'serial_number'
        close_url = f"{self.api_host}/api/v1/browser/stop?{user_key}={self.ads_id}"
        self.log.debug_start('close_window')
        max_try_times = 3
        try:
            self.log.debug_append()
            requests.get(close_url)
            time.sleep(1)
            self.log.debug_end('done')
        except Exception:
            if ++max_try_times < 3:
                self.close()
            self.log.debug_end('fail')

    def choose_proxy_port(self):
        status_list = config.get_account_status()
        proxy_ports = list(self.proxy_pool.keys())
        using_ports = {}
        for user_id in status_list:
            status = status_list.get(user_id)
            port = status.get('proxy_port')
            if port in proxy_ports:
                using_ports[port] = using_ports.get(port, 0) + 1
        selected_port = None
        random.shuffle(proxy_ports)
        # 找使用次数最少的IP
        min_using_times = 0
        if len(using_ports) > 0:
            min_using_times = min(using_ports.values())
        for port in proxy_ports:
            country = self.proxy_pool.get(port)
            using_count = using_ports.get(port, 0)
            if using_count > min_using_times:
                continue
            self.log.info(f'choose {port}[{country}]')
            selected_port = port
            break

        return selected_port

    def get_proxy_pool(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/proxy_pool.json')
            with open(path, 'r') as f:
                proxy_pool = json.load(f)
        except json.JSONDecodeError:
            proxy_pool = {}
        except FileNotFoundError:
            proxy_pool = {}
        return proxy_pool

    def get_proxy_from_window_name(self):
        query_url = f"{self.api_host}/api/v1/user/list?serial_number={self.ads_id}"
        query_resp = requests.get(query_url).json()
        user_list = query_resp.get('data', {}).get('list', [])
        if len(user_list) > 0:
            name = user_list[0].get('name', '')
            if name in self.proxy_pool:
                return name
        return None
