"""御魂副本自动化状态机，支持队长/队员双模式。"""

import time
import random
from enum import Enum

from config import (
    SCAN_INTERVAL,
    CLICK_DELAY,
    CLICK_INTERVAL,
    DEFAULT_CONFIDENCE,
    ANTI_DETECT,
    SPIRIT_FLOOR_NUM,
    SPIRIT_ROUNDS,
    SPIRIT_MODE,
)


class SpiritHubState(Enum):
    IDLE = "空闲"
    ENTER_SPIRIT = "进入御魂"
    SELECT_FLOOR = "选择层数"
    LEADER_CREATE = "队长创建队伍"
    LEADER_WAIT = "队长等待队友"
    MEMBER_JOIN = "队员加入队伍"
    MEMBER_READY = "队员准备"
    IN_DUNGEON = "战斗中"
    CLEAR_WAVE = "清波次"
    LOOT = "捡物"
    RETURN = "返回主城"
    ERROR = "错误"


class StopReason(Enum):
    NONE = "无"
    USER_STOP = "用户停止"
    MAX_ROUNDS = "达到最大次数"


class SpiritHubBot:
    def __init__(self, window_manager, image_recognition, auto_clicker, md_logger=None):
        self.window_manager = window_manager
        self.image_recognition = image_recognition
        self.auto_clicker = auto_clicker
        self.md_logger = md_logger

        self.state = SpiritHubState.IDLE
        self.running = False
        self.thread = None
        self.stop_event = None

        self.log_callback = None
        self.state_callback = None

        self.round_count = 0
        self.retry_count = 0

        self.max_rounds = SPIRIT_ROUNDS
        self.floor_num = SPIRIT_FLOOR_NUM
        self.party_mode = "leader"  # "leader" 或 "member"
        self.stop_reason = StopReason.NONE

        self.start_time = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def set_state_callback(self, callback):
        self.state_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        if self.md_logger:
            self.md_logger.log("日志", message)

    def _md_log(self, action_type, detail, confidence=None):
        """通过 MdLogger 记录一步操作。"""
        if self.md_logger:
            self.md_logger.log(action_type, detail, confidence)

    def set_state(self, state):
        self.state = state
        if self.state_callback:
            self.state_callback(state.value)

    def set_params(self, floor_num=SPIRIT_FLOOR_NUM, rounds=SPIRIT_ROUNDS, mode="leader"):
        self.floor_num = floor_num
        self.max_rounds = rounds
        self.party_mode = mode

    def start(self):
        if self.running:
            return False

        if not self.window_manager.find_window():
            self.log("未找到阴阳师游戏窗口！")
            return False

        self.running = True
        self.stop_event = threading.Event()
        self.stop_event.clear()
        self.round_count = 0
        self.retry_count = 0
        self.stop_reason = StopReason.NONE
        self.start_time = time.time()

        self.set_state(SpiritHubState.ENTER_SPIRIT)
        self.log("御魂副本自动化已启动")
        self.log(f"模式: {self.party_mode} | 层数: {self.floor_num} | 次数: {self.max_rounds}")

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self, reason=StopReason.USER_STOP):
        if not self.running:
            return

        self.running = False
        self.stop_reason = reason
        self.stop_event.set()
        self.set_state(SpiritHubState.IDLE)
        self.log(f"御魂自动化已停止（{reason.value}）")

    def _check_stop_conditions(self):
        if self.max_rounds > 0 and self.round_count >= self.max_rounds:
            self.stop(StopReason.MAX_ROUNDS)
            return True
        return False

    def _run_loop(self):
        import threading
        screenshot_failures = 0
        while not self.stop_event.is_set():
            try:
                if self._check_stop_conditions():
                    break

                self.window_manager.update_window_rect()
                screen = self.window_manager.screenshot()

                if screen is None:
                    screenshot_failures += 1
                    if screenshot_failures >= 5:
                        self.log("截图连续失败，尝试重新查找游戏窗口...")
                        if self.window_manager.find_window():
                            self.log("成功重新找到游戏窗口")
                            screenshot_failures = 0
                        else:
                            self.log("无法找到游戏窗口，挂机已暂停")
                            self.stop_event.wait(min(SCAN_INTERVAL * 10, 30))
                            continue
                    else:
                        self.log(f"截图失败 ({screenshot_failures}/5)，重试中...")
                    time.sleep(SCAN_INTERVAL)
                    continue

                screenshot_failures = 0
                self._process_state(screen)

            except Exception as e:
                self.log(f"发生错误: {str(e)}")
                self.set_state(SpiritHubState.ERROR)
                time.sleep(SCAN_INTERVAL)

            jitter = random.uniform(
                -ANTI_DETECT['scan_interval_jitter'],
                ANTI_DETECT['scan_interval_jitter']
            )
            interval = max(0.5, SCAN_INTERVAL + jitter)
            if self.stop_event.wait(interval):
                break

    def _process_state(self, screen):
        handlers = {
            SpiritHubState.ENTER_SPIRIT: self._handle_enter_spirit,
            SpiritHubState.SELECT_FLOOR: self._handle_select_floor,
            SpiritHubState.LEADER_CREATE: self._handle_leader_create,
            SpiritHubState.LEADER_WAIT: self._handle_leader_wait,
            SpiritHubState.MEMBER_JOIN: self._handle_member_join,
            SpiritHubState.MEMBER_READY: self._handle_member_ready,
            SpiritHubState.IN_DUNGEON: self._handle_in_dungeon,
            SpiritHubState.CLEAR_WAVE: self._handle_clear_wave,
            SpiritHubState.LOOT: self._handle_loot,
            SpiritHubState.RETURN: self._handle_return,
        }
        handler = handlers.get(self.state)
        if handler:
            handler(screen)

    def _enter_spirit_dungeon(self, screen):
        """找御魂入口按钮并点击进入。"""
        # 御魂入口通常在大地图或功能菜单中，这里用通用方式：点击屏幕固定区域
        w, h = self.window_manager.get_window_size()
        # 尝试找"御魂"文字按钮（可用模板匹配，暂时用坐标）
        spirit_x = int(w * 0.75)
        spirit_y = int(h * 0.35)
        self.log(f"点击御魂入口 ({spirit_x}, {spirit_y})")
        self.auto_clicker.click(spirit_x, spirit_y)
        self._md_log("点击", "进入御魂副本入口")
        time.sleep(1.0)
        return True

    def _select_floor(self, screen):
        """选择层数。1-9层直接点击，10-15层需要先下滑滚动才能看到。"""
        w, h = self.window_manager.get_window_size()

        if self.floor_num <= 9:
            # 1-9层：直接点击右侧对应位置
            floor_x = int(w * 0.82)
            floor_y = int(h * 0.15 + (self.floor_num - 1) * (h * 0.07))
            self.log(f"选择{self.floor_num}层 ({floor_x}, {floor_y})")
            self.auto_clicker.click(floor_x, floor_y)
            self._md_log("选择", f"选择{self.floor_num}层")
        else:
            # 10-15层：先下滑滚动露出高层，再点击
            scroll_start_y = int(h * 0.82)
            scroll_distance = int(h * 0.35)
            self.log(f"下滑滚动以显示{self.floor_num}层")
            self.auto_clicker.drag_up(scroll_start_y, scroll_start_y, distance=scroll_distance, duration=0.8)
            time.sleep(0.8)

            # 滚动后再点击对应位置（10-15层的索引偏移）
            adjusted_floor = self.floor_num - 9  # 10->1, 11->2...15->6
            floor_x = int(w * 0.82)
            floor_y = int(h * 0.15 + (adjusted_floor - 1) * (h * 0.07))
            self.log(f"选择{self.floor_num}层 ({floor_x}, {floor_y})")
            self.auto_clicker.click(floor_x, floor_y)
            self._md_log("选择", f"下滑后选择{self.floor_num}层")

        time.sleep(0.5)
        return True

    def _handle_enter_spirit(self, screen):
        self._enter_spirit_dungeon(screen)
        self.set_state(SpiritHubState.SELECT_FLOOR)

    def _handle_select_floor(self, screen):
        self._select_floor(screen)
        if self.party_mode == "leader":
            self.set_state(SpiritHubState.LEADER_CREATE)
        else:
            self.set_state(SpiritHubState.MEMBER_JOIN)

    def _handle_leader_create(self, screen):
        """队长：创建队伍并等待队友。"""
        # 找"创建队伍"或"开始游戏"按钮
        create_btn = self.image_recognition.find_template(
            screen, 'spirit_confirm', confidence=DEFAULT_CONFIDENCE
        )
        if create_btn:
            self.log("找到确认按钮，创建队伍")
            self.auto_clicker.click_match_result(create_btn)
            self._md_log("点击", "创建队伍")
            time.sleep(1.0)
            self.set_state(SpiritHubState.LEADER_WAIT)
            return

        # 超时未找到，尝试点击固定位置
        w, h = self.window_manager.get_window_size()
        create_x, create_y = int(w * 0.75), int(h * 0.85)
        self.log(f"点击创建队伍 ({create_x}, {create_y})")
        self.auto_clicker.click(create_x, create_y)
        self._md_log("点击", "创建队伍（坐标）")
        time.sleep(1.0)
        self.set_state(SpiritHubState.LEADER_WAIT)

    def _handle_leader_wait(self, screen):
        """队长：等待队友加入。"""
        ready_btn = self.image_recognition.find_template(
            screen, 'spirit_ready', confidence=DEFAULT_CONFIDENCE
        )
        if ready_btn:
            self.log("检测到队友已就绪")
            self.set_state(SpiritHubState.IN_DUNGEON)
            return

        start_btn = self.image_recognition.find_template(
            screen, 'spirit_start', confidence=DEFAULT_CONFIDENCE
        )
        if start_btn:
            self.log("开始进攻！")
            self.auto_clicker.click_match_result(start_btn)
            self._md_log("点击", "队长发起进攻")
            time.sleep(1.5)
            self.set_state(SpiritHubState.IN_DUNGEON)
            return

        self.retry_count += 1
        if self.retry_count >= 30:
            self.log("等待队友超时，强制开始")
            self.retry_count = 0
            self.set_state(SpiritHubState.IN_DUNGEON)

    def _handle_member_join(self, screen):
        """队员：加入队伍。"""
        join_btn = self.image_recognition.find_template(
            screen, 'spirit_confirm', confidence=DEFAULT_CONFIDENCE
        )
        if join_btn:
            self.log("找到加入按钮，加入队伍")
            self.auto_clicker.click_match_result(join_btn)
            self._md_log("点击", "加入队伍")
            time.sleep(1.0)
            self.set_state(SpiritHubState.MEMBER_READY)
            return

        # 尝试点击加入按钮固定位置
        w, h = self.window_manager.get_window_size()
        join_x, join_y = int(w * 0.75), int(h * 0.85)
        self.auto_clicker.click(join_x, join_y)
        self._md_log("点击", "加入队伍（坐标）")
        time.sleep(1.0)
        self.set_state(SpiritHubState.MEMBER_READY)

    def _handle_member_ready(self, screen):
        """队员：等待队长开始，自动准备。"""
        ready_btn = self.image_recognition.find_template(
            screen, 'spirit_ready', confidence=DEFAULT_CONFIDENCE
        )
        if ready_btn:
            self.log("找到准备按钮")
            self.auto_clicker.click_match_result(ready_btn)
            self._md_log("点击", "队员准备")
            time.sleep(0.5)

        start_btn = self.image_recognition.find_template(
            screen, 'spirit_start', confidence=DEFAULT_CONFIDENCE
        )
        if start_btn:
            self.log("队长已开始进攻，进入战斗")
            time.sleep(1.5)
            self.set_state(SpiritHubState.IN_DUNGEON)
            return

        self.retry_count += 1
        if self.retry_count >= 30:
            self.log("等待超时，尝试进入战斗")
            self.retry_count = 0
            self.set_state(SpiritHubState.IN_DUNGEON)

    def _handle_in_dungeon(self, screen):
        """战斗中：找"手动"按钮开启自动作战。"""
        manual_result = self.image_recognition.find_template(
            screen, 'manual', confidence=DEFAULT_CONFIDENCE
        )
        if manual_result:
            self.log(f"找到'手动'按钮，开启自动作战")
            self.auto_clicker.click_match_result(manual_result)
            self._md_log("点击", "开启自动作战")
            time.sleep(2.0)
            self.retry_count = 0
            self.set_state(SpiritHubState.CLEAR_WAVE)
            return

        self.retry_count += 1
        if self.retry_count >= 5:
            self.log("未找到'手动'按钮，可能已开启自动")
            self.retry_count = 0
            self.set_state(SpiritHubState.CLEAR_WAVE)

    def _handle_clear_wave(self, screen):
        """清波次：等当前波次怪物全部清除。"""
        # 检测是否有"下一波"或"继续"按钮
        next_wave = self.image_recognition.find_template(
            screen, 'spirit_confirm', confidence=DEFAULT_CONFIDENCE
        )
        if next_wave:
            self.log("当前波次已清除，点击继续")
            self.auto_clicker.click_match_result(next_wave)
            self._md_log("点击", "进入下一波")
            time.sleep(2.0)
            self.retry_count = 0
            self.set_state(SpiritHubState.IN_DUNGEON)
            return

        self.retry_count += 1
        if self.retry_count >= 15:
            self.log("波次检测超时，进入捡物阶段")
            self.retry_count = 0
            self.set_state(SpiritHubState.LOOT)

    def _handle_loot(self, screen):
        """捡物：点击掉落物位置。"""
        w, h = self.window_manager.get_window_size()
        loot_x = int(w * 0.5)
        loot_y = int(h * 0.5)
        self.log(f"点击拾取掉落物 ({loot_x}, {loot_y})")
        self.auto_clicker.click(loot_x, loot_y, random_offset=False, smooth_move=False)
        self._md_log("点击", "拾取掉落物")
        time.sleep(1.0)
        self.set_state(SpiritHubState.RETURN)

    def _handle_return(self, screen):
        """返回主城，完成一轮。"""
        # 找退出/返回按钮
        exit_btn = self.image_recognition.find_template(
            screen, 'spirit_confirm', confidence=DEFAULT_CONFIDENCE
        )
        if exit_btn:
            self.log("找到退出按钮，返回主城")
            self.auto_clicker.click_match_result(exit_btn)
            self._md_log("点击", "返回主城")
            time.sleep(1.5)
            self.round_count += 1
            self.log(f"已完成 {self.round_count}/{self.max_rounds} 轮")
            self.retry_count = 0
            self.set_state(SpiritHubState.ENTER_SPIRIT)
            return

        # 超时未找到，强制进入下一轮
        self.retry_count += 1
        if self.retry_count >= 10:
            self.log("返回超时，强制进入下一轮")
            self.round_count += 1
            self.log(f"已完成 {self.round_count}/{self.max_rounds} 轮")
            self._md_log("返回", f"第{self.round_count}轮完成")
            self.retry_count = 0
            self.set_state(SpiritHubState.ENTER_SPIRIT)
