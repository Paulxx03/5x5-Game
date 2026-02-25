# 5x5-Game
CEN 4020 – Project 2

This project is a graphical, grid-based game developed for CEN 4020. The game features a GUI-based interface that allows players to interactively fill a 5×5 grid across two distinct levels. In the first level, players complete the 5×5 grid, while the second level expands the challenge by requiring players to fill the outer ring surrounding the original 5×5 grid, forming the border of a 7×7 grid. Players must place numbers consecutively, and points are awarded only when a number is placed diagonally adjacent to the previously placed number. The UI displays the next required number, enforces sequential placement across both levels, and provides audio feedback for valid and invalid moves. Additionally, each level now supports an administrator-defined time limit. If a player completes a level within the time limit, the remaining unused time is converted into bonus points at a rate of one point per second. If the player exceeds the limit, one point is deducted for each extra second. This feature introduces an additional strategic element to gameplay by rewarding efficiency and penalizing delays.

The program is implemented in Python and is organized into modular objects and files to improve scalability and maintainability. The Logic component handles game rules, scoring, timing, and level progression, the Interface component manages all GUI interactions and user input, and the SaveState component handles saving and loading game and completion data. Supporting modules group tightly coupled functionality such as sound management and shared data structures into dedicated files, allowing the codebase to be more reusable and easier to maintain as new levels and features are introduced. The project was developed and tested on the Windows operating system using Python version 3.12.

To run the program, navigate to the project directory and execute the following command: py -3.12 Ass1.py

Gameplay updates:

A "Next Number" panel shows the required next value and invalid numbers are rejected with a warning.

Accepted placements play a confirmation sound; invalid placements play a buzzer.

A "Clear Board" control lets you restart at any time. In Level 1 you can keep the original 1 in place or randomize it; in Level 2 only the outer ring is cleared.

Players are notified when they achieve a new fastest completion time for a level, allowing them to track personal improvement across games.

The game records and displays judge statistics including average completion time, accuracy, and average score across players, enabling performance comparison between multiple participants.

Listed below are user stories 15 & 16:
As a player i want to be notified when i recieve my fastest time so that i know when i am improving at the game
As a judge i want the game to keep track of additional statistics (avg level completion time, accuracy, and score avg) so that i can compare performance between multiple players
