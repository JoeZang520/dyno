import re
import time
import requests

from tqdm import tqdm
from bs4 import BeautifulSoup
from pytimeparse.timeparse import timeparse

##################
### 访问参数设置 ###
##################

# Request headers, 不建议修改
headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Referer": "https://axie.top/",
    "hx-current-url": "https://axie.top/",
    "hx-request": "true",
    "hx-target": "leaderboard-and-pagination",

    # 以下 sec-* / sec-ch-ua 系列通常可选，但有时服务器会做 UA fingerprint 检查
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# Request cookie, 包含premium用户身份信息，当前用的是我的身份，也可以在网站开发中工具networks中，找到自己账户的身份信息
cookie_string = (
    "ph_phc_9YFFGL1zQqAdvT2ewfygSewSd8CrpbAkL5tM4Q8vGl5_posthog=%7B%22distinct_id%22%3A%2201975980-7418-70a0-aef4-174a0d7a7c4c%22%2C%22%24sesid%22%3A%5B1753942794151%2C%2201985f23-1d19-7f6f-b8ef-35c3e5791d56%22%2C1753942793497%5D%7D; "
    "_authToken=%7B%22address%22%3A%220xf2d5b0668e805aaa6c0f61ef4b1f168011bfd9e2%22%2C%22signature%22%3A%220x3659218a2da5eb50084ba6594a11db28c710e4b8056b087ff66dd69081c3111b74c12e52271994ca019c0524091adc55439ab9f0b264594e05ad3837624c24121c%22%2C%22nonce%22%3A%22yqQiJHwF%22%2C%22expired%22%3A1768300272.7709258%7D; "
    "JSESSIONID=6E6A8F4230621E2B142B4DDF0B43FB93"
)

def cookie_str_to_dict(cookie_str):
    d = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            d[k] = v
    return d

cookies = cookie_str_to_dict(cookie_string)

####################
### 爬虫超参数设置 ###
####################

# 赛季阶段
era = "RARE"

# 活跃用户阈值，10m代表上次完成rank mode的时间在10分钟以内的则判断为当前在线玩家
active_threshold = timeparse('10m')

###############
### 运行爬虫 ###
###############

active_dic = {}
# 查询前100个玩家（2页，每页50人）
for i in tqdm(range(1,3)):
    # 获取axie top leaderboard网页代码
    url = f"https://axie.top/leaderboard/filter?page={i}&eraFilter={era}"
    with requests.Session() as request:
        request.headers.update(headers)
        request.cookies.update(cookies)
        
        html = request.get(url).text
        soup = BeautifulSoup(html, "lxml")

    # 找到当前页面所有玩家，数量应当为50
    players = soup.find_all('a', class_='leaderboard-unit')

    # 遍历玩家
    for player in players:
        # 找到该玩家上次rank mode完赛时间
        last_ranked_string = player.find('div', class_='last-played-ago').find_all('span')[1].text
        last_ranked_time = timeparse(last_ranked_string)

        # 若上次完赛时间小于阈值，则开始获取玩家队伍信息
        if (last_ranked_time < active_threshold):
            # 获得玩家排名以及经游戏昵称
            player_info = player.find_all('span', class_='liquid-font')
            player_rank = player_info[0].text
            player_name = player_info[1].text
            player_dic_value = {"rank": player_rank, "name": player_name}

            # 获得玩家游戏id
            profile_href = player.get("href")
            uuid = re.search(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", profile_href)
            player_id = uuid.group()

            # 获取玩家队伍信息网站代码
            url = f"https://axie.top/premium/profile/{player_id}/teamAnalytics"
            with requests.Session() as request:
                request.headers.update(headers)
                request.cookies.update(cookies)
                
                html = request.get(url).text
                soup1 = BeautifulSoup(html, "lxml")

            # 获取最新的队伍信息
            teams = soup1.find_all("div", class_="analytics-team-row")
            latest_team = teams[0].find_all("p")[-1].text

            if latest_team in active_dic:
                active_dic[latest_team].append(player_dic_value)
            else:
                active_dic[latest_team] = [player_dic_value]

# 打印当前在线玩家结果
for team in active_dic.keys():
    print(f"队伍: {team}, 当前在线人数: {len(active_dic[team])}")
