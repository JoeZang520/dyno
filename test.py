import cv2
import pyautogui
import numpy as np
import os
import time
import time
from libs.window_gpm import GpmWindow
from libs.task_helper import TaskHelper
import sys
from libs.config import is_axie_pal_enabled, get_account, is_clay_enabled, is_sand_enabled, is_copper_enabled
from selenium.webdriver.common.action_chains import ActionChains
import random

# 全局变量，用于记住每个用户找到的axie图片
user_axie_images = {}

def get_user_delay_config(user_id):
    """获取用户特定的延迟配置"""
    account = get_account(user_id)
    
    # 获取延迟时间（分钟），默认40分钟
    delay_minutes = account.get('delay_minutes', 40)
    
    return delay_minutes

def timer(seconds, activity_name="等待"):
    for remaining in range(seconds, -1, -1):
        print(f"\r{activity_name}: {remaining} 秒", end="")  # 显示倒计时在同一行
        time.sleep(1)  # 等待 1 秒
    print(f"\n")  # 换行并打印结束信息


def image(png, threshold=0.85, region=None, offset=(0, 0), click_times=1, color=True, gray_diff_threshold=15):
    # 自动添加 .png 扩展名
    if not png.endswith('.png'):
        png += '.png'
    
    # 获取当前截图并转换为 numpy 数组
    screenshot_data = driver.get_screenshot_as_png()
    screenshot = cv2.imdecode(np.frombuffer(screenshot_data, np.uint8), -1)

    # 如果提供了特定的区域，裁剪截图
    if region is not None:
        x, y, w, h = region
        screenshot = screenshot[y:y + h, x:x + w]

    # 获取目标图像的路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(current_dir, 'pic', png)
    
    # 检查文件是否存在
    if not os.path.exists(target_path):
        print(f"[WARN] 图片文件不存在: {target_path}")
        return None
    
    target = cv2.imread(target_path)
    
    # 检查图片是否成功加载
    if target is None:
        print(f"[WARN] 无法加载图片文件: {target_path}")
        return None

    if color:
        # 彩色匹配
        result = cv2.matchTemplate(screenshot, target, cv2.TM_CCOEFF_NORMED)
    else:
        # 灰度匹配
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, target_gray, cv2.TM_CCOEFF_NORMED)

    # 获取最大匹配值
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    locations = np.where(result >= threshold)

    # 如果找到目标，返回第一个目标位置
    if locations[0].size > 0:
        x, y = locations[1][0], locations[0][0]
        
        # 如果是彩色匹配，检查颜色是否太灰
        if color:
            # 提取匹配区域
            match_area = screenshot[
                y:y + target.shape[0],
                x:x + target.shape[1]
            ]
            
            # 计算RGB通道之间的差异
            diff_rg = np.abs(match_area[:, :, 2] - match_area[:, :, 1])
            diff_rb = np.abs(match_area[:, :, 2] - match_area[:, :, 0])
            diff_gb = np.abs(match_area[:, :, 1] - match_area[:, :, 0])
            mean_diff = np.mean((diff_rg + diff_rb + diff_gb) / 3.0)

            if mean_diff < gray_diff_threshold:
                print(f"[FAIL] {png} 匹配区域颜色太灰（均差≈{mean_diff:.2f}），未识别出图片")
                return None
            # else:
            #     print(f"[SUCCESS] {png} 匹配区域颜色合适（均差≈{mean_diff:.2f}）")
        
        # 计算最终点击位置（考虑偏移量）
        final_x = x + offset[0]
        final_y = y + offset[1]
        
        # 如果提供了区域，需要加上区域的偏移
        if region is not None:
            final_x += region[0]
            final_y += region[1]
        
        # print(f"找到'{png}'，位置: ({x}, {y})，匹配度: {max_val:.3f} (阈值: {threshold})")
        
        # 如果设置了点击次数，执行点击操作
        if click_times > 0:
            for _ in range(click_times):
                click(final_x, final_y)
                time.sleep(1)  # 短暂延迟避免点击过快
            print(f"找到'{png}'，({x}, {y})，{max_val:.3f}，点击 {click_times} 次")
        
        return (final_x, final_y)  # 返回最终点击位置

    print(f"未找到'{png}'，最大匹配度: {max_val:.3f} (阈值: {threshold})")
    return None  # 如果没有找到目标，返回 None

