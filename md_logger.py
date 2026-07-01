"""Markdown 操作记录模块，将每一步操作追加写入 .md 表格文件。"""

import os
from datetime import datetime


class MdLogger:
    def __init__(self, filepath):
        self.filepath = filepath
        self._started_at = None
        self._action_count = 0

        # 确保目录存在
        dirpath = os.path.dirname(filepath)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)

        # 首次创建时写入表头
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# 操作记录\n\n")
                f.write(f"> 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("| 时间 | 操作类型 | 操作详情 | 置信度 |\n")
                f.write("|------|---------|---------|--------|\n")

    def log(self, action_type, detail, confidence=None):
        """记录一步操作。"""
        now = datetime.now().strftime("%H:%M:%S")
        if self._started_at is None:
            self._started_at = datetime.now()

        conf_str = f"{confidence:.2f}" if confidence is not None else "-"
        line = f"| {now} | {action_type} | {detail} | {conf_str} |\n"

        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(line)

        self._action_count += 1

    def close(self):
        """追加总结行。"""
        if self._started_at is None:
            return

        duration = (datetime.now() - self._started_at).total_seconds()
        m, s = divmod(int(duration), 60)
        dur_str = f"{m}分{s}秒" if m > 0 else f"{s}秒"

        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(f"\n> 共操作 {self._action_count} 步，耗时 {dur_str}\n")
