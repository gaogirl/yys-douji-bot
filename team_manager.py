import json
import os

TEAMS_FILE = 'teams.json'


class TeamManager:
    def __init__(self):
        self.teams = []
        self.current_team_index = 0
        self.load()

    def load(self):
        try:
            if os.path.exists(TEAMS_FILE):
                with open(TEAMS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.teams = data.get('teams', [])
                self.current_team_index = data.get('current_index', 0)
                if not self.teams:
                    self._create_default_teams()
            else:
                self._create_default_teams()
        except:
            self._create_default_teams()

    def save(self):
        try:
            data = {
                'teams': self.teams,
                'current_index': self.current_team_index,
            }
            with open(TEAMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _create_default_teams(self):
        self.teams = [
            {
                'name': '默认阵容1',
                'shikigami': ['', '', '', '', ''],
                'onmyouji': '',
                'enabled': True,
            },
            {
                'name': '默认阵容2',
                'shikigami': ['', '', '', '', ''],
                'onmyouji': '',
                'enabled': False,
            },
            {
                'name': '默认阵容3',
                'shikigami': ['', '', '', '', ''],
                'onmyouji': '',
                'enabled': False,
            },
        ]
        self.current_team_index = 0
        self.save()

    def get_current_team(self):
        if 0 <= self.current_team_index < len(self.teams):
            return self.teams[self.current_team_index]
        return None

    def set_current_team(self, index):
        if 0 <= index < len(self.teams):
            self.current_team_index = index
            self.save()
            return True
        return False

    def get_team(self, index):
        if 0 <= index < len(self.teams):
            return self.teams[index]
        return None

    def update_team(self, index, name=None, shikigami=None, onmyouji=None, enabled=None):
        if 0 <= index < len(self.teams):
            if name is not None:
                self.teams[index]['name'] = name
            if shikigami is not None:
                self.teams[index]['shikigami'] = shikigami
            if onmyouji is not None:
                self.teams[index]['onmyouji'] = onmyouji
            if enabled is not None:
                self.teams[index]['enabled'] = enabled
            self.save()
            return True
        return False

    def add_team(self, name='新阵容'):
        self.teams.append({
            'name': name,
            'shikigami': ['', '', '', '', ''],
            'onmyouji': '',
            'enabled': True,
        })
        self.save()
        return len(self.teams) - 1

    def remove_team(self, index):
        if len(self.teams) <= 1:
            return False
        if 0 <= index < len(self.teams):
            del self.teams[index]
            if self.current_team_index >= len(self.teams):
                self.current_team_index = len(self.teams) - 1
            self.save()
            return True
        return False

    def get_enabled_teams(self):
        return [(i, t) for i, t in enumerate(self.teams) if t.get('enabled', True)]

    def next_team(self):
        enabled = self.get_enabled_teams()
        if not enabled:
            return None

        current_found = False
        for i, (idx, team) in enumerate(enabled):
            if idx == self.current_team_index:
                if i < len(enabled) - 1:
                    next_idx = enabled[i + 1][0]
                else:
                    next_idx = enabled[0][0]
                self.current_team_index = next_idx
                current_found = True
                break

        if not current_found:
            self.current_team_index = enabled[0][0]

        self.save()
        return self.get_current_team()

    def get_team_count(self):
        return len(self.teams)
