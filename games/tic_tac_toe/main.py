import tkinter as tk
from tkinter import messagebox
import random

class TicTacToeAI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tic-Tac-Toe")
        
        self.human = "X"
        self.ai = "O"
        self.current_player = self.human  # Human turn first
        self.buttons = []
        
        # Matrix of buttons in 3x3 mesh 
        for r in range(3):
            row_buttons = []
            for c in range(3):
                btn = tk.Button(root, text="", font=("Arial", 20, "bold"), width=5, height=2,
                                command=lambda row=r, col=c: self.human_move(row, col))
                btn.grid(row=r, column=c, padx=5, pady=5)
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

    def human_move(self, row, col):
        # If AI's turn or cell is used - ignore click
        if self.current_player != self.human or self.buttons[row][col]["text"] != "":
            return
            
        # Human move
        self.make_move(row, col, self.human, "blue")
        
        if self.check_game_over():
            return
            
        # Giving the turn to AI
        self.current_player = self.ai
        self.root.after(500, self.ai_move)  # A slight delay for realism.

    def ai_move(self):
        # Finding the best move, using Mini-Max algorithm
        best_score = -float('inf')
        best_move = None
        
        for r in range(3):
            for c in range(3):
                if self.buttons[r][c]["text"] == "":
                    # Trying to do the move
                    self.buttons[r][c]["text"] = self.ai
                    score = self.minimax(0, False)
                    # Undo the move 
                    self.buttons[r][c]["text"] = ""
                    
                    if score > best_score:
                        best_score = score
                        best_move = (r, c)
                        
        if best_move:
            self.make_move(best_move[0], best_move[1], self.ai, "red")
            
        if self.check_game_over():
            return
            
        self.current_player = self.human

    def minimax(self, depth, is_maximizing):
        # Basic conditions checup: is this move end the game?
        if self.evaluate_winner(self.ai):
            return 10 - depth
        if self.evaluate_winner(self.human):
            return depth - 10
        if self.is_board_full():
            return 0
            
        if is_maximizing:
            best_score = -float('inf')
            for r in range(3):
                for c in range(3):
                    if self.buttons[r][c]["text"] == "":
                        self.buttons[r][c]["text"] = self.ai
                        score = self.minimax(depth + 1, False)
                        self.buttons[r][c]["text"] = ""
                        best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for r in range(3):
                for c in range(3):
                    if self.buttons[r][c]["text"] == "":
                        self.buttons[r][c]["text"] = self.human
                        score = self.minimax(depth + 1, True)
                        self.buttons[r][c]["text"] = ""
                        best_score = min(score, best_score)
            return best_score

    def make_move(self, row, col, player, color):
        self.buttons[row][col]["text"] = player
        self.buttons[row][col]["fg"] = color

    def check_game_over(self):
        if self.evaluate_winner(self.human):
            messagebox.showinfo("WIN!", "You are bit the AI!")
            self.reset_game()
            return True
        if self.evaluate_winner(self.ai):
            messagebox.showinfo("Fail", "The AI is win!")
            self.reset_game()
            return True
        if self.is_board_full():
            messagebox.showinfo("The draw", "The draw!")
            self.reset_game()
            return True
        return False

    def evaluate_winner(self, p):
        b = self.buttons
        # Checking the rows, collumns and diagnals for the player "p"
        for i in range(3):
            if b[i][0]["text"] == b[i][1]["text"] == b[i][2]["text"] == p: return True
            if b[0][i]["text"] == b[1][i]["text"] == b[2][i]["text"] == p: return True
        if b[0][0]["text"] == b[1][1]["text"] == b[2][2]["text"] == p: return True
        if b[0][2]["text"] == b[1][1]["text"] == b[2][0]["text"] == p: return True
        return False

    def is_board_full(self):
        for row in self.buttons:
            for btn in row:
                if btn["text"] == "":
                    return False
        return True

    def reset_game(self):
        self.current_player = self.human
        for row in self.buttons:
            for btn in row:
                btn["text"] = ""
                btn["fg"] = "black"

def main():
    root = tk.Tk()
    game = TicTacToeAI(root)
    root.mainloop()