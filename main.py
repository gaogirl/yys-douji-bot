import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
from datetime import datetime

from window_manager import WindowManager
from image_recognition import ImageRecognition
from auto_clicker import AutoClicker
from douji_bot import DoujiBot
from battle_stats import BattleStats
from hotkey_manager import GlobalHotkey
from tray_manager import SystemTray
from team_manager import TeamManager
from selection_handler import SelectionHandler
from config import HOTKEY_TOGGLE, DEFAULT_CONFIDENCE


class DoujiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("阴阳师斗技自动挂机")
        self.root.geometry("580x820")
        self.root.resizable(False, False)

        self.window_manager = WindowManager()
        self.image_recognition = ImageRecognition()
        self.auto_clicker = AutoClicker(self.window_manager)
        self.stats = BattleStats()
        self.team_manager = TeamManager()
        self.selection_handler = SelectionHandler(
            self.window_manager, self.image_recognition, self.auto_clicker
        )
        self.bot = DoujiBot(
            self.window_manager,
            self.image_recognition,
            self.auto_clicker,
            self.stats,
            self.selection_handler,
            self.team_manager,
        )
        self.hotkey = GlobalHotkey()
        self.tray = None

        self.bot.set_log_callback(self._append_log)
        self.bot.set_state_callback(self._update_state)
        self.bot.set_stats_callback(self._update_stats_display)

        self.confidence_var = tk.DoubleVar(value=DEFAULT_CONFIDENCE)
        self.max_battles_var = tk.StringVar(value="0")
        self.max_minutes_var = tk.StringVar(value="0")

        self.auto_select_var = tk.BooleanVar(value=False)
        self.rotate_team_var = tk.BooleanVar(value=False)
        self.rotate_every_var = tk.StringVar(value="3")
        self.rotate_on_loss_var = tk.BooleanVar(value=False)
        self.current_team_var = tk.StringVar(value="")

        self._create_widgets()
        self._setup_tray()
        self._setup_hotkey()
        self._check_templates()
        self._refresh_team_list()
        self._update_stats_display(self.stats.get_summary())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="阴阳师斗技自动挂机",
            font=("Microsoft YaHei", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        status_frame = ttk.LabelFrame(main_frame, text="运行状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 8))

        self.state_var = tk.StringVar(value="空闲")
        state_label = ttk.Label(status_frame, text="当前状态:")
        state_label.grid(row=0, column=0, sticky=tk.W)
        self.state_value = ttk.Label(
            status_frame,
            textvariable=self.state_var,
            foreground="blue",
            font=("Microsoft YaHei", 10, "bold")
        )
        self.state_value.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        self.battle_count_var = tk.StringVar(value="0")
        count_label = ttk.Label(status_frame, text="本次场次:")
        count_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.count_value = ttk.Label(
            status_frame,
            textvariable=self.battle_count_var,
            foreground="green",
            font=("Microsoft YaHei", 10, "bold")
        )
        self.count_value.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))

        win_label = ttk.Label(status_frame, text="胜:")
        win_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.win_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.win_var, foreground="green").grid(
            row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))

        lose_label = ttk.Label(status_frame, text="负:")
        lose_label.grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=(5, 0))
        self.lose_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.lose_var, foreground="red").grid(
            row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 0))

        rate_label = ttk.Label(status_frame, text="胜率:")
        rate_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.rate_var = tk.StringVar(value="0%")
        ttk.Label(status_frame, textvariable=self.rate_var, foreground="orange").grid(
            row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))

        dur_label = ttk.Label(status_frame, text="时长:")
        dur_label.grid(row=2, column=2, sticky=tk.W, padx=(20, 0), pady=(5, 0))
        self.dur_var = tk.StringVar(value="0秒")
        ttk.Label(status_frame, textvariable=self.dur_var).grid(
            row=2, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 8))

        self.start_button = ttk.Button(
            button_frame,
            text="开始挂机 (F6)",
            command=self._start_bot,
            width=18
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_button = ttk.Button(
            button_frame,
            text="停止挂机 (F6)",
            command=self._stop_bot,
            width=18,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT)

        self.tray_button = ttk.Button(
            button_frame,
            text="最小化到托盘",
            command=self._hide_to_tray,
            width=18
        )
        self.tray_button.pack(side=tk.RIGHT)

        tool_frame = ttk.Frame(main_frame)
        tool_frame.pack(fill=tk.X, pady=(0, 8))

        self.detect_button = ttk.Button(
            tool_frame,
            text="检测游戏窗口",
            command=self._detect_window,
            width=14
        )
        self.detect_button.pack(side=tk.LEFT, padx=(0, 8))

        self.template_button = ttk.Button(
            tool_frame,
            text="打开模板目录",
            command=self._open_template_dir,
            width=14
        )
        self.template_button.pack(side=tk.LEFT)

        self.reset_stats_btn = ttk.Button(
            tool_frame,
            text="重置统计",
            command=self._reset_stats,
            width=14
        )
        self.reset_stats_btn.pack(side=tk.RIGHT)

        settings_frame = ttk.LabelFrame(main_frame, text="挂机设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 8))

        conf_frame = ttk.Frame(settings_frame)
        conf_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(conf_frame, text="识别灵敏度:").pack(side=tk.LEFT)
        self.conf_scale = ttk.Scale(
            conf_frame,
            from_=0.5,
            to=0.99,
            orient=tk.HORIZONTAL,
            variable=self.confidence_var,
            command=self._on_confidence_change,
            length=200
        )
        self.conf_scale.pack(side=tk.LEFT, padx=(10, 10))
        self.conf_label = ttk.Label(conf_frame, text=f"{DEFAULT_CONFIDENCE:.2f}")
        self.conf_label.pack(side=tk.LEFT)

        limit_frame = ttk.Frame(settings_frame)
        limit_frame.pack(fill=tk.X)

        ttk.Label(limit_frame, text="最多场次:").pack(side=tk.LEFT)
        self.battles_entry = ttk.Entry(
            limit_frame,
            textvariable=self.max_battles_var,
            width=8
        )
        self.battles_entry.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(limit_frame, text="(0=不限制)").pack(side=tk.LEFT)

        ttk.Label(limit_frame, text="最长分钟:").pack(side=tk.LEFT, padx=(20, 0))
        self.minutes_entry = ttk.Entry(
            limit_frame,
            textvariable=self.max_minutes_var,
            width=8
        )
        self.minutes_entry.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(limit_frame, text="(0=不限制)").pack(side=tk.LEFT)

        team_frame = ttk.LabelFrame(main_frame, text="阵容设置", padding="10")
        team_frame.pack(fill=tk.X, pady=(0, 8))

        auto_sel_row = ttk.Frame(team_frame)
        auto_sel_row.pack(fill=tk.X, pady=(0, 6))
        self.auto_select_check = ttk.Checkbutton(
            auto_sel_row,
            text="启用自动选人",
            variable=self.auto_select_var,
        )
        self.auto_select_check.pack(side=tk.LEFT)

        team_row = ttk.Frame(team_frame)
        team_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(team_row, text="当前阵容:").pack(side=tk.LEFT)
        self.team_combo = ttk.Combobox(
            team_row,
            textvariable=self.current_team_var,
            state="readonly",
            width=15
        )
        self.team_combo.pack(side=tk.LEFT, padx=(8, 8))
        self.team_combo.bind("<<ComboboxSelected>>", self._on_team_select)
        self.edit_team_btn = ttk.Button(
            team_row,
            text="编辑阵容",
            command=self._edit_team,
            width=10
        )
        self.edit_team_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.add_team_btn = ttk.Button(
            team_row,
            text="新增",
            command=self._add_team,
            width=6
        )
        self.add_team_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.del_team_btn = ttk.Button(
            team_row,
            text="删除",
            command=self._delete_team,
            width=6
        )
        self.del_team_btn.pack(side=tk.LEFT)

        rotate_row = ttk.Frame(team_frame)
        rotate_row.pack(fill=tk.X)
        self.rotate_check = ttk.Checkbutton(
            rotate_row,
            text="阵容轮换",
            variable=self.rotate_team_var,
        )
        self.rotate_check.pack(side=tk.LEFT)
        ttk.Label(rotate_row, text="每").pack(side=tk.LEFT, padx=(10, 0))
        self.rotate_every_entry = ttk.Entry(
            rotate_row,
            textvariable=self.rotate_every_var,
            width=5
        )
        self.rotate_every_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Label(rotate_row, text="场换一套").pack(side=tk.LEFT)
        self.rotate_loss_check = ttk.Checkbutton(
            rotate_row,
            text="仅战败时换",
            variable=self.rotate_on_loss_var,
        )
        self.rotate_loss_check.pack(side=tk.LEFT, padx=(15, 0))

        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=("Consolas", 9),
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        tip_label = ttk.Label(
            main_frame,
            text=f"提示: 全局热键 F6 一键启停 | 关闭窗口自动缩到托盘",
            foreground="gray",
            font=("Microsoft YaHei", 9)
        )
        tip_label.pack(pady=(8, 0))

    def _setup_tray(self):
        try:
            self.tray = SystemTray(
                self.root,
                on_show=self._show_from_tray,
                on_quit=self._quit_app
            )
            self.tray.start()
        except Exception as e:
            self._append_log(f"托盘功能初始化失败: {str(e)}")

    def _setup_hotkey(self):
        self.hotkey.register(HOTKEY_TOGGLE, self._toggle_bot)
        self.hotkey.start()

    def _toggle_bot(self):
        if self.bot.running:
            self.root.after(0, self._stop_bot)
        else:
            self.root.after(0, self._start_bot)

    def _on_close(self):
        if self.tray:
            self._append_log("窗口已最小化到托盘，右键托盘图标可退出")
            self.tray.hide_to_tray()
        else:
            self._quit_app()

    def _hide_to_tray(self):
        if self.tray:
            self.tray.hide_to_tray()
            self._append_log("已最小化到托盘")

    def _show_from_tray(self):
        if self.tray:
            self.tray.show_from_tray()

    def _quit_app(self):
        try:
            self.bot.stop()
        except:
            pass
        try:
            self.hotkey.stop()
        except:
            pass
        try:
            if self.tray:
                self.tray.stop()
        except:
            pass
        self.root.quit()
        self.root.destroy()

    def _on_confidence_change(self, value):
        val = float(value)
        self.conf_label.config(text=f"{val:.2f}")

    def _check_templates(self):
        from config import TEMPLATES
        missing = []
        for name, filename in TEMPLATES.items():
            if name in ['victory', 'defeat']:
                continue
            if not self.image_recognition.has_template(name):
                missing.append(filename)

        if missing:
            self._append_log(f"警告: 缺少以下模板图片: {', '.join(missing)}")
            self._append_log("请将模板截图放入 templates 文件夹")
        else:
            self._append_log("核心模板图片加载成功")

    def _detect_window(self):
        if self.window_manager.find_window():
            info = self.window_manager.get_window_info()
            self._append_log(f"找到游戏窗口！标题: {info['title']}")
            self._append_log(f"进程: {info['process']} | 大小: {info['size'][0]} x {info['size'][1]}")
        else:
            self._append_log("未找到阴阳师游戏窗口，请先启动游戏")
            messagebox.showwarning("提示", "未找到阴阳师游戏窗口\n\n请确保：\n1. 已启动阴阳师游戏客户端\n2. 游戏窗口处于可见状态")

    def _start_bot(self):
        try:
            max_battles = int(self.max_battles_var.get() or 0)
        except ValueError:
            max_battles = 0

        try:
            max_minutes = int(self.max_minutes_var.get() or 0)
        except ValueError:
            max_minutes = 0

        confidence = self.confidence_var.get()

        from config import DEFAULT_CONFIDENCE
        import config
        config.DEFAULT_CONFIDENCE = confidence

        auto_select = self.auto_select_var.get()
        rotate_team = self.rotate_team_var.get()
        try:
            rotate_every = int(self.rotate_every_var.get() or 3)
        except ValueError:
            rotate_every = 3
        rotate_on_loss = self.rotate_on_loss_var.get()

        self.bot.set_auto_select(auto_select)
        self.bot.set_team_rotate(rotate_team, every=rotate_every, on_loss=rotate_on_loss)

        success = self.bot.start(max_battles=max_battles, max_minutes=max_minutes)
        if success:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.detect_button.config(state=tk.DISABLED)
            self.auto_select_check.config(state=tk.DISABLED)
            self.rotate_check.config(state=tk.DISABLED)
            self.rotate_every_entry.config(state=tk.DISABLED)
            self.rotate_loss_check.config(state=tk.DISABLED)
            self.team_combo.config(state=tk.DISABLED)
            self.edit_team_btn.config(state=tk.DISABLED)
            self.add_team_btn.config(state=tk.DISABLED)
            self.del_team_btn.config(state=tk.DISABLED)

    def _stop_bot(self):
        self.bot.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.detect_button.config(state=tk.NORMAL)
        self.auto_select_check.config(state=tk.NORMAL)
        self.rotate_check.config(state=tk.NORMAL)
        self.rotate_every_entry.config(state=tk.NORMAL)
        self.rotate_loss_check.config(state=tk.NORMAL)
        self.team_combo.config(state="readonly")
        self.edit_team_btn.config(state=tk.NORMAL)
        self.add_team_btn.config(state=tk.NORMAL)
        self.del_team_btn.config(state=tk.NORMAL)

    def _reset_stats(self):
        if messagebox.askyesno("确认", "确定要重置本次统计数据吗？"):
            self.stats.reset_session()
            self._update_stats_display(self.stats.get_summary())
            self._append_log("统计数据已重置")

    def _append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_line)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        self.root.after(0, _append)

    def _update_state(self, state):
        def _update():
            self.state_var.set(state)
            self.battle_count_var.set(str(self.bot.battle_count))

        self.root.after(0, _update)

    def _update_stats_display(self, stats_summary):
        def _update():
            self.win_var.set(str(stats_summary['session_wins']))
            self.lose_var.set(str(stats_summary['session_losses']))
            self.rate_var.set(f"{stats_summary['session_win_rate']:.1f}%")
            self.dur_var.set(stats_summary['session_duration'])

        self.root.after(0, _update)

    def _refresh_team_list(self):
        teams = []
        for i in range(self.team_manager.get_team_count()):
            team = self.team_manager.get_team(i)
            if team:
                prefix = "✓ " if team.get('enabled', True) else "✗ "
                teams.append(prefix + team.get('name', f'阵容{i+1}'))
        self.team_combo['values'] = teams
        current_idx = self.team_manager.current_team_index
        if 0 <= current_idx < len(teams):
            self.team_combo.current(current_idx)

    def _on_team_select(self, event=None):
        idx = self.team_combo.current()
        if idx >= 0:
            self.team_manager.set_current_team(idx)
            team = self.team_manager.get_current_team()
            if team:
                self._append_log(f"已选择阵容: {team.get('name', '未知')}")

    def _add_team(self):
        idx = self.team_manager.add_team()
        self._refresh_team_list()
        self.team_manager.set_current_team(idx)
        self._refresh_team_list()
        self._append_log(f"已新增阵容")
        self._edit_team()

    def _delete_team(self):
        idx = self.team_combo.current()
        if idx < 0:
            return
        if self.team_manager.get_team_count() <= 1:
            messagebox.showinfo("提示", "至少保留一套阵容")
            return
        team = self.team_manager.get_team(idx)
        name = team.get('name', '该阵容') if team else '该阵容'
        if messagebox.askyesno("确认", f"确定要删除「{name}」吗？"):
            self.team_manager.remove_team(idx)
            self._refresh_team_list()
            self._append_log(f"已删除阵容: {name}")

    def _edit_team(self):
        idx = self.team_combo.current()
        if idx < 0:
            idx = self.team_manager.current_team_index
        team = self.team_manager.get_team(idx)
        if not team:
            return

        editor = tk.Toplevel(self.root)
        editor.title("编辑阵容")
        editor.geometry("400x380")
        editor.resizable(False, False)
        editor.transient(self.root)
        editor.grab_set()

        frm = ttk.Frame(editor, padding="15")
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="阵容名称:").grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        name_var = tk.StringVar(value=team.get('name', ''))
        ttk.Entry(frm, textvariable=name_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=(0, 8))

        ttk.Label(frm, text="式神1:").grid(row=1, column=0, sticky=tk.W, pady=4)
        shikigami_vars = []
        for i in range(5):
            var = tk.StringVar(value=team.get('shikigami', ['']*5)[i] if i < len(team.get('shikigami', [])) else '')
            shikigami_vars.append(var)
            ttk.Label(frm, text=f"式神{i+1}:").grid(row=i+1, column=0, sticky=tk.W, pady=4)
            ttk.Entry(frm, textvariable=var, width=30).grid(row=i+1, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="阴阳师:").grid(row=6, column=0, sticky=tk.W, pady=4)
        onmyouji_var = tk.StringVar(value=team.get('onmyouji', ''))
        ttk.Entry(frm, textvariable=onmyouji_var, width=30).grid(row=6, column=1, sticky=tk.W, pady=4)

        enabled_var = tk.BooleanVar(value=team.get('enabled', True))
        ttk.Checkbutton(frm, text="启用该阵容", variable=enabled_var).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

        def save():
            name = name_var.get().strip() or f'阵容{idx+1}'
            shikigami = [v.get().strip() for v in shikigami_vars]
            onmyouji = onmyouji_var.get().strip()
            self.team_manager.update_team(
                idx,
                name=name,
                shikigami=shikigami,
                onmyouji=onmyouji,
                enabled=enabled_var.get()
            )
            self._refresh_team_list()
            self._append_log(f"已保存阵容: {name}")
            editor.destroy()

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=save, width=12).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="取消", command=editor.destroy, width=12).pack(side=tk.LEFT)

    def _open_template_dir(self):
        from config import TEMPLATE_DIR
        template_path = TEMPLATE_DIR
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            template_path = os.path.join(exe_dir, 'templates')
        if not os.path.exists(template_path):
            os.makedirs(template_path)
        os.startfile(template_path)


def main():
    root = tk.Tk()

    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except:
        pass

    app = DoujiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
