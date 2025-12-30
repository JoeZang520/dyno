import time
from urllib.parse import urlencode

import requests
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver
import sys
from libs import config
from libs.log import Log


class GpmWindow:
    def __init__(self, id):
        self.api_host = f'http://127.0.0.1:{config.get_env('gpm_api_port', 19915)}/api/v3'
        account = config.get_account(id)
        self.gpm_id = account.get('user_id')
        self.log = Log(id)

    def open(self, close_before_open=True):
        if close_before_open:
            self.close()
            time.sleep(2)

        open_resp = self.open_window()
        if not open_resp["success"]:
            print(self.gpm_id, open_resp)
            sys.exit()

        web_driver = open_resp["data"]["driver_path"]

        service = ChromeService(executable_path=web_driver)
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--force-color-profile=srgb')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        # 添加超时和稳定性配置
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option("debuggerAddress", open_resp["data"]["remote_debugging_address"])
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # 设置更长的超时时间
        driver.set_page_load_timeout(60)  # 页面加载超时60秒
        driver.implicitly_wait(10)  # 隐式等待10秒
        return driver

    def open_window(self):
        query = {
            'win_scale': 1,
            'win_size': "1800,660",
            'win_pos': "0,0",
            'addination_args': ' --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run '
        }

        open_url = f"{self.api_host}/profiles/start/{self.gpm_id}?{urlencode(query)}"
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
        close_url = f"{self.api_host}/profiles/close/{self.gpm_id}"
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
