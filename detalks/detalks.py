import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
import threading
import re

try:
    from mistralai import Mistral
except ImportError:
    try:
        from mistralai.client import Mistral
    except ImportError:
        Mistral = None

class DeutschCoach:
    def __init__(self, root):
        self.root = root
        self.root.title("DeTalks: Interactive Tutor")
        self.root.geometry("1000x900")
        self.root.configure(bg="#2c3e50")

        self.client = None
        self.chat_history = []
        self.cache = {}
        
        self.setup_ui()
        self.show_key_dialog()
        
        self.tooltip = tk.Label(self.root, bg="#f1c40f", fg="black", font=("Arial", 10, "bold"), 
                               relief="solid", borderwidth=1, padx=8, pady=4)

    def show_key_dialog(self):
        self.key_window = tk.Toplevel(self.root)
        self.key_window.title("API Authentication")
        self.key_window.geometry("450x200")
        self.key_window.configure(bg="#ecf0f1")
        self.key_window.transient(self.root) 
        self.key_window.grab_set() 

        tk.Label(self.key_window, text="Enter Mistral API Key:", bg="#ecf0f1", font=("Arial", 11, "bold")).pack(pady=20)
        self.key_entry = tk.Entry(self.key_window, show="*", width=45)
        self.key_entry.pack(pady=5)
        ttk.Button(self.key_window, text="Verify & Unlock App", command=self.verify_key).pack(pady=20)

    def verify_key(self):
        key = self.key_entry.get().strip()
        if not key: return
        try:
            test_client = Mistral(api_key=key)
            test_client.models.list() 
            self.client = test_client
            self.key_window.destroy()
        except Exception as e:
            messagebox.showerror("Invalid Key", f"Error: {e}")

    def setup_ui(self):
        top_bar = tk.Frame(self.root, bg="#34495e", pady=10)
        top_bar.pack(fill="x")
        
        tk.Label(top_bar, text="Level:", bg="#34495e", fg="white").pack(side="left", padx=5)
        self.level_var = tk.StringVar(value="Beginner")
        self.level_menu = ttk.Combobox(top_bar, textvariable=self.level_var, 
                                       values=["Beginner", "Intermediate", "Advanced"], 
                                       state="readonly", width=12)
        self.level_menu.pack(side="left", padx=5)
        
        tk.Label(top_bar, text="Hover Mode:", bg="#34495e", fg="white").pack(side="left", padx=15)
        self.mode_var = tk.StringVar(value="Both")
        ttk.Combobox(top_bar, textvariable=self.mode_var, values=["Word", "Sentence", "Both"], 
                     state="readonly", width=10).pack(side="left", padx=5)
        
        self.start_btn = ttk.Button(top_bar, text="🚀 Start Conversation", command=self.start_chat)
        self.start_btn.pack(side="left", padx=20)
        ttk.Button(top_bar, text="🔄 Reset / New Topic", command=self.reset_chat).pack(side="left")

        chat_frame = tk.Frame(self.root, bg="#2c3e50")
        chat_frame.pack(expand=True, fill="both", padx=20, pady=5)
        
        self.chat_display = tk.Text(chat_frame, wrap="word", bg="#ecf0f1", fg="#2c3e50", 
                                   font=("Georgia", 12), state="disabled", padx=15, pady=15)
        scrollbar = ttk.Scrollbar(chat_frame, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.chat_display.pack(side="left", expand=True, fill="both")

        self.trans_panel = tk.Label(self.root, text="Waiting to start...", bg="#2c3e50", 
                                   fg="#bdc3c7", font=("Arial", 11, "italic"), pady=5)
        self.trans_panel.pack(fill="x")

        input_frame = tk.Frame(self.root, bg="#2c3e50", pady=10)
        input_frame.pack(fill="x", padx=20)
        self.user_input = tk.Entry(input_frame, font=("Arial", 13))
        self.user_input.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.user_input.bind("<Return>", lambda e: self.send_message())
        self.send_btn = ttk.Button(input_frame, text="Senden", command=self.send_message)
        self.send_btn.pack(side="right")

    def start_chat(self):
        if not self.client: return
        self.start_btn.config(state="disabled")
        self.level_menu.config(state="disabled")
        
        level = self.level_var.get()
        # Prompt for starting a German-only chat
        prompt = f"Start a friendly conversation in German. Level: {level}. Use only German. Ask one opening question."
        threading.Thread(target=self.get_ai_response, args=(prompt, "System: Initialize Conversation. Output ONLY German."), daemon=True).start()

    def reset_chat(self):
        self.chat_history = []
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.config(state="disabled")
        self.start_btn.config(state="normal")
        self.level_menu.config(state="readonly")
        self.trans_panel.config(text="Reset complete.")

    def send_message(self):
        text = self.user_input.get().strip()
        if not text or not self.client: return
        
        self.append_to_chat(f"\nDu: {text}\n", "user")
        self.user_input.delete(0, "end")
        
        instruction = (
            f"Role: German Tutor for {self.level_var.get()} level. "
            "STRICT RULE: Your entire output must be in GERMAN only. Do not translate for the user. "
            "Structure: If error exists: 'Korrektur: [Correction in German]'. "
            "Then: 'Antwort: [Response in German]'."
        )
        threading.Thread(target=self.get_ai_response, args=(text, instruction), daemon=True).start()

    def get_ai_response(self, user_text, instruction):
        try:
            messages = [{"role": "system", "content": instruction}] + self.chat_history + [{"role": "user", "content": user_text}]
            response = self.client.chat.complete(model="mistral-small-latest", messages=messages)
            ai_text = response.choices[0].message.content
            
            self.chat_history.append({"role": "user", "content": user_text})
            self.chat_history.append({"role": "assistant", "content": ai_text})
            
            self.root.after(0, lambda: self.append_to_chat("\nCoach: ", "coach_header"))
            self.root.after(0, lambda: self.process_ai_text(ai_text))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("API Error", str(e)))

    def append_to_chat(self, text, tag):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", text, tag)
        self.chat_display.tag_configure("user", foreground="#2980b9", font=("Arial", 12, "bold"))
        self.chat_display.tag_configure("coach_header", foreground="#c0392b", font=("Arial", 12, "bold"))
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def process_ai_text(self, text):
        self.chat_display.config(state="normal")
        for word in text.split():
            clean = re.sub(r'[^\w]', '', word)
            tag = f"tag_{clean}_{self.chat_display.index('insert').replace('.', '_')}"
            self.chat_display.insert("end", word + " ", tag)
            self.chat_display.tag_bind(tag, "<Enter>", lambda e, w=clean, s=text, t=tag: self.on_hover(e, w, s, t))
            self.chat_display.tag_bind(tag, "<Leave>", lambda e, t=tag: self.on_leave(e, t))
        self.chat_display.insert("end", "\n")
        self.chat_display.config(state="disabled")

    def on_hover(self, event, word, full_sentence, tag):
        self.chat_display.tag_configure(tag, background="#dfe6e9", foreground="#d35400")
        mode = self.mode_var.get()
        
        def translate():
            result = ""
            try:
                if mode in ["Word", "Both"] and word:
                    w_trans = self.cache.get(f"w_{word}") or GoogleTranslator(source='de', target='en').translate(word)
                    self.cache[f"w_{word}"] = w_trans
                    result += f"Word: {w_trans}"
                if mode in ["Sentence", "Both"]:
                    s_trans = self.cache.get(f"s_{full_sentence}") or GoogleTranslator(source='de', target='en').translate(full_sentence)
                    self.cache[f"s_{full_sentence}"] = s_trans
                    result += (" | " if result else "") + f"Sentence: {s_trans}"
            except: result = "Error"
            self.root.after(0, lambda: self.update_ui_trans(result, event))

        threading.Thread(target=translate, daemon=True).start()

    def update_ui_trans(self, text, event):
        self.tooltip.config(text=text)
        self.tooltip.place(x=event.x_root - self.root.winfo_rootx() + 10, y=event.y_root - self.root.winfo_rooty() + 10)
        self.trans_panel.config(text=text, fg="#3498db", font=("Arial", 11, "bold"))

    def on_leave(self, event, tag):
        self.chat_display.tag_configure(tag, background="", foreground="#2c3e50")
        self.tooltip.place_forget()
        self.trans_panel.config(text="Ready", fg="#bdc3c7", font=("Arial", 11, "italic"))

if __name__ == "__main__":
    root = tk.Tk()
    app = DeutschCoach(root)
    root.mainloop()