thresholds = {
    "craft": 0.9
}
def image_multi(png_list, thresholds=thresholds, region=None, min_x_distance=40, min_y_distance=40, click_times=0,
                excluded_points=None, color=True, gray_diff_threshold=20):
    """使用网页内截图进行多图片查找，支持彩色匹配和灰度检测，能查找同一模板的多个匹配位置"""
    if isinstance(png_list, str):
        png_list = [png_list]

    if not thresholds:
        raise ValueError("阈值字典 (thresholds) 必须提供")

    results = {}
    all_found_points = []  # 存储所有找到的点，用于去重

    def is_far_enough(cx, cy, points, min_dx, min_dy):
        for px, py, _ in points:
            if abs(cx - px) < min_dx and abs(cy - py) < min_dy:
                return False
        if excluded_points:
            for ex, ey in excluded_points:
                if abs(cx - ex) < min_dx and abs(cy - ey) < min_dy:
                    return False
        return True

    for picture in png_list:
        # 查找所有相关的图片文件
        templates = []
        
        # 查找完全匹配的文件
        exact_match = f"{picture}.png"
        if os.path.exists(os.path.join('pic', exact_match)):
            templates.append(exact_match)
        
        # 查找以picture_开头的文件
        for file in os.listdir('pic'):
            if file.startswith(f"{picture}_") and file.endswith('.png'):
                templates.append(file)

        if not templates:
            print(f"[ERROR] 未找到任何图片：{picture}.png 或 {picture}_*.png")
            results[picture] = []
            continue

        threshold = thresholds.get(picture)
        if threshold is None:
            print(f"[WARN] 图片 {picture} 没有设置阈值，跳过该角色")
            continue

        picture_points = []
        
        for template_file in templates:
            # 直接在这里实现多匹配查找，不使用单独的image函数
            # 获取当前截图并转换为 numpy 数组
            screenshot_data = driver.get_screenshot_as_png()
            screenshot = cv2.imdecode(np.frombuffer(screenshot_data, np.uint8), -1)

            # 如果提供了特定的区域，裁剪截图
            if region is not None:
                x, y, w, h = region
                screenshot = screenshot[y:y + h, x:x + w]

            # 获取目标图像的路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            target_path = os.path.join(current_dir, 'pic', template_file)
            
            # 检查文件是否存在
            if not os.path.exists(target_path):
                print(f"[WARN] 图片文件不存在: {target_path}")
                continue
            
            target = cv2.imread(target_path)
            
            # 检查图片是否成功加载
            if target is None:
                print(f"[WARN] 无法加载图片文件: {target_path}")
                continue

            if color:
                # 彩色匹配
                result = cv2.matchTemplate(screenshot, target, cv2.TM_CCOEFF_NORMED)
            else:
                # 灰度匹配
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
                result = cv2.matchTemplate(screenshot_gray, target_gray, cv2.TM_CCOEFF_NORMED)

            # 找到所有匹配位置
            locations = np.where(result >= threshold)
            
            if locations[0].size > 0:
                h, w = target.shape[:2]
                
                for pt in zip(*locations[::-1]):
                    x, y = pt[0], pt[1]
                    
                    # 如果是彩色匹配，先检查颜色是否太灰，再决定是否处理
                    if color:
                        # 提取匹配区域
                        match_area = screenshot[y:y + h, x:x + w]
                        
                        # 计算RGB通道之间的差异
                        diff_rg = np.abs(match_area[:, :, 2] - match_area[:, :, 1])
                        diff_rb = np.abs(match_area[:, :, 2] - match_area[:, :, 0])
                        diff_gb = np.abs(match_area[:, :, 1] - match_area[:, :, 0])
                        mean_diff = np.mean((diff_rg + diff_rb + diff_gb) / 3.0)

                        if mean_diff < gray_diff_threshold:
                            print(f"[SKIP] 跳过灰色匹配: ({x}, {y}), 颜色差异: {mean_diff:.2f} < {gray_diff_threshold}")
                            continue  # 跳过颜色太灰的匹配
                        # else:
                        #     print(f"[PASS] 通过颜色检测: ({x}, {y}), 颜色差异: {mean_diff:.2f} >= {gray_diff_threshold}")
                    
                    # 计算最终位置（考虑区域偏移）
                    final_x = x + w // 2
                    final_y = y + h // 2
                    
                    if region is not None:
                        final_x += region[0]
                        final_y += region[1]
                    
                    # 获取匹配度
                    score = result[y, x]
                    
                    # 检查是否与已找到的点距离足够远
                    if is_far_enough(final_x, final_y, all_found_points, min_x_distance, min_y_distance):
                        picture_points.append((final_x, final_y, score))
                        all_found_points.append((final_x, final_y, score))
                        # print(f"[DEBUG] 找到匹配点: ({final_x}, {final_y}), 匹配度: {score:.3f}, 图片: {template_file}")
                    # else:
                    #     print(f"[SKIP] 跳过距离太近的匹配: ({final_x}, {final_y})")

        results[picture] = picture_points

    # 点击第一个找到的点（如果设置了click_times）
    if click_times > 0 and all_found_points:
        first_point = all_found_points[0]
        cx, cy = first_point[0], first_point[1]
        print(f"[INFO] 点击匹配点：({cx}, {cy})")
        pyautogui.click(cx, cy)
        time.sleep(1)

    return results


