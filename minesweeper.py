"""
Minesweeper - a classic Minesweeper game with a tkinter GUI.

Run with:  python minesweeper.py
Requires:  Python 3.8+ (tkinter ships with the standard installer)
"""

import json
import os
import random
import sys
import time
import tkinter as tk
from tkinter import messagebox

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DIFFICULTIES = {
    # name: (rows, cols, mines)
    "Beginner": (9, 9, 10),
    "Intermediate": (16, 16, 40),
    "Expert": (16, 30, 99),
}

CELL = 32  # pixel size of one cell

# Colours
BG = "#2b2d31"
PANEL_BG = "#1e1f22"
UNREVEALED = "#9aa5b1"
UNREVEALED_LIGHT = "#d5dbe1"
UNREVEALED_DARK = "#66707b"
REVEALED = "#e9edf1"
REVEALED_LINE = "#b8c0c9"
MINE_HIT = "#ff5252"
DIGIT_BG = "#000000"
DIGIT_FG = "#ff3b30"

NUM_COLORS = {
    1: "#1976d2",
    2: "#2e7d32",
    3: "#d32f2f",
    4: "#6a1b9a",
    5: "#e65100",
    6: "#00838f",
    7: "#212121",
    8: "#757575",
}

BEST_FILE = os.path.join(os.path.expanduser("~"), ".minesweeper_best.json")


# --------------------------------------------------------------------------- #
# Game logic (no GUI code here, so it is easy to test)
# --------------------------------------------------------------------------- #

class Board:
    READY, PLAYING, WON, LOST = "ready", "playing", "won", "lost"

    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.reset()

    def reset(self):
        self.state = Board.READY
        self.has_mine = [[False] * self.cols for _ in range(self.rows)]
        self.adjacent = [[0] * self.cols for _ in range(self.rows)]
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        self.flagged = [[False] * self.cols for _ in range(self.rows)]
        self.revealed_count = 0
        self.flag_count = 0
        self.hit = None  # (r, c) of the mine that was clicked

    # -- helpers ----------------------------------------------------------- #

    def neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def _place_mines(self, safe_r, safe_c):
        """Place mines after the first click so the first click is always safe
        (and, when there is room, opens up an area)."""
        forbidden = {(safe_r, safe_c), *self.neighbors(safe_r, safe_c)}
        cells = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        candidates = [cell for cell in cells if cell not in forbidden]
        if len(candidates) < self.mines:  # tiny board / many mines
            candidates = [cell for cell in cells if cell != (safe_r, safe_c)]
        for r, c in random.sample(candidates, self.mines):
            self.has_mine[r][c] = True
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.has_mine[r][c]:
                    self.adjacent[r][c] = sum(
                        self.has_mine[nr][nc] for nr, nc in self.neighbors(r, c)
                    )

    # -- actions ----------------------------------------------------------- #

    def reveal(self, r, c):
        """Reveal a cell. Returns the list of cells whose look changed."""
        if self.state in (Board.WON, Board.LOST):
            return []
        if self.revealed[r][c] or self.flagged[r][c]:
            return []
        if self.state == Board.READY:
            self._place_mines(r, c)
            self.state = Board.PLAYING

        if self.has_mine[r][c]:
            self.state = Board.LOST
            self.hit = (r, c)
            return [(r, c)]

        changed = []
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if self.revealed[cr][cc] or self.flagged[cr][cc]:
                continue
            self.revealed[cr][cc] = True
            self.revealed_count += 1
            changed.append((cr, cc))
            if self.adjacent[cr][cc] == 0:
                for nr, nc in self.neighbors(cr, cc):
                    if not self.revealed[nr][nc] and not self.has_mine[nr][nc]:
                        stack.append((nr, nc))

        if self.revealed_count == self.rows * self.cols - self.mines:
            self.state = Board.WON
        return changed

    def toggle_flag(self, r, c):
        if self.state not in (Board.READY, Board.PLAYING) or self.revealed[r][c]:
            return False
        self.flagged[r][c] = not self.flagged[r][c]
        self.flag_count += 1 if self.flagged[r][c] else -1
        return True

    def chord(self, r, c):
        """Click a revealed number whose flag count matches it to reveal all
        its unflagged neighbours at once."""
        if self.state != Board.PLAYING or not self.revealed[r][c]:
            return []
        if self.adjacent[r][c] == 0:
            return []
        flags = sum(self.flagged[nr][nc] for nr, nc in self.neighbors(r, c))
        if flags != self.adjacent[r][c]:
            return []
        changed = []
        for nr, nc in self.neighbors(r, c):
            if not self.flagged[nr][nc] and not self.revealed[nr][nc]:
                changed += self.reveal(nr, nc)
                if self.state == Board.LOST:
                    break
        return changed


