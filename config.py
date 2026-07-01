import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

WINDOW_TITLE_KEYWORDS = ['阴阳师', 'onmyoji']
WINDOW_PROCESS_NAMES = ['onmyoji.exe', 'netease games', '阴阳师']

# 模拟器扩展关键词（用于宽松匹配，覆盖常见模拟器进程/窗口名）
EMULATOR_TITLE_KEYWORDS = ['阴阳师', 'onmyoji', 'MuMu', '网易MuMu', '雷电', 'Nox', '夜神', '蓝叠', 'BlueStacks', '模拟器', '安卓']
EMULATOR_PROCESS_NAMES = ['onmyoji.exe', 'netease games', '阴阳师', 'noremu.exe', 'momu.exe', 'mumu.exe', 'nox.exe', 'noxupdater.exe', 'bshaper.exe', 'stacks.exe', 'hypervisor.exe', 'nox_android.exe', 'android_turing.exe', 'android_boot_service.exe']

MIN_WINDOW_WIDTH = 600
MIN_WINDOW_HEIGHT = 400

DEFAULT_CONFIDENCE = 0.8
SCAN_INTERVAL = 1.0
CLICK_DELAY = 0.5

TEMPLATES = {
    'battle_button': 'battle_button.png',
    'confirm': 'confirm.png',
    'manual': 'manual.png',
    'victory': 'victory.png',
    'defeat': 'defeat.png',
    'search_button': 'search_button.png',
    # 御魂副本模板
    'spirit_entry': 'spirit_entry.png',
    'spirit_confirm': 'spirit_confirm.png',
    'spirit_ready': 'spirit_ready.png',
    'spirit_start': 'spirit_start.png',
}

# 御魂副本默认配置
SPIRIT_FLOOR_NUM = 8       # 默认刷的层数（1-15）
SPIRIT_ROUNDS = 10         # 默认刷的次数

REGIONS = {
    'battle_button': None,
    'confirm': None,
    'manual': None,
}

MAX_RETRIES = 10
CLICK_INTERVAL = 2.0

HOTKEY_TOGGLE = 'f6'

ANTI_DETECT = {
    'click_offset_range': 8,
    'click_duration_min': 0.08,
    'click_duration_max': 0.15,
    'post_click_delay_min': 0.3,
    'post_click_delay_max': 0.8,
    'mouse_move_steps': 20,
    'mouse_move_duration': 0.3,
    'scan_interval_jitter': 0.3,
}

STATS_FILE = 'stats.json'