def loading(image_names, check_interval: float = 1, threshold=0.85, gray_diff_threshold=12, offset=(0, 0), click_times=1, timeout=45):
    """循环检测任意一张指定图片出现，返回True或False"""
    start_time = time.time()
    print(f"正在加载 {image_names} ... ")

    while True:
        for image_name in image_names:
            pos = image(image_name, threshold=threshold, gray_diff_threshold=gray_diff_threshold, offset=offset, click_times=click_times, color=True)
            if pos is not None:
                # print(f"找到 {image_names}")        
                return image_name

        if timeout and (time.time() - start_time) > timeout:
            print(f"加载 {image_names} 超时")
            return None

        time.sleep(check_interval)

def press(key):
    print(f"[按键] : {key}")
    
    # 键名映射 - 将简化名称映射到标准名称
    key_mapping = {
        'Right': 'ArrowRight',
        'Left': 'ArrowLeft', 
        'Up': 'ArrowUp',
        'Down': 'ArrowDown'
    }
    
    # 定义键码映射
    key_codes = {
        'ArrowRight': 39,
        'ArrowLeft': 37,
        'ArrowUp': 38,
        'ArrowDown': 40,
        'Enter': 13,
        'Space': 32,
        'Tab': 9,
        'Escape': 27
    }
    
    # 获取实际的键名和键码
    actual_key = key_mapping.get(key, key)
    key_code = key_codes.get(actual_key, ord(key) if len(key) == 1 else 0)
    
    print(f"[调试] 实际键名: {actual_key}, 键码: {key_code}")
    
    script = f"""
    console.log('发送按键事件:', '{actual_key}', {key_code});
    
    var keyEvent = function(eventType, key) {{
        var event = new KeyboardEvent(eventType, {{
            bubbles: true,
            cancelable: true,
            key: '{actual_key}',
            code: '{actual_key}',
            keyCode: {key_code},
            which: {key_code}
        }});
        console.log('触发事件:', eventType, event);
        document.dispatchEvent(event);
    }};

    keyEvent('keydown', '{actual_key}');
    keyEvent('keypress', '{actual_key}');
    keyEvent('keyup', '{actual_key}');
    """
    
    try:
        driver.execute_script(script)
        print(f"[成功] 按键事件已发送: {actual_key}")
    except Exception as e:
        print(f"[错误] 发送按键事件失败: {e}")