# --------------------------------------------------------------------------- #
# Best-time storage
# --------------------------------------------------------------------------- #

def load_best():
    try:
        with open(BEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: float(v) for k, v in data.items() if k in DIFFICULTIES}
    except (OSError, ValueError, TypeError):
        return {}


def save_best(best):
    try:
        with open(BEST_FILE, "w", encoding="utf-8") as f:
            json.dump(best, f)
    except OSError:
        pass  # not critical


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #

class MinesweeperApp:
    def __init__(self, root):
        self.root = root
        root.title("Minesweeper")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.difficulty = tk.StringVar(value="Beginner")
        self.best = load_best()
        self.board = None
        self.start_time = None
        self.elapsed = 0
        self.timer_job = None
        self.face = "smile"

        self._build_menu()

        self.top = tk.Frame(root, bg=BG, padx=10, pady=10)
        self.top.pack(fill="x")
        self.mine_label = self._digit_label(self.top)
        self.mine_label.pack(side="left")
        self.face_canvas = tk.Canvas(
            self.top, width=44, height=44, bg=BG, highlightthickness=0, cursor="hand2"
        )
        self.face_canvas.pack(side="left", expand=True)
        self.face_canvas.bind("<Button-1>", lambda e: self.new_game())
        self.time_label = self._digit_label(self.top)
        self.time_label.pack(side="right")

        self.canvas = None
        self.new_game()

        root.bind("<F2>", lambda e: self.new_game())

    # -- widgets ----------------------------------------------------------- #

    def _digit_label(self, parent):
        return tk.Label(
            parent,
            text="000",
            font=("Courier", 22, "bold"),
            fg=DIGIT_FG,
            bg=DIGIT_BG,
            width=4,
            relief="sunken",
            bd=3,
        )

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        game = tk.Menu(menubar, tearoff=0)
        game.add_command(label="New Game  (F2)", command=self.new_game)
        game.add_separator()
        for name, (r, c, m) in DIFFICULTIES.items():
            game.add_radiobutton(
                label=f"{name}  ({c}x{r}, {m} mines)",
                variable=self.difficulty,
                value=name,
                command=self.new_game,
            )
        game.add_separator()
        game.add_command(label="Best Times", command=self.show_best)
        game.add_separator()
        game.add_command(label="Quit", command=self.root.destroy)
        menubar.add_cascade(label="Game", menu=game)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="How to Play", command=self.show_help)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.root.config(menu=menubar)

    # -- game flow --------------------------------------------------------- #

    def new_game(self):
        self._stop_timer()
        rows, cols, mines = DIFFICULTIES[self.difficulty.get()]
        self.board = Board(rows, cols, mines)
        self.start_time = None
        self.elapsed = 0
        self.face = "smile"

        if self.canvas is not None:
            self.canvas.destroy()
        self.canvas = tk.Canvas(
            self.root,
            width=cols * CELL,
            height=rows * CELL,
            bg=PANEL_BG,
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=(0, 10))
        self.canvas.bind("<Button-1>", self.on_left_click)
        # Right click is Button-3 on Windows/Linux and Button-2 on macOS.
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Button-2>", self.on_right_click)
        self.canvas.bind("<Control-Button-1>", self.on_right_click)

        self.draw_all()
        self.update_counters()
        self.draw_face()

    def _start_timer(self):
        self.start_time = time.time()
        self._tick()

    def _tick(self):
        if self.start_time is None or self.board.state != Board.PLAYING:
            return
        self.elapsed = time.time() - self.start_time
        self.update_counters()
        self.timer_job = self.root.after(100, self._tick)

    def _stop_timer(self):
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def update_counters(self):
        remaining = self.board.mines - self.board.flag_count
        self.mine_label.config(text=f"{max(min(remaining, 999), -99):03d}")
        self.time_label.config(text=f"{min(int(self.elapsed), 999):03d}")

    # -- events ------------------------------------------------------------ #

    def _cell_at(self, event):
        c, r = event.x // CELL, event.y // CELL
        if 0 <= r < self.board.rows and 0 <= c < self.board.cols:
            return r, c
        return None

    def on_left_click(self, event):
        pos = self._cell_at(event)
        if pos is None:
            return
        r, c = pos
        b = self.board
        if b.state in (Board.WON, Board.LOST):
            return
        if b.revealed[r][c]:
            changed = b.chord(r, c)
        else:
            was_ready = b.state == Board.READY
            changed = b.reveal(r, c)
            if was_ready and b.state == Board.PLAYING:
                self._start_timer()
        self._after_move(changed)

    def on_right_click(self, event):
        pos = self._cell_at(event)
        if pos is None:
            return "break"
        r, c = pos
        if self.board.toggle_flag(r, c):
            self.draw_cell(r, c)
            self.update_counters()
        return "break"

    def _after_move(self, changed):
        b = self.board
        for r, c in changed:
            self.draw_cell(r, c)
        self.update_counters()

        if b.state == Board.LOST:
            self._stop_timer()
            self.face = "dead"
            self.draw_all()  # reveal every mine
            self.draw_face()
        elif b.state == Board.WON:
            self._stop_timer()
            self.face = "cool"
            # auto-flag the remaining mines
            for r in range(b.rows):
                for c in range(b.cols):
                    if b.has_mine[r][c] and not b.flagged[r][c]:
                        b.flagged[r][c] = True
                        b.flag_count += 1
            self.draw_all()
            self.update_counters()
            self.draw_face()
            self.root.after(150, self._announce_win)

    def _announce_win(self):
        name = self.difficulty.get()
        t = round(self.elapsed, 1)
        previous = self.best.get(name)
        if previous is None or t < previous:
            self.best[name] = t
            save_best(self.best)
            messagebox.showinfo("You win!", f"New best time on {name}: {t} s")
        else:
            messagebox.showinfo(
                "You win!", f"Cleared in {t} s.\nBest on {name}: {previous} s"
            )

    # -- drawing ----------------------------------------------------------- #

    def draw_all(self):
        self.canvas.delete("all")
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                self.draw_cell(r, c)

    def draw_cell(self, r, c):
        b = self.board
        cv = self.canvas
        x1, y1 = c * CELL, r * CELL
        x2, y2 = x1 + CELL, y1 + CELL
        tag = f"cell_{r}_{c}"
        cv.delete(tag)
        game_over = b.state in (Board.LOST, Board.WON)

        if b.revealed[r][c]:
            cv.create_rectangle(
                x1, y1, x2, y2, fill=REVEALED, outline=REVEALED_LINE, tags=tag
            )
            n = b.adjacent[r][c]
            if n:
                cv.create_text(
                    x1 + CELL / 2,
                    y1 + CELL / 2,
                    text=str(n),
                    fill=NUM_COLORS[n],
                    font=("Helvetica", 15, "bold"),
                    tags=tag,
                )
            return

        # Mines shown after losing
        if b.state == Board.LOST and b.has_mine[r][c] and not b.flagged[r][c]:
            bg = MINE_HIT if b.hit == (r, c) else REVEALED
            cv.create_rectangle(
                x1, y1, x2, y2, fill=bg, outline=REVEALED_LINE, tags=tag
            )
            self._draw_mine(x1, y1, tag)
            return

        # Wrong flag after losing
        if b.state == Board.LOST and b.flagged[r][c] and not b.has_mine[r][c]:
            cv.create_rectangle(
                x1, y1, x2, y2, fill=REVEALED, outline=REVEALED_LINE, tags=tag
            )
            self._draw_mine(x1, y1, tag)
            cv.create_line(x1 + 5, y1 + 5, x2 - 5, y2 - 5, fill=MINE_HIT, width=3, tags=tag)
            cv.create_line(x1 + 5, y2 - 5, x2 - 5, y1 + 5, fill=MINE_HIT, width=3, tags=tag)
            return

        # Normal unrevealed (raised) cell
        cv.create_rectangle(x1, y1, x2, y2, fill=UNREVEALED, outline="", tags=tag)
        cv.create_polygon(
            x1, y1, x2, y1, x2 - 3, y1 + 3, x1 + 3, y1 + 3, x1 + 3, y2 - 3, x1, y2,
            fill=UNREVEALED_LIGHT, outline="", tags=tag,
        )
        cv.create_polygon(
            x2, y2, x2, y1, x2 - 3, y1 + 3, x2 - 3, y2 - 3, x1 + 3, y2 - 3, x1, y2,
            fill=UNREVEALED_DARK, outline="", tags=tag,
        )
        if b.flagged[r][c]:
            self._draw_flag(x1, y1, tag)

    def _draw_flag(self, x, y, tag):
        cv = self.canvas
        cv.create_polygon(
            x + 11, y + 7, x + 23, y + 12, x + 11, y + 17,
            fill="#e53935", outline="", tags=tag,
        )
        cv.create_line(x + 11, y + 7, x + 11, y + 25, fill="#111", width=2, tags=tag)
        cv.create_rectangle(x + 7, y + 25, x + 20, y + 27, fill="#111", outline="", tags=tag)

    def _draw_mine(self, x, y, tag):
        cv = self.canvas
        cx, cy = x + CELL / 2, y + CELL / 2
        for dx, dy in ((0, -11), (0, 11), (-11, 0), (11, 0), (-8, -8), (8, 8), (-8, 8), (8, -8)):
            cv.create_line(cx, cy, cx + dx, cy + dy, fill="#111", width=2, tags=tag)
        cv.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill="#111", outline="", tags=tag)
        cv.create_oval(cx - 4, cy - 4, cx - 1, cy - 1, fill="#fff", outline="", tags=tag)

    def draw_face(self):
        cv = self.face_canvas
        cv.delete("all")
        cv.create_oval(3, 3, 41, 41, fill="#ffd54f", outline="#b28900", width=2)
        if self.face == "cool":
            cv.create_rectangle(9, 14, 20, 22, fill="#111", outline="")
            cv.create_rectangle(24, 14, 35, 22, fill="#111", outline="")
            cv.create_line(20, 17, 24, 17, fill="#111", width=2)
            cv.create_arc(11, 18, 33, 36, start=200, extent=140, style="arc", outline="#111", width=2)
        elif self.face == "dead":
            for ex in (15, 29):
                cv.create_line(ex - 4, 13, ex + 4, 21, fill="#111", width=2)
                cv.create_line(ex - 4, 21, ex + 4, 13, fill="#111", width=2)
            cv.create_arc(12, 26, 32, 40, start=20, extent=140, style="arc", outline="#111", width=2)
        else:
            cv.create_oval(13, 14, 18, 22, fill="#111", outline="")
            cv.create_oval(26, 14, 31, 22, fill="#111", outline="")
            cv.create_arc(11, 14, 33, 36, start=200, extent=140, style="arc", outline="#111", width=2)

    # -- dialogs ----------------------------------------------------------- #

    def show_best(self):
        lines = []
        for name in DIFFICULTIES:
            t = self.best.get(name)
            lines.append(f"{name}: {t} s" if t is not None else f"{name}: --")
        messagebox.showinfo("Best Times", "\n".join(lines))

    def show_help(self):
        messagebox.showinfo(
            "How to Play",
            "Goal: reveal every cell that does not hold a mine.\n\n"
            "Left click   - reveal a cell\n"
            "Right click  - place / remove a flag\n"
            "  (Mac: right click or Ctrl+click)\n"
            "Left click on a number whose flags match it - reveal all its\n"
            "  other neighbours at once (chording)\n"
            "F2 - new game\n\n"
            "A number tells you how many mines touch that cell.\n"
            "Your first click is always safe.",
        )


def main():
    root = tk.Tk()
    MinesweeperApp(root)
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
