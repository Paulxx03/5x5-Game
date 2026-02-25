import json

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

    def save_completed_game(self, data: dict) -> None:
        with open(self.completionsfile, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)