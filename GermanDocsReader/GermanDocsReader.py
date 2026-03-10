import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from deep_translator import GoogleTranslator
import threading
import re
import os

# --- SAFE MISTRAL IMPORT ---
try:
    from mistralai import Mistral
except ImportError:
    try:
        from mistralai.client import Mistral
    except ImportError:
        Mistral = None

class LingoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("German Transcript Tool - Saif: Mistral AI Edition")
        self.root.geometry("1300x900")
        self.root.configure(bg="#1e1e1e")

        self.client = None
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
        
        self.translation_mode = tk.StringVar(value="word")
        self.api_key_var = tk.StringVar()
        
        self.show_landing_page()

    def clear_screen(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def open_link(self, event):
        webbrowser.open_new("https://console.mistral.ai/")

    def save_key(self):
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("Empty Key", "Please enter a valid Mistral API Key.")
            return
        
        if Mistral:
            try:
                self.client = Mistral(api_key=key)
                messagebox.showinfo("Success", "Mistral API Key saved for this session!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to initialize: {e}")
        else:
            messagebox.showerror("Module Error", "mistralai library not found. Run: pip install mistralai")

    def copy_to_clipboard(self, text_widget, button_widget):
        content = text_widget.get("1.0", "end-1c")
        if content.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            # Visual feedback
            original_text = button_widget['text']
            button_widget.config(text="✅ Copied!")
            self.root.after(1500, lambda: button_widget.config(text=original_text))

    def show_landing_page(self):
        self.clear_screen()
        inner_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(inner_frame, text="German Transcript Tool", font=("Segoe UI", 32, "bold"), 
                 bg="#1e1e1e", fg="#3498db").pack(pady=(0, 30))
        
        # API Key Section
        key_frame = tk.LabelFrame(inner_frame, text=" API Settings ", font=("Segoe UI", 10, "bold"),
                                  bg="#1e1e1e", fg="#f1c40f", padx=20, pady=20)
        key_frame.pack(pady=20, fill="x")

        tk.Label(key_frame, text="Enter Mistral API Key:", font=("Segoe UI", 10)).pack(anchor="w")
        key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, width=40, show="*")
        key_entry.pack(pady=5, fill="x")

        link_label = tk.Label(key_frame, text="Get a key at: https://console.mistral.ai/", 
                              font=("Segoe UI", 9, "underline"), bg="#1e1e1e", fg="#3498db", cursor="hand2")
        link_label.pack(anchor="w")
        link_label.bind("<Button-1>", self.open_link)

        ttk.Button(key_frame, text="Submit Key", command=self.save_key).pack(pady=10)

        # Mode Buttons
        btn_frame = tk.Frame(inner_frame, bg="#1e1e1e")
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="📖 Translation Reader", style="Menu.TButton", 
                   command=self.setup_translation_ui).pack(pady=10, fill="x")
        ttk.Button(btn_frame, text="✍️ AI Transcript Fixer", style="Menu.TButton", 
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

    # --- TRANSCRIPT CORRECTION ---

    def setup_transcript_ui(self):
        self.clear_screen()
        nav = tk.Frame(self.main_container, bg="#1e1e1e")
        nav.pack(fill="x", padx=10, pady=5)
        ttk.Button(nav, text="← Back", command=self.show_landing_page).pack(side="left")

        workspace = tk.Frame(self.main_container, bg="#1e1e1e")
        workspace.pack(expand=True, fill="both", padx=10, pady=5)
        workspace.columnconfigure(0, weight=1); workspace.columnconfigure(1, weight=3); workspace.rowconfigure(0, weight=1)

        left_panel = tk.Frame(workspace, bg="#1e1e1e")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(left_panel, text="1. Paste Transcript:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.fix_btn = ttk.Button(left_panel, text="✨ Run Mistral Fix", style="Action.TButton", command=self.start_fix_thread)
        self.fix_btn.pack(fill="x", pady=(5, 10))
        input_frame, self.trans_input = self.create_text_area(left_panel)
        input_frame.pack(expand=True, fill="both")

        right_panel = tk.Frame(workspace, bg="#1e1e1e")
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        header_right = tk.Frame(right_panel, bg="#1e1e1e")
        header_right.pack(fill="x", pady=(0, 10))
        tk.Label(header_right, text="2. AI Result:", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        # NEW: Copy Button
        self.copy_btn = ttk.Button(header_right, text="📋 Copy Output", command=lambda: self.copy_to_clipboard(self.trans_output, self.copy_btn))
        self.copy_btn.pack(side="right")

        output_frame, self.trans_output = self.create_text_area(right_panel, is_reader=True)
        output_frame.pack(expand=True, fill="both")

    def start_fix_thread(self):
        if not self.client:
            messagebox.showerror("Key Missing", "Please enter and submit your API key on the home screen first.")
            return
        self.fix_btn.config(state="disabled", text="🤖 Processing...")
        threading.Thread(target=self.fix_transcript, daemon=True).start()

    def fix_transcript(self):
        raw_text = self.trans_input.get("1.0", "end-1c")
        if not raw_text.strip():
            self.root.after(0, lambda: self.fix_btn.config(state="normal", text="✨ Run Mistral Fix"))
            return
        try:
            chat_response = self.client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": f"Fix German transcript punctuation/capitalization:\n\n{raw_text}"}]
            )
            final_text = chat_response.choices[0].message.content.strip()
            self.root.after(0, lambda: (self.trans_output.delete("1.0", "end"), 
                                        self.trans_output.insert("1.0", final_text),
                                        self.fix_btn.config(state="normal", text="✨ Run Mistral Fix")))
        except Exception as e:
            self.root.after(0, lambda: (messagebox.showerror("Error", str(e)),
                                        self.fix_btn.config(state="normal", text="✨ Run Mistral Fix")))

    # --- TRANSLATION READER ---

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
        tk.Label(left_panel, text="1. German Input:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Button(left_panel, text="🔍 Analyze", style="Action.TButton", command=self.process_text).pack(fill="x", pady=(5, 10))
        input_frame, self.input_text = self.create_text_area(left_panel)
        input_frame.pack(expand=True, fill="both")

        right_panel = tk.Frame(workspace, bg="#1e1e1e")
        right_panel.grid(row=0, column=1, sticky="nsew")
        self.sentence_display = tk.Text(right_panel, font=("Segoe UI", 12), bg="#2d2d2d", fg="#f1c40f", 
                                        relief="flat", height=3, padx=10, pady=10, wrap="word")
        self.sentence_display.pack(fill="x", pady=(0, 10))
        self.sentence_display.config(state="disabled")
        
        reader_frame, self.display = self.create_text_area(right_panel, is_reader=True)
        reader_frame.pack(expand=True, fill="both")
        self.display.config(state="disabled")

        self.tooltip = tk.Label(self.root, text="", bg="#f1c40f", fg="#2c3e50", font=("Segoe UI", 11, "bold"), padx=10, pady=5, relief="solid", borderwidth=1)

    def process_text(self):
        raw_text = self.input_text.get("1.0", "end-1c")
        self.display.config(state="normal")
        self.display.delete("1.0", "end")
        for line in raw_text.splitlines():
            for word in line.split():
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

    def on_hover(self, event, word, tag):
        self.display.tag_configure(tag, foreground="#e67e22", underline=True)
        mode = self.translation_mode.get()

        if mode in ["word", "both"]:
            if word not in self.cache:
                try: self.cache[word] = GoogleTranslator(source='de', target='en').translate(word)
                except: self.cache[word] = "..."
            self.tooltip.config(text=self.cache[word])
            self.tooltip.place(x=event.x_root - self.root.winfo_rootx() + 15, y=event.y_root - self.root.winfo_rooty() + 15)
        
        if mode in ["sentence", "both"]:
            content = self.display.get("1.0", "end-1c")
            idx = self.display.index(f"{tag}.first")
            line, col = map(int, idx.split('.'))
            lines = content.splitlines(keepends=True)
            offset = sum(len(l) for l in lines[:line-1]) + col
            for m in re.finditer(r'[^.!?\n]+[.!?]?', content):
                if m.start() <= offset < m.end():
                    sentence = m.group(0).strip()
                    if sentence not in self.cache:
                        self.cache[sentence] = GoogleTranslator(source='de', target='en').translate(sentence)
                    self.sentence_display.config(state="normal")
                    self.sentence_display.delete("1.0", tk.END)
                    self.sentence_display.insert("1.0", self.cache[sentence])
                    self.sentence_display.config(state="disabled")
                    break

    def on_leave(self, event, tag):
        self.display.tag_configure(tag, foreground="#2c3e50", underline=False)
        self.tooltip.place_forget()

if __name__ == "__main__":
    root = tk.Tk()
    app = LingoApp(root)
    root.mainloop()
