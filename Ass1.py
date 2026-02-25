import json
import random
from datetime import datetime
from dataclasses import dataclass

import ttkbootstrap as ttk
from ttkbootstrap.widgets import ToastNotification
from ttkbootstrap.dialogs import Messagebox

import pygame
from tkinter import simpledialog
import copy
from typing import List, Tuple

import sys, os


# -------------------------
# Sound Effects
# -------------------------

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

pygame.mixer.init()
metal_pipe = pygame.mixer.Sound(resource_path("Sounds/Metal Pipe Falling.wav"))
metal_pipe.set_volume(0.3)
incorrect_buzzer = pygame.mixer.Sound(resource_path("Sounds/Incorrect Buzzer.wav"))
incorrect_buzzer.set_volume(0.5)
correct = pygame.mixer.Sound(resource_path("Sounds/Correct.wav"))
correct.set_volume(0.5)

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
        self.correct_moves = 0
        self.invalid_moves = 0

        # Level 2 ring values (7x7, ring cells used; 0 = empty)
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.move_history: List[Tuple[str, dict]] = []  # List of (action_type, state_snapshot)
        self.MAX_UNDO_HISTORY = 50
        self.level1_completed = False
        self.level1_snapshot = None
        self.level2_completed = False
        self.level2_available_positions = {}  
        self.current_outer_number = 2  
    def get_placed_outer_numbers(self) -> List[int]:
        """Get list of numbers already placed in outer ring"""
        placed = []
        for r in range(7):
            for c in range(7):
                if self.is_ring_cell(r, c) and self.ring[r][c] != 0:
                    placed.append(self.ring[r][c])
        return placed
    def _find_position_inner(self, number: int) -> Tuple[int, int] | None:
        """Find position of a number in the inner 5x5 board"""
        for r in range(5):
            for c in range(5):
                if self.board[r][c] == number:
                    return (r, c)
        return None
    
    def _is_on_main_diagonal(self, r: int, c: int) -> bool:
        """Check if position is on main diagonal (r == c)"""
        return r == c
    
    def _is_on_anti_diagonal(self, r: int, c: int) -> bool:
        """Check if position is on anti-diagonal (r + c == 4) for 5x5 board"""
        return r + c == 4
    
    def _get_available_positions_for_number(self, number: int) -> List[Tuple[int, int]]:
        """Get available outer ring positions for a specific number based on rules"""
        if number > 25 or number < 2:
            return []
        
        # Find the inner board position of this number
        inner_pos = self._find_position_inner(number)
        if not inner_pos:
            return []
        
        r, c = inner_pos
        available_positions = []
        
        # Convert inner 5x5 coordinates (0-4) to outer 7x7 coordinates
        outer_r = r + 1  # Inner rows 0-4 become outer rows 1-5
        outer_c = c + 1  # Inner cols 0-4 become outer cols 1-5
        
        # Rule 3: Blue cells - ends of the row and column
        # Top end of column (row 0, same column)
        if self.ring[0][outer_c] == 0:
            available_positions.append((0, outer_c))
        
        # Bottom end of column (row 6, same column)
        if self.ring[6][outer_c] == 0:
            available_positions.append((6, outer_c))
        
        # Left end of row (same row, column 0)
        if self.ring[outer_r][0] == 0:
            available_positions.append((outer_r, 0))
        
        # Right end of row (same row, column 6)
        if self.ring[outer_r][6] == 0:
            available_positions.append((outer_r, 6))
        
        # Rule 4: Yellow cells - diagonal ends (only for numbers on main diagonals)
        # Check if the number is on either of the two longest diagonals
        on_main = self._is_on_main_diagonal(r, c)
        on_anti = self._is_on_anti_diagonal(r, c)
        
        if on_main:
            # Top-left diagonal end
            if (r, c) == (0, 0):  # Top-left corner
                if self.ring[0][0] == 0:
                    available_positions.append((0, 0))
            # Bottom-right diagonal end
            if (r, c) == (4, 4):  # Bottom-right corner
                if self.ring[6][6] == 0:
                    available_positions.append((6, 6))
        
        if on_anti:
            # Top-right diagonal end
            if (r, c) == (0, 4):  # Top-right corner
                if self.ring[0][6] == 0:
                    available_positions.append((0, 6))
            # Bottom-left diagonal end
            if (r, c) == (4, 0):  # Bottom-left corner
                if self.ring[6][0] == 0:
                    available_positions.append((6, 0))
        
        return available_positions
    def start_level2(self) -> None:
        """Called when transitioning from Level 1 to Level 2"""
        self.level1_completed = True
        self.level1_snapshot = {
            "board": copy.deepcopy(self.board),
            "score": self.score,
            "level": 1,
            "ring": copy.deepcopy(self.ring)
        }
        # Clear history for Level 2
        self.move_history.clear()
        # Save initial Level 2 state
        self._save_to_history("level2_initial")
        self.level = 2
        self.correct_moves = 0
        self.invalid_moves = 0
        self.current_outer_number = 2 
        self.level2_completed = False  
        
        self._calculate_all_available_positions()  

    def reset_new_game_level1(self) -> None:
        """Clear board; place 1 randomly. Reset Level 2 ring too."""
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.score = 0
        self.level = 1
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.move_history.clear()
        r = random.randint(0, 4)
        c = random.randint(0, 4)
        self.board[r][c] = 1
        self._save_to_history("initial")
        self.level1_completed = False
        self.level1_snapshot = None
        self.correct_moves = 0
        self.invalid_moves = 0

    def clear_level1_keep_one(self) -> None:
        """Clear board but keep 1 in its current cell."""
        pos = self.find_position(1)
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.score = 0
        self.level = 1
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.move_history.clear()
        if pos is None:
            r = random.randint(0, 4)
            c = random.randint(0, 4)
        else:
            r, c = pos
        self.board[r][c] = 1
        self._save_to_history("initial")
        self.level1_completed = False
        self.level1_snapshot = None

    def clear_level1_random_one(self) -> None:
        """Clear board and place 1 randomly."""
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.score = 0
        self.level = 1
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.move_history.clear()
        r = random.randint(0, 4)
        c = random.randint(0, 4)
        self.board[r][c] = 1
        self._save_to_history("initial")
        self.level1_completed = False
        self.level1_snapshot = None
    def _save_to_history(self, action_type: str, state_snapshot: dict = None) -> None:  # ADD state_snapshot parameter
        """Save current state to undo history."""
        if len(self.move_history) >= self.MAX_UNDO_HISTORY:
            self.move_history.pop(0)  # Remove oldest if limit reached
            
        if state_snapshot is None:
            # If no snapshot provided, create one of current state
            state_snapshot = {
                "board": copy.deepcopy(self.board),
                "score": self.score,
                "level": self.level,
                "ring": copy.deepcopy(self.ring)
            }
        
        self.move_history.append((action_type, state_snapshot))
    
    def undo_last_move(self) -> bool:
        """Revert to previous state. Returns True if undo was successful."""
        if self.level1_completed and self.level == 2:
            # Check if we're at the beginning of Level 2 history
            if len(self.move_history) <= 1:
                return False
        if len(self.move_history) < 2:  # Need at least initial + one move
            return False
            
        # Get the PREVIOUS state (don't pop yet!)
        if self.level == 1:
            action_type, prev_state = self.move_history[-2]  # Use -2 for previous state
        else:
            action_type, prev_state = self.move_history[-1]
        
        # Restore previous state
        self.board = copy.deepcopy(prev_state["board"])
        self.score = prev_state["score"]
        self.level = prev_state["level"]
        self.ring = copy.deepcopy(prev_state["ring"])
        
        # Now remove the CURRENT state from history (keep previous state)
        self.move_history.pop()
        
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.move_history) > 1


    def get_cell(self, r: int, c: int) -> int:
        return self.board[r][c]

    def previous_input(self) -> int:
        return max(max(row) for row in self.board)

    def get_next_number(self) -> int:
        if self.level == 1:
            board_max = max(max(row) for row in self.board)
            if board_max == 25:
                return max(max(row) for row in self.ring) + 1 if any(any(row) for row in self.ring) else 2
            return board_max + 1
        else:
            # Level 2: No next number - show 0 or -1
            return -1

    def find_position(self, target: int) -> tuple[int, int] | None:
        for r in range(5):
            for c in range(5):
                if self.board[r][c] == target:
                    return r, c
        return None
    
    def play_sound(self, sound):
      sound.play()

    

    def make_move_level1(self, r: int, c: int, value: int) -> bool:
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
        
        pr, pc = prev_pos
        if abs(r - pr) > 1 or abs(c - pc) > 1:
            return False

        # Make the move FIRST
        self.board[r][c] = value

        # Update score if diagonal
        if abs(r - pr) == 1 and abs(c - pc) == 1:
            self.score += 1
        
        # Save the POST-MOVE state to history
        post_move_state = {
            "board": copy.deepcopy(self.board),  # Board AFTER placing number
            "score": self.score,  # Score AFTER potential increase
            "level": self.level,
            "ring": copy.deepcopy(self.ring)
        }
        self._save_to_history("move", post_move_state)  # ✅ SAVE NEW STATE
        self.correct_moves += 1

        return True

    def is_level1_complete(self) -> bool:
        return all(cell != 0 for row in self.board for cell in row)
    
    def is_level2_complete(self) -> bool:
        """Check if all outer ring cells (24 cells) are filled"""
        placed_count = 0
        for r in range(7):
            for c in range(7):
                if self.is_ring_cell(r, c) and self.ring[r][c] != 0:
                    placed_count += 1
        
        # There are 24 outer ring cells (top/bottom: 5+5=10, left/right: 5+5=10, minus 4 corners counted twice)
        return placed_count == 24

    # Level 2 (UI-only placement for now)
    @staticmethod
    def is_ring_cell(r: int, c: int) -> bool:
        return (r == 0 or r == 6 or c == 0 or c == 6)

    def ring_cell_empty(self, r: int, c: int) -> bool:
        return self.ring[r][c] == 0

    def place_on_ring_ui_only(self, r: int, c: int, value: int) -> bool:
        if not (0 <= r < 7 and 0 <= c < 7):
            return False
        if not self.is_ring_cell(r, c):
            return False
        if not self.ring_cell_empty(r, c):
            return False
        
        if value in self.get_placed_outer_numbers():
            return False
        
        # Check if this placement follows Level 2 rules
        available_positions = self.level2_available_positions.get(value, [])
        if (r, c) not in available_positions:
            return False
        
        # Save PRE-MOVE state
        pre_move_state = {
            "board": copy.deepcopy(self.board),
            "score": self.score,
            "level": self.level,
            "ring": copy.deepcopy(self.ring),
            "level2_available_positions": copy.deepcopy(self.level2_available_positions),  # <-- ADD THIS
            "current_outer_number": self.current_outer_number  # <-- ADD THIS
        }
        self._save_to_history("ring_move", pre_move_state)
        
        # Now place the number
        self.ring[r][c] = value
        self.correct_moves += 1
        
        # Recalculate available positions for all remaining numbers
        self._calculate_all_available_positions()
        
        return True
    def clear_ring(self) -> None:
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.current_outer_number = 2  
        self._calculate_all_available_positions()  

    

    def get_state(self) -> dict:
        return {
            "board": self.board,
            "score": self.score,
            "level": self.level,
            "ring": self.ring,
            "level1_completed": self.level1_completed,
            "level1_snapshot": self.level1_snapshot,
            "level2_available_positions": self.level2_available_positions,  
            "current_outer_number": self.current_outer_number,  
            "level2_completed": self.level2_completed  
        }

    def set_state(self, state: dict) -> None:
        self.board = state["board"]
        self.score = state["score"]
        self.level = state.get("level", 1)
        self.ring = state.get("ring", [[0 for _ in range(7)] for _ in range(7)])
        self.level1_completed = state.get("level1_completed", False)
        self.level1_snapshot = state.get("level1_snapshot", None)
        self.level2_available_positions = state.get("level2_available_positions", {})  # <-- ADD THIS
        self.current_outer_number = state.get("current_outer_number", 2)  # <-- ADD THIS
        self.level2_completed = state.get("level2_completed", False)  # <-- ADD THIS

    def get_completion_data(self, elapsed_time, parent) -> dict:

        while not self.player_name:
            name = simpledialog.askstring("Level Complete", "Level 1 complete!\n\nEnter your name to save your score and continue:", parent=parent)
            if name is None:
                Messagebox.show_warning("Name Required", "You must enter a name to continue", parent=parent)
            else:
                self.player_name = name.strip()
            
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state = self.get_state()

        completion_data = {
            "Name" : self.player_name,
            "Completed At" : formatted_time,
            "Completion Seconds": elapsed_time,
            "Correct Moves": self.correct_moves,
            "Invalid Moves": self.invalid_moves,
            "Game Level" : state["level"],
            "Score" : state["score"],
            "Board" : state["board"],
            "Ring" : state["ring"]
        }

        return completion_data
    
    def is_personal_best(self, data, player_name, current_time_seconds, level):

        players = data.get("Players", {})
        player_games = players.get(player_name, [])

        previous_times = [
            game["Completion Seconds"]
            for game in player_games
            if game.get("Game Level") == level
        ]

        if not previous_times:
            return False

        return current_time_seconds < min(previous_times)

    def _calculate_all_available_positions(self) -> None:
        """Calculate available outer ring positions for numbers 2-25"""
        self.level2_available_positions = {}
        
        for num in range(2, 26):
            positions = self._get_available_positions_for_number(num)
            self.level2_available_positions[num] = positions


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

        self.level1_start_time = None
        self.level2_start_time = None
        self.level1_duration = None
        self.level2_duration = None

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
        self.level1_start_time = datetime.now()

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

        self.clear_btn = ttk.Button(
            self.panel_card, text="Clear Board", bootstyle="warning", command=self.on_clear_board
        )
        self.clear_btn.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        self.undo_btn = ttk.Button(
            self.panel_card, 
            text="Undo Last Move", 
            bootstyle="info",
            command=self.on_undo
        )
        self.undo_btn.grid(row=10, column=0, sticky="ew", pady=(0, 8))
        ttk.Separator(self.panel_card).grid(row=11, column=0, sticky="ew", pady=10)

        

        self.new_btn = ttk.Button(
            self.panel_card, text="New Game (Level 1)", bootstyle="success", command=self.new_game_level1
        )
        self.new_btn.grid(row=12, column=0, sticky="ew", pady=4)

        self.save_btn = ttk.Button(self.panel_card, text="Save", bootstyle="secondary", command=self.on_save)
        self.save_btn.grid(row=13, column=0, sticky="ew", pady=4)

        self.load_btn = ttk.Button(self.panel_card, text="Load", bootstyle="secondary", command=self.on_load)
        self.load_btn.grid(row=14, column=0, sticky="ew", pady=4)

        self.load_btn = ttk.Button(self.panel_card, text="Judge Statistics", bootstyle="secondary", command=self.show_judge_statistics)
        self.load_btn.grid(row=15, column=0, sticky="ew", pady=4)

        self.exit_btn = ttk.Button(self.panel_card, text="Exit", bootstyle="danger", command=self.app.destroy)
        self.exit_btn.grid(row=16, column=0, sticky="ew", pady=(16, 0))
    def on_undo(self) -> None:
        """Handle undo button click."""
        if self.logic.level1_completed and self.logic.level == 2:
            # Check if we're at the beginning of Level 2 history
            if len(self.logic.move_history) <= 1:
                Messagebox.show_info(
                    "Cannot undo", 
                    "Level 1 is completed and cannot be modified.\n"
                    "Undo is only available for Level 2 moves.",
                    parent=self.app
                )
                return
        if not self.logic.can_undo():
            Messagebox.show_info("Cannot undo", "No moves to undo", parent=self.app)
            return
            
        if Messagebox.yesno("Undo Move", "Undo the last move?", parent=self.app):
            success = self.logic.undo_last_move()
            if success:
                self.selected = None
                self.value_var.set("")
                self._refresh_board()
                self._refresh_panel()
                Messagebox.show_info("Undo successful", "Last move undone", parent=self.app)
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
        self.level1_start_time = datetime.now()
        self.selected = None
        self.value_var.set("")
        self.board_card.config(text="Board (Level 1)")
        self._refresh_board()
        self._refresh_panel()

    def on_clear_board(self) -> None:
        if self.logic.level == 2:
            self.logic.clear_ring()
            self.selected = None
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            return

        keep_one = Messagebox.yesno(
            "Clear board",
            "Keep number 1 in its original cell?\n\n"
            "Yes = keep same cell\nNo = place 1 randomly",
            parent=self.app,
        )
        if keep_one:
            self.logic.clear_level1_keep_one()
        else:
            self.logic.clear_level1_random_one()

        self.selected = None
        self.value_var.set("")
        self._refresh_board()
        self._refresh_panel()

    def start_level2_ui_only(self) -> None:
        self.level2_start_time = datetime.now() 
        """Switch UI into Level 2: show yellow ring + display-only inner 5x5."""
        self.logic.start_level2()
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

        
        if self.logic.level == 1:
            expected = self.logic.get_next_number()
            if value != expected:
                self.logic.invalid_moves += 1
                self.logic.play_sound(incorrect_buzzer)
                Messagebox.show_info(
                    f"Next number must be {expected}.",
                    "Invalid number",
                    parent=self.app,
                )
                self.value_var.set("")
                self.value_entry.focus_set()
                return

        if self.logic.level == 2:
            if value < 2 or value > 25:
                self.logic.play_sound(incorrect_buzzer)
                Messagebox.show_info(
                    "Level 2 numbers must be between 2 and 25.",
                    "Invalid number",
                    parent=self.app,
                )
                self.value_var.set("")
                self.value_entry.focus_set()
                return
            
            # Check if number already placed
            if value in self.logic.get_placed_outer_numbers():
                self.logic.play_sound(incorrect_buzzer)
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
                self.logic.play_sound(incorrect_buzzer) 
                Messagebox.show_info("Invalid placement. Try another cell.", "Invalid placement", parent=self.app)
                self.value_var.set("")
                self.value_entry.focus_set()
                return
            self.logic.play_sound(correct)
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()

            if self.logic.is_level1_complete():
                self.level1_end_time = datetime.now() 
                self.level1_duration = round((self.level1_end_time - self.level1_start_time).total_seconds(), 2) 
                data = self.save_state.load_completed_games()
                completion = self.logic.get_completion_data(self.level1_duration, parent=self.app)
                save_data = self.save_state.load_completed_games()

                if (self.logic.is_personal_best(data, self.logic.player_name, self.level1_duration, level = 1)):
                    toast = ToastNotification(
                        title="Personal Best!",
                        message=f"{self.logic.player_name}, you earned new fastest time of {self.level1_duration}s!",
                        duration=6000,
                        bootstyle="success"
                    )
                    toast.show_toast()
                
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
                self.logic.invalid_moves += 1
                self.logic.play_sound(incorrect_buzzer)
                Messagebox.show_info("Pick an empty yellow ring cell.", "Invalid ring placement")
                return
            self.logic.play_sound(correct)
            self.value_var.set("")
            self._refresh_board()
            self._refresh_panel()
            self.value_entry.focus_set()

            if self.logic.is_level2_complete():
                self.level2_end_time = datetime.now() 
                self.level2_duration = round((self.level2_end_time - self.level2_start_time).total_seconds(), 2) 
                completion = self.logic.get_completion_data(self.level2_duration, parent=self.app)
                save_data = self.save_state.load_completed_games()


                if (self.logic.is_personal_best(save_data, self.logic.player_name, self.level2_duration, level = 2)):
                    toast = ToastNotification(
                        title="Personal Best!",
                        message=f"{self.logic.player_name}, you earned new fastest time of {self.level2_duration}s!",
                        duration=6000,
                        bootstyle="success"
                    )
                    toast.show_toast()

                save_data.setdefault("Players", {})
                save_data["Players"].setdefault(completion["Name"], [])
                save_data["Players"][completion["Name"]].append(completion)
                self.save_state.save_completed_game(save_data)
            return
        
        self.logic.play_sound(incorrect_buzzer)
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

        # If loaded Level 1 is complete, auto-advance
        if self.logic.level == 1 and self.logic.is_level1_complete():
            self.logic.level1_completed = True
            self.logic.level1_snapshot = {
                "board": copy.deepcopy(self.logic.board),
                "score": self.logic.score,
                "level": 1,
                "ring": copy.deepcopy(self.logic.ring)
            }
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

    def show_judge_statistics(self) -> None:
        data = self.save_state.load_completed_games()
        players = data.get("Players", {})

        if not players:
            Messagebox.show_info("No completed games found.", "Stats")
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

        Messagebox.show_info(report, "Judge Statistics")

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
        
        # Show next number for Level 1, different message for Level 2
        next_num = self.logic.get_next_number()
        if self.logic.level == 1:
            if next_num == 26:  # All numbers placed
                self.next_number_label.config(text="Complete")
            else:
                self.next_number_label.config(text=str(next_num))
        else:
            # Level 2: Show "Any 2-25" or "—"
            self.next_number_label.config(text="Any 2-25")

    def run(self) -> None:
        self.app.mainloop()


if __name__ == "__main__":
    InterfaceGUI().run()



