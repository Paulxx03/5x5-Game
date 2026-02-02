import json
import random
from datetime import datetime
from dataclasses import dataclass

import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox

import pygame
from tkinter import simpledialog


# -------------------------
# Sound Effects
# -------------------------
pygame.mixer.init()
metal_pipe = pygame.mixer.Sound("Sounds/Metal Pipe Falling.wav")
metal_pipe.set_volume(0.3)
incorrect_buzzer = pygame.mixer.Sound("Sounds/Incorrect Buzzer.wav")
incorrect_buzzer.set_volume(0.5)


# -------------------------
# Styling constants
# -------------------------
CELL_FONT_INNER = ("Segoe UI", 22, "bold")
CELL_FONT_RING = ("Segoe UI", 18, "bold")
CELL_FONT_INNER_L2 = ("Segoe UI", 22, "bold")


# -------------------------
# Save / Load (Text file I/O)
# -------------------------
class SaveState:
    def __init__(self, filename="SavedState.json"):
        self.filename = filename
        self.completionsfile = "CompletedGames.json"

    def save_game(self, data: dict) -> None:
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_game(self) -> dict | None:
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        
    def load_completed_games(self) -> dict:
        try:
            with open(self.completionsfile, "r", encoding="utf=8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"Players": {}}

    def save_completed_game(self, data:dict) -> None:
        with open(self.completionsfile, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)



# -------------------------
# Game Logic
# -------------------------
class Logic:
    def __init__(self):
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.score = 0
        self.level = 1
        self.player_name = None

        # Level 2 ring values (7x7, ring cells used; 0 = empty)
        self.ring = [[0 for _ in range(7)] for _ in range(7)]

    def reset_new_game_level1(self) -> None:
        """Clear board; place 1 randomly. Reset Level 2 ring too."""
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.score = 0
        self.level = 1
        self.ring = [[0 for _ in range(7)] for _ in range(7)]

        r = random.randint(0, 4)
        c = random.randint(0, 4)
        self.board[r][c] = 1

    def get_cell(self, r: int, c: int) -> int:
        return self.board[r][c]

    def previous_input(self) -> int:
        return max(max(row) for row in self.board)

    def find_position(self, target: int) -> tuple[int, int] | None:
        for r in range(5):
            for c in range(5):
                if self.board[r][c] == target:
                    return r, c
        return None
    
    def play_sound(self, sound):
      sound.play()

    def make_move_level1(self, r: int, c: int, value: int) -> bool:
        """
        Level 1 rules:
        - Must place next sequential number
        - Must place in an empty cell
        - Invalid placement ends game (handled by UI)
        - Score +1 if diagonal to predecessor
        """
        if not (0 <= r < 5 and 0 <= c < 5):
            return False

        prev_value = self.previous_input()
        if value != prev_value + 1:
            return False

        prev_pos = self.find_position(prev_value)
        if prev_pos is None:
            return False

        if self.board[r][c] != 0:
            return False

        self.board[r][c] = value

        pr, pc = prev_pos
        if abs(r - pr) != 1 or abs(c - pc) != 1:
            return False

        if abs(r - pr) == 1 and abs(c - pc) == 1:
            self.score += 1

        return True


    def is_level1_complete(self) -> bool:
        return all(cell != 0 for row in self.board for cell in row)

    # Level 2 (UI-only placement for now)
    @staticmethod
    def is_ring_cell(r: int, c: int) -> bool:
        return (r == 0 or r == 6 or c == 0 or c == 6)

    def ring_cell_empty(self, r: int, c: int) -> bool:
        return self.ring[r][c] == 0

    def place_on_ring_ui_only(self, r: int, c: int, value: int) -> bool:
        """NO Level 2 rules yet. Just: ring cell + empty + store number."""
        if not (0 <= r < 7 and 0 <= c < 7):
            return False
        if not self.is_ring_cell(r, c):
            return False
        if not self.ring_cell_empty(r, c):
            return False
        self.ring[r][c] = value
        return True

    def get_state(self) -> dict:
        return {
            "board": self.board,
            "score": self.score,
            "level": self.level,
            "ring": self.ring,
        }

    def set_state(self, state: dict) -> None:
        self.board = state["board"]
        self.score = state["score"]
        self.level = state.get("level", 1)
        self.ring = state.get("ring", [[0 for _ in range(7)] for _ in range(7)])

    def get_completion_data(self, parent) -> dict:

        while not self.player_name:
            name = simpledialog.askstring("Level Complete", "Level 1 complete!\n\nEnter your name to save your score and continue:", parent=parent)
            if name is None:
                Messagebox.show_warning("Name Required", "You must enter a name to continue", parent=parent)
            else:
                self.player_name = name.strip()
            
        now = datetime.now()
        formatted_time = now.strftime("%A %m/%d/%Y %I:%M %p")
        state = self.get_state()

        completion_data = {
            "Name" : self.player_name,
            "Time" : formatted_time,
            "Game Level" : state["level"],
            "Score" : state["score"],
            "Board" : state["board"],
            "Ring" : state["ring"]
        }

        return completion_data


# -------------------------
# GUI
# -------------------------
@dataclass
class SelectedCell:
    area: str  # "inner" or "ring"
    r: int
    c: int


class InterfaceGUI:
    def __init__(self):
        self.logic = Logic()
        self.save_state = SaveState()

        self.app = ttk.Window(
            title="Ass1 - 5x5 Number Game",
            themename="darkly",
            size=(980, 680),
            resizable=(True, True),
        )

        self.style = ttk.Style()

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

        # -------- Level 2 view container (7x7) - hidden until needed --------
        self.level2_container: ttk.Frame | None = None
        self.ring_buttons: dict[tuple[int, int], ttk.Button] = {}

        # Level 2 inner display labels (separate from Level 1)
        self.inner_display_labels: dict[tuple[int, int], ttk.Label] = {}

        # Controls
        self._build_controls()

        # Start game
        self.new_game_level1()

    # ---------- Build UI ----------
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
        Build 7x7 with yellow ring buttons, and a *separate* 5x5 label grid in the center.
        This avoids moving the Level 1 5x5 buttons (which caused the blank center).
        """
        self.level2_container = ttk.Frame(self.board_card)

        for i in range(7):
            self.level2_container.rowconfigure(i, weight=1, uniform="cells7")
            self.level2_container.columnconfigure(i, weight=1, uniform="cells7")

        # Ring buttons (yellow)
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

        # Center framed holder (nice “board” frame)
        outer_frame = ttk.Frame(self.level2_container, padding=12, bootstyle="secondary")
        outer_frame.grid(row=1, column=1, rowspan=5, columnspan=5, sticky="nsew", padx=10, pady=10)
        outer_frame.rowconfigure(0, weight=1)
        outer_frame.columnconfigure(0, weight=1)

        inner_frame = ttk.Frame(outer_frame, padding=8)
        inner_frame.grid(row=0, column=0, sticky="nsew")
        inner_frame.rowconfigure(0, weight=1)
        inner_frame.columnconfigure(0, weight=1)

        # The 5x5 display grid (labels)
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
                    bootstyle="secondary",  # gives a subtle tile look
                )
                lbl.grid(row=r, column=c, sticky="nsew", padx=6, pady=6, ipadx=10, ipady=18)
                self.inner_display_labels[(r, c)] = lbl

    def _build_controls(self) -> None:
        ttk.Label(self.panel_card, text="Selected Cell", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.selected_label = ttk.Label(self.panel_card, text="None", font=("Segoe UI", 10))
        self.selected_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        ttk.Label(self.panel_card, text="Enter Number", font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, sticky="w"
        )
        self.value_var = ttk.StringVar(value="")
        self.value_entry = ttk.Entry(self.panel_card, textvariable=self.value_var)
        self.value_entry.grid(row=3, column=0, sticky="ew")
        self.value_entry.bind("<Return>", self.on_enter_pressed)

        self.place_btn = ttk.Button(self.panel_card, text="Place", bootstyle="primary", command=self.on_place)
        self.place_btn.grid(row=4, column=0, sticky="ew", pady=(8, 14))

        ttk.Label(self.panel_card, text="Score (Level 1)", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, sticky="w"
        )
        self.score_label = ttk.Label(self.panel_card, text="0", font=("Segoe UI", 14))
        self.score_label.grid(row=6, column=0, sticky="w", pady=(0, 12))

        ttk.Label(self.panel_card, text="Next Number", font=("Segoe UI", 10, "bold")).grid(
            row=7, column=0, sticky="w"
        )
        self.next_number_label = ttk.Label(
            self.panel_card, text="—", font=("Segoe UI", 18, "bold"), bootstyle="info"
        )
        self.next_number_label.grid(row=8, column=0, sticky="w", pady=(0, 14))

        ttk.Separator(self.panel_card).grid(row=9, column=0, sticky="ew", pady=10)

        self.new_btn = ttk.Button(
            self.panel_card, text="New Game (Level 1)", bootstyle="success", command=self.new_game_level1
        )
        self.new_btn.grid(row=10, column=0, sticky="ew", pady=4)

        self.save_btn = ttk.Button(self.panel_card, text="Save", bootstyle="secondary", command=self.on_save)
        self.save_btn.grid(row=11, column=0, sticky="ew", pady=4)

        self.load_btn = ttk.Button(self.panel_card, text="Load", bootstyle="secondary", command=self.on_load)
        self.load_btn.grid(row=12, column=0, sticky="ew", pady=4)

        self.exit_btn = ttk.Button(self.panel_card, text="Exit", bootstyle="danger", command=self.app.destroy)
        self.exit_btn.grid(row=13, column=0, sticky="ew", pady=(16, 0))

    # ---------- Input handlers ----------
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

    # ---------- Actions ----------
    def new_game_level1(self) -> None:
        # Hide level2 UI if visible
        if self.level2_container is not None:
            self.level2_container.grid_forget()

        # Show level1 inner button grid
        self.inner_frame.grid_forget()
        self.inner_frame.grid(row=0, column=0, sticky="nsew")

        self.logic.reset_new_game_level1()
        self.selected = None
        self.value_var.set("")
        self.next_number_label.config(text="—")
        self.board_card.config(text="Board (Level 1)")
        self._refresh_board()
        self._refresh_panel()

    def start_level2_ui_only(self) -> None:
        """Switch UI into Level 2: show yellow ring + display-only inner 5x5."""
        self.logic.level = 2
        self.board_card.config(text="Board (Level 2)")

        if self.level2_container is None:
            self._build_level2_container_hidden()

        # Hide the Level 1 button grid (we don't move it)
        self.inner_frame.grid_forget()

        # Show Level 2 container
        self.level2_container.grid(row=0, column=0, sticky="nsew")

        self.selected = None
        self._refresh_board()
        self._refresh_panel()

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

        # Level 1 placement
        if self.logic.level == 1 and self.selected.area == "inner":
            ok = self.logic.make_move_level1(self.selected.r, self.selected.c, value)
            if not ok:
                self.logic.play_sound(metal_pipe)
                #self.logic.play_sound(incorrect_buzzer)
                Messagebox.show_info("Invalid placement. Game over.", "Game Over", parent=self.app)

                self.new_game_level1()
                return

            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()

            if self.logic.is_level1_complete():
                completion = self.logic.get_completion_data(parent=self.app)
                save_data = self.save_state.load_completed_games()
                save_data.setdefault("Players", {})
                save_data["Players"].setdefault(completion["Name"], [])
                save_data["Players"][completion["Name"]].append(completion)
                self.save_state.save_completed_game(save_data)
                self.start_level2_ui_only()
            return

        # Level 2 ring placement (UI-only)
        if self.logic.level == 2 and self.selected.area == "ring":
            ok = self.logic.place_on_ring_ui_only(self.selected.r, self.selected.c, value)
            if not ok:
                Messagebox.show_warning("Pick an empty yellow ring cell.", "Invalid ring placement")
                return

            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()
            return

        Messagebox.show_warning("Select a valid cell for the current level.", "Wrong cell")

    def on_save(self) -> None:
        self.save_state.save_game(self.logic.get_state())
        Messagebox.show_info("Game saved to SavedState.json", "Saved")

    def on_load(self) -> None:
        data = self.save_state.load_game()
        if not data:
            Messagebox.show_info("No saved game file found.", "No Save Found")
            return

        self.logic.set_state(data)
        self.selected = None
        self.value_var.set("")
        self.next_number_label.config(text="—")

        # If loaded Level 1 is complete, auto-advance
        if self.logic.level == 1 and self.logic.is_level1_complete():
            Messagebox.show_info(
                "Loaded game has Level 1 completed. Switching to Level 2.",
                "Auto-Advance",
            )
            self.start_level2_ui_only()
            return

        # Show correct UI based on level
        if self.logic.level == 1:
            if self.level2_container is not None:
                self.level2_container.grid_forget()

            self.inner_frame.grid_forget()
            self.inner_frame.grid(row=0, column=0, sticky="nsew")
            self.board_card.config(text="Board (Level 1)")
        else:
            self.start_level2_ui_only()

        self._refresh_board()
        self._refresh_panel()

    # ---------- Refresh ----------
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

        # Level 2 inner display labels (shows the same 5x5 values)
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

    def run(self) -> None:
        self.app.mainloop()


if __name__ == "__main__":
    InterfaceGUI().run()


