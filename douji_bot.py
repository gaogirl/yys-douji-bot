import time
import threading
import random
from enum import Enum

from config import (
    SCAN_INTERVAL,
    CLICK_DELAY,
    CLICK_INTERVAL,
    DEFAULT_CONFIDENCE,
    ANTI_DETECT,
)


class DoujiState(Enum):
    IDLE = "空闲"
    FIND_MATCH = "寻找匹配"
    SELECTING = "选人/等待"
    AUTO_SELECT = "自动选人"
    IN_BATTLE = "战斗中"
    BATTLE_END = "结算中"
    ERROR = "错误"


class StopReason(Enum):
    NONE = "无"
    USER_STOP = "用户停止"
    MAX_BATTLES = "达到最大场次"
    MAX_MINUTES = "达到最大时长"


class DoujiBot:
    def __init__(self, window_manager, image_recognition, auto_clicker, stats=None,
                 selection_handler=None, team_manager=None, md_logger=None):
        self.window_manager = window_manager
        self.image_recognition = image_recognition
        self.auto_clicker = auto_clicker
        self.stats = stats
        self.selection_handler = selection_handler
        self.team_manager = team_manager
        self.md_logger = md_logger

        self.state = DoujiState.IDLE
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()

        self.log_callback = None
        self.state_callback = None
        self.stats_callback = None

        self.battle_count = 0
        self.retry_count = 0

        self.max_battles = 0
        self.max_minutes = 0
        self.stop_reason = StopReason.NONE

        self.start_time = None

        self.auto_select = False
        self.rotate_team = False
        self.rotate_every = 1
        self.rotate_on_loss = False

        self._selecting_done = False

    def set_log_callback(self, callback):
        self.log_callback = callback

    def set_state_callback(self, callback):
        self.state_callback = callback

    def set_stats_callback(self, callback):
        self.stats_callback = callback

    def set_limits(self, max_battles=0, max_minutes=0):
        self.max_battles = max_battles
        self.max_minutes = max_minutes

    def set_auto_select(self, enabled=False):
        self.auto_select = enabled

    def set_team_rotate(self, enabled=False, every=1, on_loss=False):
        self.rotate_team = enabled
        self.rotate_every = max(1, every)
        self.rotate_on_loss = on_loss

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def _md_log(self, action_type, detail, confidence=None):
        """通过 MdLogger 记录一步操作。"""
        if self.md_logger:
            self.md_logger.log(action_type, detail, confidence)

    def set_state(self, state):
        self.state = state
        if self.state_callback:
            self.state_callback(state.value)

    def _update_stats(self):
        if self.stats_callback and self.stats:
            self.stats_callback(self.stats.get_summary())

    def start(self, max_battles=0, max_minutes=0):
        if self.running:
            return False

        if not self.window_manager.find_window():
            self.log("未找到阴阳师游戏窗口！")
            return False

        self.running = True
        self.stop_event.clear()
        self.battle_count = 0
        self.retry_count = 0
        self.max_battles = max_battles
        self.max_minutes = max_minutes
        self.stop_reason = StopReason.NONE
        self.start_time = time.time()

        if self.stats:
            self.stats.start_session()

        self.set_state(DoujiState.FIND_MATCH)
        self.log("斗技自动挂机已启动")

        if self.max_battles > 0:
            self.log(f"设置: 最多打 {self.max_battles} 场")
        if self.max_minutes > 0:
            self.log(f"设置: 最多挂 {self.max_minutes} 分钟")

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self, reason=StopReason.USER_STOP):
        if not self.running:
            return

        self.running = False
        self.stop_reason = reason
        self.stop_event.set()
        self.set_state(DoujiState.IDLE)

        if self.stats:
            self.stats.end_session()

        self.log(f"斗技自动挂机已停止（{reason.value}）")

    def _check_stop_conditions(self):
        if self.max_battles > 0 and self.battle_count >= self.max_battles:
            self.stop(StopReason.MAX_BATTLES)
            return True

        if self.max_minutes > 0 and self.start_time:
            elapsed = (time.time() - self.start_time) / 60
            if elapsed >= self.max_minutes:
                self.stop(StopReason.MAX_MINUTES)
                return True

        return False

    def _run_loop(self):
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
                self._update_stats()

            except Exception as e:
                self.log(f"发生错误: {str(e)}")
                self.set_state(DoujiState.ERROR)
                time.sleep(SCAN_INTERVAL)

            jitter = random.uniform(
                -ANTI_DETECT['scan_interval_jitter'],
                ANTI_DETECT['scan_interval_jitter']
            )
            interval = max(0.5, SCAN_INTERVAL + jitter)
            if self.stop_event.wait(interval):
                break

    def _get_screen_center(self, screen):
        h, w = screen.shape[:2]
        return w // 2, h // 2

    def _process_state(self, screen):
        if self.state == DoujiState.FIND_MATCH:
            self._handle_find_match(screen)
        elif self.state == DoujiState.SELECTING:
            self._handle_selecting(screen)
        elif self.state == DoujiState.AUTO_SELECT:
            self._handle_auto_select(screen)
        elif self.state == DoujiState.IN_BATTLE:
            self._handle_in_battle(screen)
        elif self.state == DoujiState.BATTLE_END:
            self._handle_battle_end(screen)

    def _handle_find_match(self, screen):
        battle_btn = self.image_recognition.find_template(
            screen, 'battle_button', confidence=DEFAULT_CONFIDENCE
        )

        if battle_btn:
            self.log(f"找到'战'按钮，置信度: {battle_btn['confidence']:.2f}")
            self.auto_clicker.click_match_result(battle_btn)
            self._md_log("点击", "进入斗技匹配", battle_btn['confidence'])
            self.retry_count = 0
            self._selecting_done = False
            self.set_state(DoujiState.SELECTING)
            self.log("已点击'战'，进入选人/等待阶段...")
        else:
            self.retry_count += 1
            if self.retry_count >= 30:
                self.log("⚠ 已超过30秒未找到'战'按钮，请确保在斗技匹配界面")
                self.retry_count = 0

    def _handle_selecting(self, screen):
        manual_result = self.image_recognition.find_template(
            screen, 'manual', confidence=DEFAULT_CONFIDENCE
        )

        if manual_result:
            self.log("匹配完成，进入战斗界面")
            self.set_state(DoujiState.IN_BATTLE)
            return

        confirm_result = self.image_recognition.find_template(
            screen, 'confirm', confidence=DEFAULT_CONFIDENCE
        )

        if confirm_result:
            if self.auto_select and not self._selecting_done:
                self.set_state(DoujiState.AUTO_SELECT)
                return

            self.log(f"找到'确定'按钮，置信度: {confirm_result['confidence']:.2f}")
            self.auto_clicker.click_match_result(confirm_result)
            self._md_log("点击", "斗技确认", confirm_result['confidence'])
            self.log("已点击'确定'，等待对手...")
            time.sleep(CLICK_INTERVAL)
        else:
            self.log("等待选人/对手确认...")

    def _handle_auto_select(self, screen):
        if not self.selection_handler or not self.team_manager:
            self.log("选人模块未初始化，跳过自动选人")
            self._selecting_done = True
            self.set_state(DoujiState.SELECTING)
            return

        team = self.team_manager.get_current_team()
        if not team:
            self.log("当前阵容为空，跳过自动选人")
            self._selecting_done = True
            self.set_state(DoujiState.SELECTING)
            return

        team_name = team.get('name', '未知')
        self.log(f"使用阵容: {team_name}")

        success = self.selection_handler.select_team(team, log_callback=self.log)

        if success:
            self.log("自动选人完成")
        else:
            self.log("自动选人可能未完成，请检查")

        self._selecting_done = True
        time.sleep(1)
        self.set_state(DoujiState.SELECTING)

    def _handle_in_battle(self, screen):
        manual_result = self.image_recognition.find_template(
            screen, 'manual', confidence=DEFAULT_CONFIDENCE
        )

        if manual_result:
            self.log(f"找到'手动'按钮，置信度: {manual_result['confidence']:.2f}")
            self.auto_clicker.click_match_result(manual_result)
            self.log("已点击'手动'开启自动作战")
            self._md_log("点击", "开启自动作战", manual_result['confidence'])

            if self.stats:
                self.stats.start_battle()

            self.battle_count += 1
            self.log(f"当前战斗场次: {self.battle_count}")
            self.set_state(DoujiState.BATTLE_END)
            self.retry_count = 0
        else:
            self.retry_count += 1
            if self.retry_count >= 5:
                self.log("未找到'手动'按钮，可能已开启自动，进入结算等待...")
                if self.stats:
                    self.stats.start_battle()
                self.set_state(DoujiState.BATTLE_END)
                self.retry_count = 0

    def _dismiss_settlement(self, screen):
        """查找并点击结算画面上的胜利/失败按钮，返回结果类型。"""
        victory_result = self.image_recognition.find_template(
            screen, 'victory', confidence=DEFAULT_CONFIDENCE
        )
        if victory_result:
            self.log(f"找到'胜利'按钮，置信度: {victory_result['confidence']:.2f}")
            self.auto_clicker.click_match_result(victory_result)
            return 'victory'

        defeat_result = self.image_recognition.find_template(
            screen, 'defeat', confidence=DEFAULT_CONFIDENCE
        )
        if defeat_result:
            self.log(f"找到'失败'按钮，置信度: {defeat_result['confidence']:.2f}")
            self.auto_clicker.click_match_result(defeat_result)
            return 'defeat'

        return None

    def _handle_battle_end(self, screen):
        # ① 先尝试识别结算画面（胜利/失败按钮）
        result = self._dismiss_settlement(screen)
        if result:
            is_victory = (result == 'victory')

            if self.stats and self.stats.battle_start_time:
                self.stats.end_battle(is_victory)

            if result == 'victory':
                self.log("战斗胜利！")
                self._md_log("结算", "战斗胜利", 0.95)
            else:
                self.log("战斗失败")
                self._md_log("结算", "战斗失败", 0.95)

            self._maybe_rotate_team(is_victory)
            self._update_stats()
            self.set_state(DoujiState.FIND_MATCH)
            return

        # ② 结算画面没找到 → 检查是否已经回到匹配界面（有战按钮）
        battle_btn = self.image_recognition.find_template(
            screen, 'battle_button', confidence=DEFAULT_CONFIDENCE
        )
        if battle_btn:
            # 可能跳过了结算画面（快速自动跳转），仍记录胜负
            if self.stats and self.stats.battle_start_time:
                self.stats.end_battle(None)  # 未知结果
            self.log("检测到已回到匹配界面（结算画面可能已跳过）")
            self._update_stats()
            self.set_state(DoujiState.FIND_MATCH)
            return

        # ③ 都不是 → 点击屏幕中央跳过可能的中间画面
        cx, cy = self._get_screen_center(screen)
        self.log("结算中... 点击屏幕中央跳过")
        self.auto_clicker.click(cx, cy)
        time.sleep(CLICK_INTERVAL)

    def _maybe_rotate_team(self, is_victory):
        if not self.rotate_team or not self.team_manager:
            return

        should_rotate = False
        reason = ""

        if self.rotate_on_loss and not is_victory:
            should_rotate = True
            reason = "战败轮换"
        elif not self.rotate_on_loss and self.battle_count > 0 and self.battle_count % self.rotate_every == 0:
            should_rotate = True
            reason = f"每{self.rotate_every}场轮换"

        if should_rotate:
            next_team = self.team_manager.next_team()
            if next_team:
                self.log(f"阵容轮换 - {reason}: {next_team.get('name', '未知')}")
