import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
from google import genai
import threading
import re

# --- CONFIGURATION ---
# Replace with your free key from https://aistudio.google.com/
API_KEY = "AIzaSyCYQr3qfMCe1scDXY3uf4jfZV9wVrlvSWw"
client = genai.Client(api_key=API_KEY)

class LingoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("German Document Reader - Saif: AI German Workspace")
        self.root.geometry("1300x900")
        self.root.configure(bg="#1e1e1e")

        self.cache = {}
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # UI Styling
        self.style.configure("Menu.TButton", font=("Segoe UI", 12, "bold"), padding=20)
        self.style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), padding=5)
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        self.style.configure("TRadiobutton", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))

        self.main_container = tk.Frame(root, bg="#1e1e1e")
        self.main_container.pack(expand=True, fill="both")
        
        # State Variables
        self.translation_mode = tk.StringVar(value="word")
        
        self.show_landing_page()

    def clear_screen(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def show_landing_page(self):
        self.clear_screen()
        inner_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(inner_frame, text="German Transcript Reader", font=("Segoe UI", 32, "bold"), 
                 bg="#1e1e1e", fg="#3498db").pack(pady=20)
        
        ttk.Button(inner_frame, text="📖 Translation Reader", style="Menu.TButton", 
                   command=self.setup_translation_ui).pack(pady=10, fill="x")
        ttk.Button(inner_frame, text="✍️ AI Transcript Fixer", style="Menu.TButton", 
                   command=self.setup_transcript_ui).pack(pady=10, fill="x")

    def create_text_area(self, parent, is_reader=False):
        frame = tk.Frame(parent, bg="#1e1e1e")
        bg_color, fg_color = ("#ffffff", "#2c3e50") if is_reader else ("#2d2d2d", "#ecf0f1")
        font_config = ("Georgia", 13) if is_reader else ("Consolas", 11)
        pad_x, pad_y = (60, 40) if is_reader else (15, 15)
        
        txt = tk.Text(frame, wrap="word", font=font_config, bg=bg_color, fg=fg_color, 
                      insertbackground=fg_color, padx=pad_x, pady=pad_y, 
                      spacing1=10 if is_reader else 2, spacing2=4 if is_reader else 0,
                      relief="flat", borderwidth=0)
        
        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")
        txt.pack(side="right", expand=True, fill="both")
        return frame, txt

    # --- TRANSCRIPT CORRECTION LOGIC ---

    def setup_transcript_ui(self):
        self.clear_screen()
        nav = tk.Frame(self.main_container, bg="#1e1e1e")
        nav.pack(fill="x", padx=10, pady=5)
        ttk.Button(nav, text="← Back to Menu", command=self.show_landing_page).pack(side="left")

        workspace = tk.Frame(self.main_container, bg="#1e1e1e")
        workspace.pack(expand=True, fill="both", padx=10, pady=5)
        workspace.columnconfigure(0, weight=1); workspace.columnconfigure(1, weight=3); workspace.rowconfigure(0, weight=1)

        left_panel = tk.Frame(workspace, bg="#1e1e1e")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(left_panel, text="1. Paste Messy Transcript:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.fix_btn = ttk.Button(left_panel, text="✨ Run Gemini AI Fix", style="Action.TButton", command=self.start_fix_thread)
        self.fix_btn.pack(fill="x", pady=(5, 10))
        input_frame, self.trans_input = self.create_text_area(left_panel)
        input_frame.pack(expand=True, fill="both")

        right_panel = tk.Frame(workspace, bg="#1e1e1e")
        right_panel.grid(row=0, column=1, sticky="nsew")
        tk.Label(right_panel, text="2. Reconstructed German Document:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 46))
        output_frame, self.trans_output = self.create_text_area(right_panel, is_reader=True)
        output_frame.pack(expand=True, fill="both")

    def start_fix_thread(self):
        self.fix_btn.config(state="disabled", text="🤖 AI is Thinking...")
        threading.Thread(target=self.fix_transcript, daemon=True).start()

    def fix_transcript(self):
        raw_text = self.trans_input.get("1.0", "end-1c")
        if not raw_text.strip():
            self.root.after(0, lambda: self.fix_btn.config(state="normal", text="✨ Run Gemini AI Fix"))
            return
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Fix this broken German transcript. Add punctuation, fix all capitalization, and organize it into paragraphs. Return ONLY the corrected German text:\n\n{raw_text}"
            )
            final_text = response.text.strip()

            self.root.after(0, lambda: (self.trans_output.delete("1.0", "end"), 
                                        self.trans_output.insert("1.0", final_text),
                                        self.fix_btn.config(state="normal", text="✨ Run Gemini AI Fix")))
        
        except Exception as e:
            err = str(e)
            msg = "AI Limit reached. Wait 60s." if "429" in err or "EXHAUSTED" in err else f"Error: {err}"
            self.root.after(0, lambda: (messagebox.showwarning("API Limit", msg),
                                        self.fix_btn.config(state="normal", text="✨ Run Gemini AI Fix")))

    # --- TRANSLATION READER LOGIC ---

    def setup_translation_ui(self):
        self.clear_screen()
        nav = tk.Frame(self.main_container, bg="#1e1e1e")
        nav.pack(fill="x", padx=10, pady=5)
        ttk.Button(nav, text="← Back", command=self.show_landing_page).pack(side="left")
        
        mode_frame = tk.Frame(nav, bg="#1e1e1e")
        mode_frame.pack(side="right", padx=10)
        ttk.Radiobutton(mode_frame, text="Word", variable=self.translation_mode, value="word").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Sentence", variable=self.translation_mode, value="sentence").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Both", variable=self.translation_mode, value="both").pack(side="left", padx=5)

        workspace = tk.Frame(self.main_container, bg="#1e1e1e")
        workspace.pack(expand=True, fill="both", padx=10, pady=5)
        workspace.columnconfigure(0, weight=1); workspace.columnconfigure(1, weight=3); workspace.rowconfigure(0, weight=1)

        left_panel = tk.Frame(workspace, bg="#1e1e1e")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(left_panel, text="1. Input German:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Button(left_panel, text="🔍 Analyze Text", style="Action.TButton", command=self.process_text).pack(fill="x", pady=(5, 10))
        input_frame, self.input_text = self.create_text_area(left_panel)
        input_frame.pack(expand=True, fill="both")

        right_panel = tk.Frame(workspace, bg="#1e1e1e")
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        tk.Label(right_panel, text="Sentence Translation Display:", font=("Segoe UI", 9)).pack(anchor="w")
        self.sentence_display = tk.Text(right_panel, font=("Segoe UI", 12), bg="#2d2d2d", fg="#f1c40f", 
                                        relief="flat", height=3, padx=10, pady=10, wrap="word")
        self.sentence_display.pack(fill="x", pady=(0, 10))
        self.sentence_display.config(state="disabled")
        
        reader_frame, self.display = self.create_text_area(right_panel, is_reader=True)
        reader_frame.pack(expand=True, fill="both")
        self.display.config(state="disabled", cursor="arrow")

        self.tooltip = tk.Label(self.root, text="", bg="#f1c40f", fg="#2c3e50", 
                               font=("Segoe UI", 11, "bold"), padx=10, pady=5, relief="solid", borderwidth=1)

    def get_full_sentence(self, index):
        content = self.display.get("1.0", "end-1c")
        line, col = map(int, index.split('.'))
        lines = content.splitlines(keepends=True)
        char_offset = sum(len(l) for l in lines[:line-1]) + col
        
        for m in re.finditer(r'[^.!?\n]+[.!?]?', content):
            if m.start() <= char_offset < m.end():
                return m.group(0).strip()
        return ""

    def process_text(self):
        raw_text = self.input_text.get("1.0", "end-1c")
        self.display.config(state="normal")
        self.display.delete("1.0", "end")

        for line in raw_text.splitlines():
            words = line.split()
            if not words:
                self.display.insert("end", "\n")
                continue
            for word in words:
                clean = "".join(filter(str.isalnum, word))
                if not clean:
                    self.display.insert("end", word + " ")
                    continue
                
                tag = f"t_{clean}_{self.display.index('insert').replace('.', '_')}"
                self.display.insert("end", word + " ")
                self.display.tag_add(tag, "insert - 2c wordstart", "insert - 1c")
                self.display.tag_bind(tag, "<Enter>", lambda e, w=clean, t=tag: self.on_hover(e, w, t))
                self.display.tag_bind(tag, "<Leave>", lambda e, t=tag: self.on_leave(e, t))
            self.display.insert("end", "\n")
        self.display.config(state="disabled")

    def translate_word(self, word):
        if word not in self.cache:
            try: self.cache[word] = GoogleTranslator(source='de', target='en').translate(word)
            except: self.cache[word] = "..."
        return self.cache[word]

    def translate_sentence(self, sentence):
        if sentence not in self.cache:
            try: self.cache[sentence] = GoogleTranslator(source='de', target='en').translate(sentence)
            except: self.cache[sentence] = "Translation error..."
        return self.cache[sentence]

    def on_hover(self, event, word, tag):
        self.display.tag_configure(tag, foreground="#e67e22", underline=True)
        idx = self.display.index(f"{tag}.first")
        mode = self.translation_mode.get()

        # Word Translation (Tooltip)
        if mode in ["word", "both"]:
            result = self.translate_word(word)
            self.tooltip.config(text=result)
            self.tooltip.place(x=event.x_root - self.root.winfo_rootx() + 15, 
                               y=event.y_root - self.root.winfo_rooty() + 15)
        
        # Sentence Translation (Top Bar)
        if mode in ["sentence", "both"]:
            sentence = self.get_full_sentence(idx)
            if sentence:
                result = self.translate_sentence(sentence)
                self.sentence_display.config(state="normal")
                self.sentence_display.delete("1.0", tk.END)
                self.sentence_display.insert("1.0", result)
                self.sentence_display.config(state="disabled")

    def on_leave(self, event, tag):
        self.display.tag_configure(tag, foreground="#2c3e50", underline=False)
        self.tooltip.place_forget()

if __name__ == "__main__":
    root = tk.Tk()
    app = LingoApp(root)
    root.mainloop()
