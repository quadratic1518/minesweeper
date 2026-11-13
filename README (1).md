# Minesweeper (Python + tkinter)

A classic Minesweeper game with a clean graphical interface, written in pure Python. No third-party packages needed.

## Features

- Three difficulty levels: Beginner (9x9, 10 mines), Intermediate (16x16, 40 mines), Expert (30x16, 99 mines)
- First click is always safe
- Flood-fill reveal of empty areas
- Flagging with a live mine counter
- Chording: click a satisfied number to open all its neighbours
- Timer and a face button that reacts to win/loss (click it to restart)
- Best times saved per difficulty (stored in `~/.minesweeper_best.json`)
- Custom-drawn cells, so it looks the same on Windows, macOS and Linux

## Requirements

- Python 3.8 or newer
- tkinter (included with the standard Python installers for Windows and macOS)

On Linux, install tkinter if it is missing:

```bash
# Debian / Ubuntu
sudo apt install python3-tk
# Fedora
sudo dnf install python3-tkinter
```

## How to run

```bash
python minesweeper.py
```

On macOS / Linux you may need `python3 minesweeper.py`.

## Controls

| Action | Control |
| --- | --- |
| Reveal a cell | Left click |
| Place / remove flag | Right click (Mac: right click or Ctrl + click) |
| Chord (open neighbours) | Left click on a number with matching flags |
| New game | Click the face or press `F2` |
| Change difficulty | `Game` menu |

## Project structure

```
minesweeper.py   # game logic (Board class) and GUI (MinesweeperApp class)
README.md
.gitignore
```

## License

Free to use and modify for learning and personal projects.