def click(offset_x, offset_y):
    ac = ActionChains(driver)
    ac.reset_actions()
    ac.move_by_offset(offset_x, offset_y).click().perform()


def drag(start_x, start_y, distance=300, duration=1.0, hold_at_end=0):
    """在指定坐标按住鼠标左键，拖动指定距离，然后松开左键
    distance为正数向上拖动，为负数向下拖动
    hold_at_end为在拖拽终点停留的时间（秒）"""
    try:
        ac = ActionChains(driver)
        ac.reset_actions()
        
        # 固定步数，确保每次操作一致
        if duration <= 0.5:
            steps = 1  # 快速拖拽
        else:
            steps = 3  # 慢速拖拽
        
        step_distance = distance / steps
        step_delay = duration / steps  # 平均分配时间，确保总时间准确
        
        # 移动到起始位置并按下鼠标
        ac.move_by_offset(start_x, start_y).click_and_hold()
        
        # 分步移动，使用更短的延迟
        for i in range(steps):
            ac.move_by_offset(0, -step_distance)  # 负号表示向上，正distance时向上，负distance时向下
            if i < steps - 1:  # 最后一步不需要延迟
                ac.pause(step_delay)
        
        # 在终点停留指定时间
        if hold_at_end > 0:
            ac.pause(hold_at_end)
        
        # 松开鼠标
        ac.release().perform()
        
        direction = "向上" if distance > 0 else "向下"
        hold_info = f"，在终点停留{hold_at_end}秒" if hold_at_end > 0 else ""
        print(f"在坐标({start_x}, {start_y}){direction}拖动{abs(distance)}像素，耗时{duration:.2f}秒{hold_info}")
        
    except Exception as e:
        # 捕获拖拽超出屏幕界限等错误，记录但不中断脚本
        direction = "向上" if distance > 0 else "向下"
        print(f"[警告] 拖拽操作失败，坐标({start_x}, {start_y}){direction}拖动{abs(distance)}像素: {str(e)}")
        print("[INFO] 继续执行后续操作...")


def perform_axie_drag(user_id):
    """执行axie图片拖拽的完整流程"""
    global user_axie_images
    
    # 检查是否已经为这个用户找到了可用的图片
    if user_id in user_axie_images:
        # 使用之前找到的图片对应的 left 和 right 图片
        base_img = user_axie_images[user_id]
        print(f"[INFO] 用户ID {user_id} 使用已找到的图片组: {base_img}")
        
        # 生成对应的 left 和 right 图片名称
        left_img = f"{base_img}_left"
        right_img = f"{base_img}_right"
        
        # 优先尝试之前找到的那张图片，然后尝试另一张
        # 需要从全局变量中获取之前找到的具体图片名称
        if hasattr(perform_axie_drag, 'last_found_img') and user_id in perform_axie_drag.last_found_img:
            last_img = perform_axie_drag.last_found_img[user_id]
            if last_img == left_img:
                target_imgs = [left_img, right_img]  # 优先尝试 left
            else:
                target_imgs = [right_img, left_img]  # 优先尝试 right
        else:
            # 如果没有记录，随机选择
            target_imgs = [left_img, right_img]
            random.shuffle(target_imgs)
        
        for axie_img in target_imgs:
            axie_pos = image(axie_img, threshold=0.75, click_times=0)
            if axie_pos:
                print(f"找到图片: {axie_img}")
                # 记录这次找到的图片
                if not hasattr(perform_axie_drag, 'last_found_img'):
                    perform_axie_drag.last_found_img = {}
                perform_axie_drag.last_found_img[user_id] = axie_img
                
                random_distance = random.randint(100, 400)
                random_duration = round(random.uniform(0.1, 1), 2)
                drag(axie_pos[0], axie_pos[1], random_distance, random_duration, 0.2)
                return True
        
        # 如果 left 和 right 都找不到，直接返回失败
        print(f"[WARN] 图片组 {base_img} 的所有变体都找不到了，继续尝试...")
        return False
    
    # 首次搜索或重新搜索
    if user_id == 1:
        axie_images = ['user1_1_left', 'user1_1_right', 'user1_2_left', 'user1_2_right', 'user1_3_left', 'user1_3_right']
    elif user_id == 2:
        axie_images = ['user2_1_left', 'user2_1_right', 'user2_2_left', 'user2_2_right', 'user2_3_left', 'user2_3_right']
    else:
        axie_images = []
    
    print(f"[INFO] 用户ID {user_id} 搜索axie图片: {axie_images}")
    axie_pos = None
    
    for axie_img in axie_images:
        axie_pos = image(axie_img, threshold=0.75, click_times=0)
        if axie_pos:
            print(f"找到图片: {axie_img}")
            # 记住这个用户找到的图片（保存基础名称，不包含 _left 或 _right）
            base_name = axie_img.replace('_left', '').replace('_right', '')
            user_axie_images[user_id] = base_name
            
            # 记录这次找到的具体图片名称
            if not hasattr(perform_axie_drag, 'last_found_img'):
                perform_axie_drag.last_found_img = {}
            perform_axie_drag.last_found_img[user_id] = axie_img
            break
    
    if axie_pos:
        random_distance = random.randint(100, 400)
        random_duration = round(random.uniform(0.1, 1), 2)
        drag(axie_pos[0], axie_pos[1], random_distance, random_duration, 0.2)
        return True
    else:
        print("未找到任何axie图片")
        return False

