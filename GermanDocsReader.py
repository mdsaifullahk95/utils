import tkinter as tk
from tkinter import ttk
from deep_translator import GoogleTranslator

class ModernReader:
    def __init__(self, root):
        self.root = root
        self.root.title("LingoHover: German Reader")
        self.root.geometry("900x600")
        self.root.configure(bg="#2d2d2d")  # Dark background

        # Style Configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TButton", padding=6, font=("Segoe UI", 10))
        self.style.configure("TLabel", background="#2d2d2d", foreground="#ecf0f1")

        # --- Top Input Section ---
        self.top_frame = tk.Frame(root, bg="#2d2d2d", pady=10)
        self.top_frame.pack(fill="x")

        ttk.Label(self.top_frame, text="Paste German Text:").pack()
        self.input_text = tk.Text(self.top_frame, height=6, bg="#3d3d3d", fg="white", 
                                  insertbackground="white", relief="flat", padx=10, pady=10)
        self.input_text.pack(padx=20, pady=5, fill="x")

        self.btn = ttk.Button(self.top_frame, text="Analyze Text", command=self.process_text)
        self.btn.pack(pady=5)

        # --- Main Reader Section (with Left Scrollbar) ---
        self.container = tk.Frame(root, bg="#2d2d2d")
        self.container.pack(expand=True, fill="both", padx=20, pady=10)

        # The Display Widget
        self.display = tk.Text(self.container, wrap="word", state="disabled",
                               font=("Georgia", 13), bg="#fdfdfd", fg="#2c3e50",
                               padx=20, pady=20, spacing1=8, spacing2=3, relief="flat")

        # The Scrollbar (Placed on the left)
        self.scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=self.display.yview)
        self.display.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="left", fill="y")
        self.display.pack(side="right", expand=True, fill="both")

        # --- Tooltip Setup ---
        self.tooltip = tk.Label(root, text="", bg="#f1c40f", fg="#2c3e50", 
                                font=("Segoe UI", 10, "bold"), relief="flat", 
                                padx=8, pady=4, borderwidth=0)
        
        self.cache = {}

    def process_text(self):
        raw_text = self.input_text.get("1.0", "end-1c")
        lines = raw_text.splitlines()

        self.display.config(state="normal")
        self.display.delete("1.0", "end")

        for line in lines:
            words = line.split()
            for word in words:
                clean_word = "".join(filter(str.isalnum, word))
                if not clean_word: continue
                
                tag_name = f"tag_{clean_word}_{self.display.index('insert').replace('.', '_')}"
                
                self.display.insert("end", word + " ")
                start_index = f"insert - {len(word)+1}c"
                end_index = "insert - 1c"
                self.display.tag_add(tag_name, start_index, end_index)
                
                # Visual feedback on hover: change color
                self.display.tag_bind(tag_name, "<Enter>", lambda e, w=clean_word, t=tag_name: self.on_hover(e, w, t))
                self.display.tag_bind(tag_name, "<Leave>", lambda e, t=tag_name: self.on_leave(e, t))

            self.display.insert("end", "\n")

        self.display.config(state="disabled")

    def on_hover(self, event, word, tag_name):
        self.display.tag_configure(tag_name, foreground="#e67e22", underline=True)
        
        if word not in self.cache:
            try:
                # Adding a '...' while loading
                self.tooltip.config(text="...")
                res = GoogleTranslator(source='de', target='en').translate(word)
                self.cache[word] = res
            except:
                self.cache[word] = "Error"

        self.tooltip.config(text=self.cache[word])
        self.tooltip.place(x=event.x_root - self.root.winfo_rootx() + 15, 
                           y=event.y_root - self.root.winfo_rooty() + 15)

    def on_leave(self, event, tag_name):
        self.display.tag_configure(tag_name, foreground="#2c3e50", underline=False)
        self.tooltip.place_forget()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernReader(root)
    root.mainloop()
