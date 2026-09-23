import tkinter as tk
from tkinter import messagebox
import random

class Minesweeper:
    def __init__(self, root):
        self.root = root
        self.root.title("Сапер")
        
        self.rows = 20
        self.cols = 20
        self.mines_count = 70 # 70
        
        self.buttons = []
        self.mines = set()       # Координаты мин (row, col)
        self.revealed = set()    # Открытые клетки (row, col)
        self.flags = set()       # Клетки с флажками (row, col)
        
        self.first_click = True  # Флаг для безопасного первого клика
        self.game_over = False
        self.color_of_bombs = 'red'

        self.create_widgets()

    def create_widgets(self):
        # Создаем сетку кнопок
        for r in range(self.rows):
            row_buttons = []
            for c in range(self.cols):
                btn = tk.Button(self.root, text="", font=("Arial", 12, "bold"), width=3, height=1,
                                bg="#d1d1d1", relief="raised")
                # Левый клик — открыть клетку
                btn.bind("<Button-1>", lambda event, row=r, col=c: self.left_click(row, col))
                # Правый клик — поставить флажок
                btn.bind("<Button-3>", lambda event, row=r, col=c: self.right_click(row, col))
                
                btn.grid(row=r, column=c, padx=1, pady=1)
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

    def generate_mines(self, start_row, start_col):
        # Мины генерируются только после первого клика
        # Исключаем из генерации саму стартовую клетку и её соседей
        forbidden_cells = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                forbidden_cells.add((start_row + dr, start_col + dc))

        while len(self.mines) < self.mines_count:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            if (r, c) not in forbidden_cells:
                self.mines.add((r, c))

    def left_click(self, row, col):
        if self.game_over or (row, col) in self.flags or (row, col) in self.revealed:
            return

        # Если это первый клик — генерируем мины вокруг этой точки
        if self.first_click:
            self.first_click = False
            self.generate_mines(row, col)

        # Наступили на мину — проигрыш
        if (row, col) in self.mines:
            self.show_mines()
            self.game_over = True
            messagebox.showerror("Бум!", "Вы подорвались на мине!")
            self.restart_window()  # Полное пересоздание окна
            return

        # Открываем клетку
        self.reveal_cell(row, col)

        # Проверка на победу
        if len(self.revealed) == (self.rows * self.cols) - self.mines_count:
            self.color_of_bombs = 'green'
            self.show_mines()
            self.game_over = True
            messagebox.showinfo("Победа!", "Поздравляем! Вы очистили поле!")
            self.restart_window()  # Полное пересоздание окна

    def right_click(self, row, col):
        if self.game_over or (row, col) in self.revealed:
            return

        btn = self.buttons[row][col]
        if (row, col) in self.flags:
            self.flags.remove((row, col))
            btn.config(text="", bg="#d1d1d1")
        else:
            self.flags.add((row, col))
            btn.config(text="🚩", fg="red")

    def count_around(self, row, col):
        count = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr, nc) in self.mines:
                        count += 1
        return count

    def reveal_cell(self, row, col):
        if (row, col) in self.revealed or (row, col) in self.flags:
            return

        self.revealed.add((row, col))
        btn = self.buttons[row][col]
        
        # Удаляем (скрываем) саму кнопку, чтобы не было артефактов
        btn.grid_forget()

        mines_around = self.count_around(row, col)

        if mines_around > 0:
            colors = {1: "blue", 2: "green", 3: "red", 4: "purple", 5: "maroon", 6: "turquoise", 7: "black", 8: "gray"}
            # Вместо кнопки рисуем плоский текст (Label)
            lbl = tk.Label(self.root, text=str(mines_around), font=("Arial", 12, "bold"), 
                           fg=colors.get(mines_around, "black"), width=3, height=1, bg="#e1e1e1", relief="flat")
            lbl.grid(row=row, column=col, padx=1, pady=1)
        else:
            # Если вокруг пусто, оставляем просто серый квадрат (пустой Label)
            lbl = tk.Label(self.root, text="", width=3, height=1, bg="#e1e1e1", relief="flat")
            lbl.grid(row=row, column=col, padx=1, pady=1)
            
            # Рекурсивно открываем соседей
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        self.reveal_cell(nr, nc)

    def show_mines(self):
        # Показываем все мины перед закрытием раунда
        for r, c in self.mines:
            if (r, c) not in self.flags:
                self.buttons[r][c].config(text="💣", bg=self.color_of_bombs, relief="sunken")

    def restart_window(self):
        # Полностью уничтожаем текущие виджеты окна и пересоздаем класс игры
        for widget in self.root.winfo_children():
            widget.destroy()
        # Переинициализируем игру заново в том же окне
        self.color_of_bombs = 'red'
        self.__init__(self.root)

def main():
    root = tk.Tk()
    game = Minesweeper(root)
    root.mainloop()
