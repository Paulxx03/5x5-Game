import copy
import random
from datetime import datetime
from typing import List, Tuple


class Logic:
    """
    Core game logic (no GUI imports).
    - Handles board/ring state
    - Validates moves
    - Undo history
    - Save/load state data
    - Completion record building (assumes player_name already set by GUI)
    - User Story 11: time limit scoring
    """

    def __init__(self):
        # Level 1: 5x5 inner board
        self.board = [[0 for _ in range(5)] for _ in range(5)]

        # Level 2: 7x7 ring (only outer cells used)
        self.ring = [[0 for _ in range(7)] for _ in range(7)]

        # Shared game stats
        self.score = 0
        self.level = 1
        self.player_name: str | None = None
        self.correct_moves = 0
        self.invalid_moves = 0

        # Undo history
        self.move_history: List[Tuple[str, dict]] = []
        self.MAX_UNDO_HISTORY = 50

        # Level completion flags
        self.level1_completed = False
        self.level1_snapshot = None
        self.level2_completed = False

        # Level 2 placement helper data
        self.level2_available_positions = {}
        self.current_outer_number = 2

        # User Story 11: time limits per level (None means disabled)
        self.time_limits = {1: 60, 2: 60, 3: 60}
        self.time_bonus_last = 0  # last applied delta

    # -------------------------
    # User Story 11: Timer config + scoring
    # -------------------------
    def set_time_limit(self, level: int, seconds: int | None) -> None:
        """seconds=None disables timing for that level."""
        if seconds is None:
            self.time_limits[level] = None
            return
        self.time_limits[level] = max(0, int(seconds))

    def get_time_limit(self, level: int) -> int | None:
        return self.time_limits.get(level, None)

    def apply_time_scoring(self, level: int, elapsed_seconds: float) -> int:
        """
        +1 point per unused second (under limit)
        -1 point per extra second (over limit)
        Returns delta applied.
        """
        limit = self.get_time_limit(level)
        if limit is None:
            self.time_bonus_last = 0
            return 0

        elapsed_int = int(round(elapsed_seconds))
        delta = (limit - elapsed_int)  # + if under, - if over
        self.score += delta
        self.time_bonus_last = delta
        return delta

    # -------------------------
    # (Future) User Story 10 Hooks
    # -------------------------
    def award_point_for_place(self) -> None:
        """Story 10 later: +1 per successful placement (any level)."""
        # TODO: Implement when Story 10 is active
        pass

    def penalize_point_for_undo(self) -> None:
        """Story 10 later: -1 per undo/reset/clear actions."""
        # TODO: Implement when Story 10 is active
        pass

    # -------------------------
    # Utility helpers
    # -------------------------
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

    def get_next_number(self) -> int:
        """
        Level 1: next number is max(board)+1 until 25.
        Level 2: UI allows any 2-25 (validation is on ring rules).
        """
        if self.level == 1:
            board_max = max(max(row) for row in self.board)
            if board_max == 25:
                return 26
            return board_max + 1
        return -1

    # -------------------------
    # Undo history
    # -------------------------
    def _snapshot_state(self) -> dict:
        """Create a complete snapshot used for undo + save/load."""
        return {
            "board": copy.deepcopy(self.board),
            "score": self.score,
            "level": self.level,
            "ring": copy.deepcopy(self.ring),
            "level1_completed": self.level1_completed,
            "level1_snapshot": copy.deepcopy(self.level1_snapshot),
            "level2_completed": self.level2_completed,
            "level2_available_positions": copy.deepcopy(self.level2_available_positions),
            "current_outer_number": self.current_outer_number,
            "correct_moves": self.correct_moves,
            "invalid_moves": self.invalid_moves,
            "player_name": self.player_name,
            "time_limits": copy.deepcopy(self.time_limits),
            "time_bonus_last": self.time_bonus_last,
        }

    def _restore_snapshot(self, snap: dict) -> None:
        self.board = copy.deepcopy(snap["board"])
        self.score = snap["score"]
        self.level = snap["level"]
        self.ring = copy.deepcopy(snap["ring"])

        self.level1_completed = snap.get("level1_completed", False)
        self.level1_snapshot = copy.deepcopy(snap.get("level1_snapshot", None))
        self.level2_completed = snap.get("level2_completed", False)

        self.level2_available_positions = copy.deepcopy(snap.get("level2_available_positions", {}))
        self.current_outer_number = snap.get("current_outer_number", 2)

        self.correct_moves = snap.get("correct_moves", 0)
        self.invalid_moves = snap.get("invalid_moves", 0)
        self.player_name = snap.get("player_name", None)

        self.time_limits = copy.deepcopy(snap.get("time_limits", {1: 60, 2: 60, 3: 60}))
        self.time_bonus_last = snap.get("time_bonus_last", 0)

    def _save_to_history(self, action_type: str, state_snapshot: dict | None = None) -> None:
        if len(self.move_history) >= self.MAX_UNDO_HISTORY:
            self.move_history.pop(0)

        if state_snapshot is None:
            state_snapshot = self._snapshot_state()

        self.move_history.append((action_type, state_snapshot))

    def can_undo(self) -> bool:
        return len(self.move_history) > 1

    def undo_last_move(self) -> bool:
        """
        Undo behavior:
        - Level 1: pop back one snapshot
        - Level 2: pop back one snapshot
        - If level1_completed and level==2, cannot undo past the initial Level 2 state.
        """
        if self.level1_completed and self.level == 2:
            # Prevent undoing into Level 1 state
            if len(self.move_history) <= 1:
                return False

        if len(self.move_history) < 2:
            return False

        # Remove current state
        self.move_history.pop()

        # Restore new last state
        _, prev_state = self.move_history[-1]
        self._restore_snapshot(prev_state)
        return True

    # -------------------------
    # Level transitions / resets
    # -------------------------
    def reset_new_game_level1(self) -> None:
        """Clear everything and place '1' randomly."""
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.score = 0
        self.level = 1

        self.correct_moves = 0
        self.invalid_moves = 0

        self.move_history.clear()
        self.level1_completed = False
        self.level1_snapshot = None
        self.level2_completed = False

        self.level2_available_positions = {}
        self.current_outer_number = 2

        r = random.randint(0, 4)
        c = random.randint(0, 4)
        self.board[r][c] = 1

        self._save_to_history("initial")

    def clear_level1_keep_one(self) -> None:
        """Clear Level 1 board but keep 1 in same position."""
        pos = self.find_position(1)
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.score = 0
        self.level = 1

        self.move_history.clear()
        self.level1_completed = False
        self.level1_snapshot = None
        self.level2_completed = False

        if pos is None:
            r = random.randint(0, 4)
            c = random.randint(0, 4)
        else:
            r, c = pos

        self.board[r][c] = 1
        self._save_to_history("initial")

    def clear_level1_random_one(self) -> None:
        """Clear Level 1 board and place 1 randomly."""
        self.board = [[0 for _ in range(5)] for _ in range(5)]
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.score = 0
        self.level = 1

        self.move_history.clear()
        self.level1_completed = False
        self.level1_snapshot = None
        self.level2_completed = False

        r = random.randint(0, 4)
        c = random.randint(0, 4)
        self.board[r][c] = 1

        self._save_to_history("initial")

    def start_level2(self) -> None:
        """Transition from Level 1 into Level 2."""
        self.level1_completed = True
        self.level1_snapshot = {
            "board": copy.deepcopy(self.board),
            "score": self.score,
            "level": 1,
            "ring": copy.deepcopy(self.ring),
        }

        self.level = 2
        self.correct_moves = 0
        self.invalid_moves = 0
        self.current_outer_number = 2
        self.level2_completed = False

        self.move_history.clear()
        self._calculate_all_available_positions()
        self._save_to_history("level2_initial")

    # -------------------------
    # Level 1 move rules
    # -------------------------
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

        # Apply move
        self.board[r][c] = value

        # Your current scoring: +1 if diagonal step
        if abs(r - pr) == 1 and abs(c - pc) == 1:
            self.score += 1

        self.correct_moves += 1

        # Save post-move state
        self._save_to_history("move")
        return True

    def is_level1_complete(self) -> bool:
        return all(cell != 0 for row in self.board for cell in row)

    # -------------------------
    # Level 2 ring rules
    # -------------------------
    @staticmethod
    def is_ring_cell(r: int, c: int) -> bool:
        return (r == 0 or r == 6 or c == 0 or c == 6)

    def ring_cell_empty(self, r: int, c: int) -> bool:
        return self.ring[r][c] == 0

    def get_placed_outer_numbers(self) -> List[int]:
        placed = []
        for r in range(7):
            for c in range(7):
                if self.is_ring_cell(r, c) and self.ring[r][c] != 0:
                    placed.append(self.ring[r][c])
        return placed

    def _find_position_inner(self, number: int) -> Tuple[int, int] | None:
        for r in range(5):
            for c in range(5):
                if self.board[r][c] == number:
                    return (r, c)
        return None

    def _is_on_main_diagonal(self, r: int, c: int) -> bool:
        return r == c

    def _is_on_anti_diagonal(self, r: int, c: int) -> bool:
        return r + c == 4

    def _get_available_positions_for_number(self, number: int) -> List[Tuple[int, int]]:
        """
        Level 2 rules as you currently coded:
        - Blue cells: ends of row/col for that inner number position
        - Yellow corners: only if number is on diagonal and is corner of inner (0,0),(0,4),(4,0),(4,4)
        """
        if number > 25 or number < 2:
            return []

        inner_pos = self._find_position_inner(number)
        if not inner_pos:
            return []

        r, c = inner_pos
        available_positions = []

        outer_r = r + 1
        outer_c = c + 1

        # Column ends
        if self.ring[0][outer_c] == 0:
            available_positions.append((0, outer_c))
        if self.ring[6][outer_c] == 0:
            available_positions.append((6, outer_c))

        # Row ends
        if self.ring[outer_r][0] == 0:
            available_positions.append((outer_r, 0))
        if self.ring[outer_r][6] == 0:
            available_positions.append((outer_r, 6))

        on_main = self._is_on_main_diagonal(r, c)
        on_anti = self._is_on_anti_diagonal(r, c)

        if on_main:
            if (r, c) == (0, 0) and self.ring[0][0] == 0:
                available_positions.append((0, 0))
            if (r, c) == (4, 4) and self.ring[6][6] == 0:
                available_positions.append((6, 6))

        if on_anti:
            if (r, c) == (0, 4) and self.ring[0][6] == 0:
                available_positions.append((0, 6))
            if (r, c) == (4, 0) and self.ring[6][0] == 0:
                available_positions.append((6, 0))

        return available_positions

    def _calculate_all_available_positions(self) -> None:
        self.level2_available_positions = {}
        for num in range(2, 26):
            self.level2_available_positions[num] = self._get_available_positions_for_number(num)

    def place_on_ring_ui_only(self, r: int, c: int, value: int) -> bool:
        if not (0 <= r < 7 and 0 <= c < 7):
            return False
        if not self.is_ring_cell(r, c):
            return False
        if not self.ring_cell_empty(r, c):
            return False
        if value in self.get_placed_outer_numbers():
            return False

        available_positions = self.level2_available_positions.get(value, [])
        if (r, c) not in available_positions:
            return False

        # Place
        self.ring[r][c] = value
        self.correct_moves += 1

        # Recompute next valid positions
        self._calculate_all_available_positions()

        # Save post-move state
        self._save_to_history("ring_move")
        return True

    def clear_ring(self) -> None:
        self.ring = [[0 for _ in range(7)] for _ in range(7)]
        self.current_outer_number = 2
        self._calculate_all_available_positions()
        self._save_to_history("clear_ring")

    def is_level2_complete(self) -> bool:
        placed_count = 0
        for r in range(7):
            for c in range(7):
                if self.is_ring_cell(r, c) and self.ring[r][c] != 0:
                    placed_count += 1
        return placed_count == 24

    # -------------------------
    # Save / Load state
    # -------------------------
    def get_state(self) -> dict:
        return self._snapshot_state()

    def set_state(self, state: dict) -> None:
        self._restore_snapshot(state)

        # Safety: ensure L2 positions computed if needed
        if self.level == 2 and not self.level2_available_positions:
            self._calculate_all_available_positions()

        # Ensure history has at least one baseline snapshot
        if not self.move_history:
            self._save_to_history("loaded_initial")

    # -------------------------
    # Completion data (GUI must set player_name)
    # -------------------------
    def build_completion_data(self, elapsed_time: float) -> dict:
        if not self.player_name:
            raise ValueError("player_name must be set before building completion data")

        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "Name": self.player_name,
            "Completed At": formatted_time,
            "Completion Seconds": elapsed_time,
            "Correct Moves": self.correct_moves,
            "Invalid Moves": self.invalid_moves,
            "Game Level": self.level,
            "Score": self.score,
            "Time Limit": self.get_time_limit(self.level),
            "Time Score Delta": self.time_bonus_last,
            "Board": copy.deepcopy(self.board),
            "Ring": copy.deepcopy(self.ring),
        }

    def is_personal_best(self, data: dict, player_name: str, current_time_seconds: float, level: int) -> bool:
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