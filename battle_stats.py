import json
import os
import time
from datetime import datetime, date

from config import STATS_FILE


class BattleStats:
    def __init__(self):
        self.total_wins = 0
        self.total_losses = 0
        self.session_wins = 0
        self.session_losses = 0
        self.session_start_time = None
        self.battle_start_time = None
        self.total_battle_time = 0
        self.shortest_battle = None
        self.longest_battle = None
        self.load()

    def load(self):
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.total_wins = data.get('total_wins', 0)
                self.total_losses = data.get('total_losses', 0)
                self.total_battle_time = data.get('total_battle_time', 0)
        except:
            pass

    def save(self):
        try:
            data = {
                'total_wins': self.total_wins,
                'total_losses': self.total_losses,
                'total_battle_time': self.total_battle_time,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def start_session(self):
        self.session_wins = 0
        self.session_losses = 0
        self.session_start_time = time.time()

    def end_session(self):
        self.save()

    def start_battle(self):
        self.battle_start_time = time.time()

    def end_battle(self, is_victory):
        if self.battle_start_time:
            battle_duration = time.time() - self.battle_start_time
            self.total_battle_time += battle_duration

            if self.shortest_battle is None or battle_duration < self.shortest_battle:
                self.shortest_battle = battle_duration
            if self.longest_battle is None or battle_duration > self.longest_battle:
                self.longest_battle = battle_duration

            self.battle_start_time = None

        if is_victory:
            self.total_wins += 1
            self.session_wins += 1
        else:
            self.total_losses += 1
            self.session_losses += 1

        self.save()

    @property
    def total_battles(self):
        return self.total_wins + self.total_losses

    @property
    def session_battles(self):
        return self.session_wins + self.session_losses

    @property
    def total_win_rate(self):
        if self.total_battles == 0:
            return 0.0
        return self.total_wins / self.total_battles * 100

    @property
    def session_win_rate(self):
        if self.session_battles == 0:
            return 0.0
        return self.session_wins / self.session_battles * 100

    @property
    def session_duration(self):
        if self.session_start_time is None:
            return 0
        return time.time() - self.session_start_time

    @property
    def avg_battle_time(self):
        if self.total_battles == 0:
            return 0
        return self.total_battle_time / self.total_battles

    def get_summary(self):
        def format_time(seconds):
            if seconds is None or seconds == 0:
                return "0秒"
            m, s = divmod(int(seconds), 60)
            if m == 0:
                return f"{s}秒"
            h, m = divmod(m, 60)
            if h == 0:
                return f"{m}分{s}秒"
            return f"{h}时{m}分{s}秒"

        return {
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'total_battles': self.total_battles,
            'total_win_rate': self.total_win_rate,
            'session_wins': self.session_wins,
            'session_losses': self.session_losses,
            'session_battles': self.session_battles,
            'session_win_rate': self.session_win_rate,
            'session_duration': format_time(self.session_duration),
            'total_battle_time': format_time(self.total_battle_time),
            'avg_battle_time': format_time(self.avg_battle_time),
        }

    def reset_session(self):
        self.session_wins = 0
        self.session_losses = 0
        self.session_start_time = time.time()
        self.battle_start_time = None
