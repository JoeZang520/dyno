## 脚本使用说明

### 安装扩展
```
#selenium
pip install selenium

# cv2
pip install opencv-python

# psutil
pip install psutil

# requests
pip install requests
```

## 任务说明

### farm.py
```
# 脚本使用前置条件
# 1. 收藏土地 4972, 818
```


## TODO
[x] 处理进入游戏失败，enter_game加重试机制或者wait_page_load增加超时时间  
[x] farm.py 根据配置和库存自动决定种什么  
[ ] charge他saona结束后直接去种地，不要再关闭一次浏览器？
[x] 根据持有金币数量判断刷任务的cost_limit  
[x] saona.py体力满了就结束运行,或者在运行前判断体力大于700就先去种地  
[x] trade.py偶尔无法走到商店上方  
[x] trade.py 未查到价格的，下次要重新查  
[x] 已有的物品交任务前也要计算价值超值的不交, 注意JAVA BEAN的处理  
[ ] get_backpack偶尔异常导致程序退出  
[x] 检查是否正常进入818，不正常就返回主城重新进  
[x] p_orders日志优化  
[ ] snapshot记录每个账号每天启动次数，方便问题排查   
[ ] 统一定义退出游戏的逻辑，方便控制是否关闭浏览器  
[x] 增加cooking逻辑  
[x] 种子最大数量在配置里定义(先统一改成300个)
[ ] 从泉水去商店，去除对818的依赖  
[x] trade.py对物品价格进行缓存，减少搜索查询次数



## TEMP

```

```