
import json

class SaveState:
  def __init__(self, filename="SavedState.json"):
    self.filename = filename

  def save_game(self, data):
    with open(self.filename, "w") as file:
      json.dump(data, file)
    print("\nGame saved\n")

  def load_game(self):
    try:
      with open (self.filename, "r") as file:
        data = json.load(file)
      print("Game loaded")
      return data
    except FileNotFoundError:
      print("No Game Saved")
      return None


class Logic:
  def __init__(self):
    self.board = [[0 for _ in range(5)] for _ in range(5)]
    self.score = 0

  def previous_input(self):
    return max(max(row) for row in self.board)
  
  def find_position(self, target):
    for row in range(len(self.board)):
      for column in range(len(self.board[row])):
        if self.board[row][column] == target:
          return row, column
    return None

  def make_move(self, row, column, value):
    if not (0 <= row < 5 and 0 <= column < 5):
      return 0
    prev_value = self.previous_input()
    if (value - 1) != prev_value:
      return 0
    prev_position = self.find_position(prev_value)
    if prev_position is None:
      return 0
    if self.board[row][column] != 0:
      return 0
    self.board[row][column] = value
    row_p, column_p = prev_position
    if abs(row - row_p) == 1 and abs(column - column_p) == 1:
      self.score += 1
    return 1

  def get_state(self):
    return {"board": self.board, "score": self.score}
  
  def set_state(self, state):
    self.board = state["board"]
    self.score = state["score"]


class Interface:
  def __init__(self):
    self.logic = Logic()
    self.save_state = SaveState()

  def menu(self):
    print("Menu\n")
    print("1. Make a Move\n")
    print("2. Load Game\n")
    print("3. Exit\n")

  def board_display(self):
    print("Board: \n")
    for row in self.logic.board:
      print(" ".join(f"{val:2}" for val in row))
    print()
    print(f"Score: {self.logic.score}\n")

  def end_program(self):
    print("Game Over! Thanks for playing!")
    return

  def main_menu(self):
    self.menu() 
    user_input = input("Enter your choice: ")

    if user_input == "1":
      self.play_game()

    elif user_input == "2":
      data = self.save_state.load_game()
      if data:
        self.logic.set_state(data)
      self.board_display()
      self.play_game()

    elif (user_input == "3"):
      self.end_program()
    
    else:
      print("Your choice is not valid. Goodbye!\n")

  def play_game(self):
    while True:
      try:
        row = int(input("Enter a row(0-4): "))
        column = int(input("Enter a column(0-4): "))
        value = int(input("Enter the number to place: "))
        result = self.logic.make_move(row, column, value)
        if result == 0:
          self.end_program()
          return
        self.board_display()

        user_input = input("Enter S to save, E to exit, or press Enter to continue the game\n")
        if user_input.upper() == "S":
          self.save_state.save_game(self.logic.get_state())
        elif user_input.upper() == "E":
          self.end_program()
          return
        else: 
          continue

      except ValueError:
        print("Please only enter numbers.")


if __name__ == "__main__":
  interface = Interface()
  interface.board_display()
  interface.main_menu()