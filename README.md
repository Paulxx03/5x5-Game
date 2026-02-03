# 5x5-Game
CEN 4020 – Project 1

This project is a graphical, grid-based game developed for CEN 4020. The game features a GUI-based interface that allows players to interactively fill a 5×5 grid across two distinct levels. In the first level, players complete the 5×5 grid, while the second level expands the challenge by requiring players to fill the outer ring surrounding the original 5×5 grid, forming the border of a 7×7 grid. Players must place numbers consecutively, and points are awarded only when a number is placed diagonally adjacent to the previously placed number. The UI displays the next required number, enforces sequential placement across both levels, and provides audio feedback for valid and invalid moves.

The program is implemented in Python and is organized into three main objects: SaveState, Logic, and Interface. Each object is responsible for handling its respective component of the application, including game rules, user interaction, and saving completed game data. The project was developed and tested on the Windows operating system using Python version 3.12.

To run the program, navigate to the project directory and execute the following command: py -3.12 Ass1.py

Gameplay updates:
- A "Next Number" panel shows the required next value and invalid numbers are rejected with a warning.
- Accepted placements play a confirmation sound; invalid placements play a buzzer.
- A "Clear Board" control lets you restart at any time. In Level 1 you can keep the original 1 in place or randomize it; in Level 2 only the outer ring is cleared.