def in_game():
    try:
        # 检查tree图片
        if image('tree', threshold=0.7, click_times=0) is not None:
            print("[INFO] 找到tree图片，确认在游戏中")
            return True
        
        print("[INFO] 未找到tree，不在游戏中")
        return False
    except Exception as e:
        print(f"[ERROR] 检查游戏状态时发生异常: {str(e)[:100]}...")
        return False
    
def enter_game():  
    print("[INFO] 检查是否已在游戏中...")
    try:
        if in_game():
            print("[INFO] 已在游戏中，无需重新加载")
            return True           
    except Exception as e:
        print(f"[ERROR] 进入游戏时发生异常: {str(e)[:100]}...")
        return False


def craft(region=None):
    """使用 image_multi 找到所有 craft 目标并对每个点击一次，避免重复点击"""
    print("[INFO] 开始查找craft图片...")

    results = image_multi(['craft'], click_times=0, region=region)
    points = results.get('craft', []) if isinstance(results, dict) else []

    if not points:
        print("[INFO] 未找到任何craft图片")
        return

    print(f"[SUCCESS] 找到 {len(points)} 个craft图片，将依次点击")
    for i, (x, y, score) in enumerate(points, start=1):
        print(f"  - 点击 {i}: ({x}, {y}), 匹配度: {score:.3f}")
        click(x, y)
        time.sleep(0.5)


