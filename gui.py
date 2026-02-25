from __future__ import annotations

import copy
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.widgets import ToastNotification
from ttkbootstrap.dialogs import Messagebox
from tkinter import simpledialog

from logic import Logic
from persistence import SaveState
from models import SelectedCell
from audio import SoundBank


# -------------------------
# Styling constants
# -------------------------
CELL_FONT_INNER = ("Segoe UI", 22, "bold")
CELL_FONT_RING = ("Segoe UI", 18, "bold")
CELL_FONT_INNER_L2 = ("Segoe UI", 22, "bold")


class InterfaceGUI:
    def __init__(self):
        self.logic = Logic()
        self.save_state = SaveState()
        self.sounds = SoundBank()

        self.app = ttk.Window(
            title="Ass1 - 5x5 Number Game",
            themename="darkly",
            size=(980, 680),
            resizable=(True, True),
        )

        self.style = ttk.Style()

        # Timer / level timing
        self._timer_job = None
        self._level_start_time: datetime | None = None

        # For completion records
        self.level1_start_time = None
        self.level2_start_time = None

        # Inner (Level 1 buttons): big white
        self.style.configure("InnerCell.TButton", font=CELL_FONT_INNER, foreground="white")
        self.style.configure("InnerCellSelected.TButton", font=CELL_FONT_INNER, foreground="white")

        # Level 2 inner display labels (not clickable)
        self.style.configure("InnerDisplay.TLabel", font=CELL_FONT_INNER_L2, foreground="white")

        # Ring cells: force TRUE yellow (not theme-warning)
        self.style.configure(
            "RingCell.TButton",
            font=CELL_FONT_RING,
            foreground="black",
            background="#F1C40F",
        )
        self.style.map(
            "RingCell.TButton",
            background=[
                ("active", "#F7DC6F"),
                ("pressed", "#D4AC0D"),
            ],
        )
        self.style.configure(
            "RingCellSelected.TButton",
            font=CELL_FONT_RING,
            foreground="black",
            background="#FFD54A",
        )

        self.selected: SelectedCell | None = None

        # Main layout
        self.main = ttk.Frame(self.app, padding=12)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.app.columnconfigure(0, weight=1)
        self.app.rowconfigure(0, weight=1)

        self.main.columnconfigure(0, weight=3)
        self.main.columnconfigure(1, weight=2)
        self.main.rowconfigure(0, weight=1)

        self.board_card = ttk.Labelframe(self.main, text="Board (Level 1)", padding=12)
        self.board_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.board_card.rowconfigure(0, weight=1)
        self.board_card.columnconfigure(0, weight=1)

        self.panel_card = ttk.Labelframe(self.main, text="Controls", padding=12)
        self.panel_card.grid(row=0, column=1, sticky="nsew")
        self.panel_card.columnconfigure(0, weight=1)

        # -------- Level 1 view: inner-only buttons --------
        self.inner_frame = ttk.Frame(self.board_card)
        self.inner_frame.grid(row=0, column=0, sticky="nsew")

        for i in range(5):
            self.inner_frame.rowconfigure(i, weight=1, uniform="cells5")
            self.inner_frame.columnconfigure(i, weight=1, uniform="cells5")

        self.inner_buttons: dict[tuple[int, int], ttk.Button] = {}
        self._build_inner_grid()

        # -------- Level 2 view container (7x7) --------
        self.level2_container: ttk.Frame | None = None
        self.ring_buttons: dict[tuple[int, int], ttk.Button] = {}
        self.inner_display_labels: dict[tuple[int, int], ttk.Label] = {}

        # Controls
        self._build_controls()

        # Start game
        self.new_game_level1()

    # -------------------------
    # Timer helpers (User Story 11)
    # -------------------------
    def _stop_level_timer(self):
        if self._timer_job is not None:
            self.app.after_cancel(self._timer_job)
            self._timer_job = None

    def _start_level_timer(self):
        self._level_start_time = datetime.now()
        self._stop_level_timer()
        self._tick_timer()

    def _tick_timer(self):
        if self._level_start_time is None:
            self.timer_label.config(text="—")
            return

        level = self.logic.level
        limit = self.logic.get_time_limit(level)
        elapsed = (datetime.now() - self._level_start_time).total_seconds()

        if limit is None:
            self.timer_label.config(text=f"Elapsed: {int(elapsed)}s")
        else:
            remaining = int(limit - elapsed)
            if remaining >= 0:
                self.timer_label.config(text=f"Time Left: {remaining}s")
            else:
                self.timer_label.config(text=f"Overtime: {abs(remaining)}s")

        self._timer_job = self.app.after(250, self._tick_timer)

    def _current_level_elapsed_seconds(self) -> float:
        if self._level_start_time is None:
            return 0.0
        return (datetime.now() - self._level_start_time).total_seconds()

    # -------------------------
    # Build UI
    # -------------------------
    def _build_inner_grid(self) -> None:
        for r in range(5):
            for c in range(5):
                btn = ttk.Button(
                    self.inner_frame,
                    text="",
                    style="InnerCell.TButton",
                    bootstyle="secondary-outline",
                    command=lambda rr=r, cc=c: self.on_inner_cell_click(rr, cc),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=6, pady=6, ipadx=12, ipady=18)
                self.inner_buttons[(r, c)] = btn

    def _build_level2_container_hidden(self) -> None:
        """
        Build 7x7 with yellow ring buttons + separate 5x5 label grid in center.
        """
        self.level2_container = ttk.Frame(self.board_card)

        for i in range(7):
            self.level2_container.rowconfigure(i, weight=1, uniform="cells7")
            self.level2_container.columnconfigure(i, weight=1, uniform="cells7")

        # Ring buttons
        for r in range(7):
            for c in range(7):
                if not self.logic.is_ring_cell(r, c):
                    continue
                btn = ttk.Button(
                    self.level2_container,
                    text="",
                    style="RingCell.TButton",
                    command=lambda rr=r, cc=c: self.on_ring_cell_click(rr, cc),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=5, pady=5, ipadx=8, ipady=12)
                self.ring_buttons[(r, c)] = btn

        # Center framed holder
        outer_frame = ttk.Frame(self.level2_container, padding=12, bootstyle="secondary")
        outer_frame.grid(row=1, column=1, rowspan=5, columnspan=5, sticky="nsew", padx=10, pady=10)
        outer_frame.rowconfigure(0, weight=1)
        outer_frame.columnconfigure(0, weight=1)

        inner_frame = ttk.Frame(outer_frame, padding=8)
        inner_frame.grid(row=0, column=0, sticky="nsew")
        inner_frame.rowconfigure(0, weight=1)
        inner_frame.columnconfigure(0, weight=1)

        grid_frame = ttk.Frame(inner_frame)
        grid_frame.grid(row=0, column=0, sticky="nsew")

        for i in range(5):
            grid_frame.rowconfigure(i, weight=1, uniform="l2cells")
            grid_frame.columnconfigure(i, weight=1, uniform="l2cells")

        for r in range(5):
            for c in range(5):
                lbl = ttk.Label(
                    grid_frame,
                    text="",
                    style="InnerDisplay.TLabel",
                    anchor="center",
                    bootstyle="secondary",
                )
                lbl.grid(row=r, column=c, sticky="nsew", padx=6, pady=6, ipadx=10, ipady=18)
                self.inner_display_labels[(r, c)] = lbl

    def _build_controls(self) -> None:
        ttk.Label(self.panel_card, text="Selected Cell", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.selected_label = ttk.Label(self.panel_card, text="None", font=("Segoe UI", 10))
        self.selected_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        ttk.Label(self.panel_card, text="Enter Number", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w")
        self.value_var = ttk.StringVar(value="")
        self.value_entry = ttk.Entry(self.panel_card, textvariable=self.value_var)
        self.value_entry.grid(row=3, column=0, sticky="ew")
        self.value_entry.bind("<Return>", self.on_enter_pressed)

        self.place_btn = ttk.Button(self.panel_card, text="Place", bootstyle="primary", command=self.on_place)
        self.place_btn.grid(row=4, column=0, sticky="ew", pady=(8, 14))

        ttk.Label(self.panel_card, text="Score", font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w")
        self.score_label = ttk.Label(self.panel_card, text="0", font=("Segoe UI", 14))
        self.score_label.grid(row=6, column=0, sticky="w", pady=(0, 12))

        ttk.Label(self.panel_card, text="Next Number", font=("Segoe UI", 10, "bold")).grid(row=7, column=0, sticky="w")
        self.next_number_label = ttk.Label(self.panel_card, text="—", font=("Segoe UI", 18, "bold"), bootstyle="info")
        self.next_number_label.grid(row=8, column=0, sticky="w", pady=(0, 14))

        self.clear_btn = ttk.Button(self.panel_card, text="Clear Board", bootstyle="warning", command=self.on_clear_board)
        self.clear_btn.grid(row=9, column=0, sticky="ew", pady=(0, 8))

        self.undo_btn = ttk.Button(self.panel_card, text="Undo Last Move", bootstyle="info", command=self.on_undo)
        self.undo_btn.grid(row=10, column=0, sticky="ew", pady=(0, 8))

        ttk.Separator(self.panel_card).grid(row=11, column=0, sticky="ew", pady=10)

        self.new_btn = ttk.Button(self.panel_card, text="New Game (Level 1)", bootstyle="success", command=self.new_game_level1)
        self.new_btn.grid(row=12, column=0, sticky="ew", pady=4)

        self.save_btn = ttk.Button(self.panel_card, text="Save", bootstyle="secondary", command=self.on_save)
        self.save_btn.grid(row=13, column=0, sticky="ew", pady=4)

        self.load_btn = ttk.Button(self.panel_card, text="Load", bootstyle="secondary", command=self.on_load)
        self.load_btn.grid(row=14, column=0, sticky="ew", pady=4)

        self.stats_btn = ttk.Button(self.panel_card, text="Judge Statistics", bootstyle="secondary", command=self.show_judge_statistics)
        self.stats_btn.grid(row=15, column=0, sticky="ew", pady=4)

        # Timer UI (User Story 11)
        ttk.Separator(self.panel_card).grid(row=16, column=0, sticky="ew", pady=10)

        ttk.Label(self.panel_card, text="Timer", font=("Segoe UI", 10, "bold")).grid(row=17, column=0, sticky="w")
        self.timer_label = ttk.Label(self.panel_card, text="—", font=("Segoe UI", 14))
        self.timer_label.grid(row=18, column=0, sticky="w", pady=(0, 10))

        self.time_btn = ttk.Button(self.panel_card, text="Set Time Limits (Admin)", bootstyle="secondary", command=self.on_set_time_limits)
        self.time_btn.grid(row=19, column=0, sticky="ew", pady=(0, 10))

        self.exit_btn = ttk.Button(self.panel_card, text="Exit", bootstyle="danger", command=self.app.destroy)
        self.exit_btn.grid(row=20, column=0, sticky="ew", pady=(16, 0))

    # -------------------------
    # Input handlers
    # -------------------------
    def on_enter_pressed(self, event):
        self.on_place()

    def on_inner_cell_click(self, r: int, c: int) -> None:
        if self.logic.level != 1:
            return
        self.selected = SelectedCell("inner", r, c)
        self._refresh_board()
        self._refresh_panel()
        self.value_entry.focus_set()

    def on_ring_cell_click(self, r: int, c: int) -> None:
        if self.logic.level != 2:
            return
        self.selected = SelectedCell("ring", r, c)
        self._refresh_board()
        self._refresh_panel()
        self.value_entry.focus_set()

    # -------------------------
    # Admin time limits (Story 11)
    # -------------------------
    def on_set_time_limits(self):
        def ask(level: int):
            val = simpledialog.askstring(
                "Set Time Limit",
                f"Enter time limit in seconds for Level {level} (blank = no limit):",
                parent=self.app
            )
            if val is None:
                return
            val = val.strip()
            if val == "":
                self.logic.set_time_limit(level, None)
                return
            try:
                sec = int(val)
                if sec < 0:
                    raise ValueError()
                self.logic.set_time_limit(level, sec)
            except ValueError:
                Messagebox.show_warning("Invalid", "Enter a non-negative integer or blank.", parent=self.app)

        ask(1)
        ask(2)
        ask(3)

    # -------------------------
    # Actions
    # -------------------------
    def new_game_level1(self) -> None:
        # Hide level2 UI if visible
        if self.level2_container is not None:
            self.level2_container.grid_forget()

        # Show level1 inner button grid
        self.inner_frame.grid_forget()
        self.inner_frame.grid(row=0, column=0, sticky="nsew")

        self.logic.reset_new_game_level1()
        self.board_card.config(text="Board (Level 1)")

        self.selected = None
        self.value_var.set("")

        self._refresh_board()
        self._refresh_panel()

        self._start_level_timer()
        self.level1_start_time = datetime.now()
        self.value_entry.focus_set()

    def on_clear_board(self) -> None:
        if self.logic.level == 2:
            # Story 10 hook later: this should penalize
            self.logic.penalize_point_for_undo()

            self.logic.clear_ring()
            self.selected = None
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            return

        keep_one = Messagebox.yesno(
            "Clear board",
            "Keep number 1 in its original cell?\n\nYes = keep same cell\nNo = place 1 randomly",
            parent=self.app,
        )
        # Story 10 hook later: reset should penalize
        self.logic.penalize_point_for_undo()

        if keep_one:
            self.logic.clear_level1_keep_one()
        else:
            self.logic.clear_level1_random_one()

        self.selected = None
        self.value_var.set("")
        self._refresh_board()
        self._refresh_panel()

    def on_undo(self) -> None:
        if self.logic.level1_completed and self.logic.level == 2:
            if len(self.logic.move_history) <= 1:
                Messagebox.show_info(
                    "Cannot undo",
                    "Level 1 is completed and cannot be modified.\nUndo is only available for Level 2 moves.",
                    parent=self.app
                )
                return

        if not self.logic.can_undo():
            Messagebox.show_info("Cannot undo", "No moves to undo", parent=self.app)
            return

        if Messagebox.yesno("Undo Move", "Undo the last move?", parent=self.app):
            # Story 10 hook later: undo should penalize
            self.logic.penalize_point_for_undo()

            success = self.logic.undo_last_move()
            if success:
                self.selected = None
                self.value_var.set("")
                self._refresh_board()
                self._refresh_panel()
                Messagebox.show_info("Undo successful", "Last move undone", parent=self.app)

    def start_level2_ui_only(self) -> None:
        """Switch UI into Level 2."""
        self.logic.start_level2()
        self.board_card.config(text="Board (Level 2)")

        if self.level2_container is None:
            self._build_level2_container_hidden()

        self.inner_frame.grid_forget()
        self.level2_container.grid(row=0, column=0, sticky="nsew")

        self.selected = None
        self.value_var.set("")
        self._refresh_board()
        self._refresh_panel()

        self._start_level_timer()
        self.level2_start_time = datetime.now()

    def _ensure_player_name(self) -> bool:
        """Prompt until name is provided. Returns False if user cancels."""
        while not self.logic.player_name:
            name = simpledialog.askstring(
                "Name Required",
                "Enter your name:",
                parent=self.app
            )
            if name is None:
                Messagebox.show_warning("Name Required", "You must enter a name to continue.", parent=self.app)
                return False
            name = name.strip()
            if name:
                self.logic.player_name = name
        return True

    def on_place(self) -> None:
        if self.selected is None:
            Messagebox.show_warning("Click a cell first.", "No cell selected")
            return

        raw = self.value_var.get().strip()
        if raw == "":
            Messagebox.show_warning("Enter a number to place.", "No number")
            return

        try:
            value = int(raw)
        except ValueError:
            Messagebox.show_warning("Please enter a whole number.", "Invalid input")
            return

        # Level 1 expected number enforcement
        if self.logic.level == 1:
            expected = self.logic.get_next_number()
            if value != expected:
                self.logic.invalid_moves += 1
                self.sounds.incorrect_buzzer.play()
                Messagebox.show_info(
                    f"Next number must be {expected}.",
                    "Invalid number",
                    parent=self.app,
                )
                self.value_var.set("")
                self.value_entry.focus_set()
                return

        # Level 2 value range enforcement
        if self.logic.level == 2:
            if value < 2 or value > 25:
                self.sounds.incorrect_buzzer.play()
                Messagebox.show_info(
                    "Level 2 numbers must be between 2 and 25.",
                    "Invalid number",
                    parent=self.app,
                )
                self.value_var.set("")
                self.value_entry.focus_set()
                return

            if value in self.logic.get_placed_outer_numbers():
                self.sounds.incorrect_buzzer.play()
                Messagebox.show_info(
                    f"Number {value} is already placed in the outer ring.",
                    "Number already placed",
                    parent=self.app,
                )
                self.value_var.set("")
                self.value_entry.focus_set()
                return

        # Level 1 placement
        if self.logic.level == 1 and self.selected.area == "inner":
            ok = self.logic.make_move_level1(self.selected.r, self.selected.c, value)
            if not ok:
                self.logic.invalid_moves += 1
                self.sounds.incorrect_buzzer.play()
                Messagebox.show_info("Invalid placement. Try another cell.", "Invalid placement", parent=self.app)
                self.value_var.set("")
                self.value_entry.focus_set()
                return

            # Story 10 hook later: award place point
            self.logic.award_point_for_place()

            self.sounds.correct.play()
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()

            # Completion for Level 1
            if self.logic.is_level1_complete():
                if not self._ensure_player_name():
                    return

                elapsed = self._current_level_elapsed_seconds()
                elapsed = round(elapsed, 2)

                # Apply time scoring (Story 11)
                self.logic.apply_time_scoring(level=1, elapsed_seconds=elapsed)
                self._stop_level_timer()

                data = self.save_state.load_completed_games()
                completion = self.logic.build_completion_data(elapsed)

                if self.logic.is_personal_best(data, self.logic.player_name, elapsed, level=1):
                    toast = ToastNotification(
                        title="Personal Best!",
                        message=f"{self.logic.player_name}, you earned new fastest time of {elapsed}s!",
                        duration=6000,
                        bootstyle="success"
                    )
                    toast.show_toast()

                data.setdefault("Players", {})
                data["Players"].setdefault(completion["Name"], [])
                data["Players"][completion["Name"]].append(completion)
                self.save_state.save_completed_game(data)

                self.start_level2_ui_only()
            return

        # Level 2 placement
        if self.logic.level == 2 and self.selected.area == "ring":
            ok = self.logic.place_on_ring_ui_only(self.selected.r, self.selected.c, value)
            if not ok:
                self.logic.invalid_moves += 1
                self.sounds.incorrect_buzzer.play()
                Messagebox.show_info("Pick a valid empty yellow ring cell.", "Invalid ring placement", parent=self.app)
                return

            # Story 10 hook later: award place point
            self.logic.award_point_for_place()

            self.sounds.correct.play()
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()

            if self.logic.is_level2_complete():
                if not self._ensure_player_name():
                    return

                elapsed = self._current_level_elapsed_seconds()
                elapsed = round(elapsed, 2)

                # Apply time scoring (Story 11)
                self.logic.apply_time_scoring(level=2, elapsed_seconds=elapsed)
                self._stop_level_timer()

                data = self.save_state.load_completed_games()
                completion = self.logic.build_completion_data(elapsed)

                if self.logic.is_personal_best(data, self.logic.player_name, elapsed, level=2):
                    toast = ToastNotification(
                        title="Personal Best!",
                        message=f"{self.logic.player_name}, you earned new fastest time of {elapsed}s!",
                        duration=6000,
                        bootstyle="success"
                    )
                    toast.show_toast()

                data.setdefault("Players", {})
                data["Players"].setdefault(completion["Name"], [])
                data["Players"][completion["Name"]].append(completion)
                self.save_state.save_completed_game(data)

                # Story 9 later: start_level3_ui_only()
            return

        self.sounds.incorrect_buzzer.play()
        Messagebox.show_warning("Select a valid cell for the current level.", "Wrong cell", parent=self.app)

    def on_save(self) -> None:
        self.save_state.save_game(self.logic.get_state())
        Messagebox.show_info("Game saved to SavedState.json", "Saved", parent=self.app)

    def on_load(self) -> None:
        data = self.save_state.load_game()
        if not data:
            Messagebox.show_info("No saved game file found.", "No Save Found", parent=self.app)
            return

        self.logic.set_state(data)
        self.selected = None
        self.value_var.set("")

        # Show correct UI based on level
        if self.logic.level == 1:
            if self.level2_container is not None:
                self.level2_container.grid_forget()

            self.inner_frame.grid_forget()
            self.inner_frame.grid(row=0, column=0, sticky="nsew")
            self.board_card.config(text="Board (Level 1)")
        else:
            # Ensure L2 UI visible
            self.board_card.config(text="Board (Level 2)")
            if self.level2_container is None:
                self._build_level2_container_hidden()

            self.inner_frame.grid_forget()
            self.level2_container.grid(row=0, column=0, sticky="nsew")

        self._refresh_board()
        self._refresh_panel()

        # Restart timer after load
        self._start_level_timer()
        if self.logic.level == 1:
            self.level1_start_time = datetime.now()
        elif self.logic.level == 2:
            self.level2_start_time = datetime.now()

    def show_judge_statistics(self) -> None:
        data = self.save_state.load_completed_games()
        players = data.get("Players", {})

        if not players:
            Messagebox.show_info("No completed games found.", "Stats", parent=self.app)
            return

        report = ""
        for player, games in players.items():
            total_games = len(games)
            avg_time = sum(g["Completion Seconds"] for g in games) / total_games
            avg_score = sum(g["Score"] for g in games) / total_games

            total_correct = sum(g.get("Correct Moves", 0) for g in games)
            total_invalid = sum(g.get("Invalid Moves", 0) for g in games)

            total_attempts = total_correct + total_invalid
            accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0

            report += (
                f"\nPlayer: {player}\n"
                f"Games Played: {total_games}\n"
                f"Average Time: {round(avg_time, 2)}s\n"
                f"Average Score: {round(avg_score, 2)}\n"
                f"Accuracy: {round(accuracy, 2)}%\n"
                f"{'-'*30}\n"
            )

        Messagebox.show_info(report, "Judge Statistics", parent=self.app)

    # -------------------------
    # Refresh
    # -------------------------
    def _refresh_board(self) -> None:
        # Level 1 inner buttons
        for r in range(5):
            for c in range(5):
                v = self.logic.get_cell(r, c)
                btn = self.inner_buttons[(r, c)]
                btn.config(text="" if v == 0 else str(v))

                if self.selected and self.selected.area == "inner" and self.selected.r == r and self.selected.c == c:
                    btn.config(style="InnerCellSelected.TButton", bootstyle="primary")
                else:
                    btn.config(style="InnerCell.TButton", bootstyle="secondary-outline")

        # Level 2 inner display labels (same 5x5 values)
        if self.logic.level == 2 and self.inner_display_labels:
            for r in range(5):
                for c in range(5):
                    v = self.logic.get_cell(r, c)
                    lbl = self.inner_display_labels[(r, c)]
                    lbl.config(text="" if v == 0 else str(v))

        # Ring
        if self.level2_container is not None and self.logic.level == 2:
            for (r, c), btn in self.ring_buttons.items():
                v = self.logic.ring[r][c]
                btn.config(text="" if v == 0 else str(v))

                if self.selected and self.selected.area == "ring" and self.selected.r == r and self.selected.c == c:
                    btn.config(style="RingCellSelected.TButton")
                else:
                    btn.config(style="RingCell.TButton")

    def _refresh_panel(self) -> None:
        if self.selected is None:
            self.selected_label.config(text="None")
        else:
            self.selected_label.config(text=f"{self.selected.area} ({self.selected.r}, {self.selected.c})")

        self.score_label.config(text=str(self.logic.score))

        next_num = self.logic.get_next_number()
        if self.logic.level == 1:
            if next_num == 26:
                self.next_number_label.config(text="Complete")
            else:
                self.next_number_label.config(text=str(next_num))
        else:
            self.next_number_label.config(text="Any 2-25")

    def run(self) -> None:
        self.app.mainloop()