def switch_axie():
    # 点击profile按钮
    image('profile')
    time.sleep(2)
    
    # 查找当前axie（根据用户ID确定要查找的axie图片）
    current_axie = None
    if user_id == 1:
        axie_images = ['user1_1_left', 'user1_1_right', 'user1_2_left', 'user1_2_right', 'user1_3_left', 'user1_3_right']
    elif user_id == 2:
        axie_images = ['user2_1_left', 'user2_1_right', 'user2_2_left', 'user2_2_right', 'user2_3_left', 'user2_3_right']
    else:
        axie_images = []
    
    for axie_img in axie_images:
        if image(axie_img, threshold=0.75, click_times=0):
            current_axie = axie_img
            print(f"[INFO] 找到当前axie: {current_axie}")
            break
    
    if current_axie:
        # 根据用户ID和当前axie确定下一个axie
        if user_id == 1:
            next_axie_map = {
                'user1_1_left': 'user1_2',
                'user1_1_right': 'user1_2', 
                'user1_2_left': 'user1_3',
                'user1_2_right': 'user1_3',
                'user1_3_left': 'user1_1',
                'user1_3_right': 'user1_1'
            }
        elif user_id == 2:
            next_axie_map = {
                'user2_1_left': 'user2_2',
                'user2_1_right': 'user2_2',
                'user2_2_left': 'user2_3', 
                'user2_2_right': 'user2_3',
                'user2_3_left': 'user2_1',
                'user2_3_right': 'user2_1'
            }
        else:
            next_axie_map = {}
        
        next_axie = next_axie_map.get(current_axie)
        if next_axie:
            print(f"[INFO] 切换到下一个axie: {next_axie}")
            # 点击下一个axie的base_image
            image(next_axie)
            time.sleep(1)
            # 点击apply按钮
            image('apply')
            time.sleep(2)
            image('x_profile')
            print(f"[INFO] axie切换完成")
            timer(5, "等待5秒")
        else:
            print(f"[WARN] 未找到对应的下一个axie")
    else:
        print(f"[WARN] 未找到当前axie")


def axie_pal():
    # 检查是否启用了axie_pal功能
    if not is_axie_pal_enabled(user_id):
        print(f"[INFO] 用户ID {user_id} 的axie_pal功能已禁用，跳过执行")
        return
    image('okay')
    
    if image('setting', offset=(-290, -30)):
        time.sleep(3)
    if image('call'):
        timer(8, "等待axie出现")
    if image('full', threshold=0.95, click_times=0):
        print(f"[INFO] axie经验已满，开始切换axie")
        switch_axie()   
    
    if image('setting', offset=(-290, -30)):
        time.sleep(3)
    if image('call'):
        timer(8, "等待axie出现")
    if image('full', threshold=0.95, click_times=0):
        print(f"[INFO] axie经验已满，开始切换axie")
        switch_axie()

    if image('setting', offset=(-290, -30)):
        time.sleep(3)
    if image('call'):
        timer(8, "等待axie出现")
    if image('full', threshold=0.95, click_times=0):
        print(f"[INFO] 第3只axie经验已满，退出axie pal")
        return

    successful_drags = 0
    attempt_count = 0
    consecutive_failures = 0  # 连续失败次数
    
    max_attempts = 110  # 最大尝试次数
    while successful_drags < 100 and attempt_count < max_attempts:
        attempt_count += 1
        print(f"\n=== 第 {attempt_count} 次尝试，已成功拖拽 {successful_drags} 次 ===")
        success = perform_axie_drag(user_id)
        if success:
            successful_drags += 1
            consecutive_failures = 0  # 重置连续失败计数
            print(f"[成功] 第 {successful_drags} 次拖拽完成")
            time.sleep(1)
        else:
            consecutive_failures += 1
            print(f"拖拽失败，连续失败 {consecutive_failures} 次...")
            
            # 如果前5次都失败，执行dismiss和call操作
            if consecutive_failures == 3:
                print("[INFO] 连续失败3次，尝试重新召唤axie...")
                if image('setting', offset=(-290, -30)):
                    time.sleep(3)
                if image('dismiss', color=False):
                    time.sleep(3)
                if image('setting', offset=(-290, -30)):
                    time.sleep(3)
                if image('call'):
                    timer(8, "等待axie出现")                      
                
                consecutive_failures = 0  # 重置连续失败计数
            
            time.sleep(2)  # 失败后等待更长时间
    
    if attempt_count >= max_attempts:
        print(f"[警告] 已达到最大尝试次数 {max_attempts}，实际成功拖拽 {successful_drags} 次")
        
    
if __name__ == "__main__":
        user_id = 1  # 调试用固定值
    
    
   
    
        driver = GpmWindow(user_id).open(False)

        
        enter_game()


        
        print(f"[INFO] dyno脚本执行完成，用户ID: {user_id}, 开始执行axie pal")

        axie_pal()
        
       
       
        
       



    
   


