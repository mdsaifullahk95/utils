import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader
import fitz  # PyMuPDF
from PIL import Image, ImageTk
from deep_translator import GoogleTranslator
import threading
import os

class VisualEditor(tk.Toplevel):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.title(f"Visual Editor: {os.path.basename(file_path)}")
        self.geometry("1200x900")
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.pages_list = [] 
        
        self.setup_ui()
        self.load_pages()

    def setup_ui(self):
        control_panel = tk.Frame(self, bg="#2c3e50", pady=10)
        control_panel.pack(fill="x")
        
        instructions = "Click IMAGE to Toggle Delete | Use ◀ ▶ to Reorder"
        tk.Label(control_panel, text=instructions, bg="#2c3e50", fg="white", font=("Helvetica", 11, "bold")).pack()

        self.canvas = tk.Canvas(self, bg="#ecf0f1", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ecf0f1")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", expand=True, fill="both")
        self.scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(self, pady=15, bg="#bdc3c7")
        footer.pack(fill="x")
        ttk.Button(footer, text="💾 Save Changes", command=self.save_edits).pack(side="right", padx=20)
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(side="right")

    def load_pages(self):
        for i in range(len(self.doc)):
            page = self.doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)

            frame = tk.Frame(self.scrollable_frame, bd=4, relief="flat", bg="#2ecc71")
            lbl_img = tk.Label(frame, image=photo, cursor="hand2")
            lbl_img.image = photo 
            lbl_img.pack(padx=5, pady=5)

            btn_frame = tk.Frame(frame, bg="white")
            btn_frame.pack(fill="x")
            tk.Button(btn_frame, text="◀", command=lambda idx=i: self.move_page(idx, -1)).pack(side="left", expand=True, fill="x")
            tk.Button(btn_frame, text="▶", command=lambda idx=i: self.move_page(idx, 1)).pack(side="right", expand=True, fill="x")

            page_info = {"orig_idx": i, "selected": True, "frame": frame}
            lbl_img.bind("<Button-1>", lambda e, p=page_info: self.toggle_page(p))
            self.pages_list.append(page_info)
        self.refresh_grid()

    def toggle_page(self, page_info):
        page_info["selected"] = not page_info["selected"]
        page_info["frame"].configure(bg="#2ecc71" if page_info["selected"] else "#e74c3c")

    def move_page(self, current_list_idx, direction):
        new_idx = current_list_idx + direction
        if 0 <= new_idx < len(self.pages_list):
            self.pages_list[current_list_idx], self.pages_list[new_idx] = self.pages_list[new_idx], self.pages_list[current_list_idx]
            self.refresh_grid()

    def refresh_grid(self):
        for item in self.pages_list: item["frame"].grid_forget()
        for i, item in enumerate(self.pages_list):
            item["frame"].grid(row=i // 4, column=i % 4, padx=15, pady=15)
            for child in item["frame"].winfo_children():
                if isinstance(child, tk.Frame):
                    btns = child.winfo_children()
                    btns[0].configure(command=lambda idx=i: self.move_page(idx, -1))
                    btns[1].configure(command=lambda idx=i: self.move_page(idx, 1))

    def save_edits(self):
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            writer = PdfWriter(); reader = PdfReader(self.file_path)
            for p in self.pages_list:
                if p["selected"]: writer.add_page(reader.pages[p["orig_idx"]])
            with open(out, "wb") as f: writer.write(f)
            self.destroy()

class PDFMasterTool:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Master Tool Pro + Translator")
        self.root.geometry("650x850")
        self.root.configure(bg="#f5f5f7")
        self.selected_merge_files = []
        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg="#f5f5f7", padx=30, pady=20)
        main_frame.pack(expand=True, fill="both")

        tk.Label(main_frame, text="PDF Master Suite", font=("Helvetica", 24, "bold"), bg="#f5f5f7", fg="#2c3e50").pack(pady=10)

        # 1. MERGE
        m_frame = tk.LabelFrame(main_frame, text=" 🔗 Merge & Order PDFs ", padx=10, pady=10, bg="white")
        m_frame.pack(fill="x", pady=5)
        self.file_listbox = tk.Listbox(m_frame, height=4)
        self.file_listbox.pack(fill="x", pady=5)
        btn_row = tk.Frame(m_frame, bg="white")
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Add Files", command=self.add_files).pack(side="left", expand=True)
        ttk.Button(btn_row, text="Clear", command=self.clear_merge).pack(side="left", expand=True)
        ttk.Button(btn_row, text="Save Merge", command=self.process_merge).pack(side="left", expand=True)

        # 2. VISUAL EDITOR
        v_frame = tk.LabelFrame(main_frame, text=" ✂️ Visual Edit (Reorder/Delete) ", padx=10, pady=10, bg="white")
        v_frame.pack(fill="x", pady=5)
        ttk.Button(v_frame, text="Open Visual Editor", command=self.open_visual_editor).pack(fill="x")

        # 3. TRANSLATOR
        t_frame = tk.LabelFrame(main_frame, text=" 🌐 DE ➔ EN Translator ", padx=10, pady=10, bg="white")
        t_frame.pack(fill="x", pady=5)
        self.prog_label = tk.Label(t_frame, text="Select a German PDF to translate", bg="white", fg="gray")
        self.prog_label.pack()
        self.progress = ttk.Progressbar(t_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=5)
        self.trans_btn = ttk.Button(t_frame, text="Translate PDF to English", command=self.start_translation)
        self.trans_btn.pack(fill="x")

        # 4. COMPRESS
        c_frame = tk.LabelFrame(main_frame, text=" 🗜️ Optimize Size ", padx=10, pady=10, bg="white")
        c_frame.pack(fill="x", pady=5)
        ttk.Button(c_frame, text="Compress PDF", command=self.compress_pdf).pack(fill="x")

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for f in files:
            self.selected_merge_files.append(f)
            self.file_listbox.insert(tk.END, os.path.basename(f))

    def clear_merge(self):
        self.selected_merge_files = []
        self.file_listbox.delete(0, tk.END)

    def process_merge(self):
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            writer = PdfWriter()
            for f in self.selected_merge_files: writer.append(f)
            with open(out, "wb") as f_out: writer.write(f_out)
            messagebox.showinfo("Done", "Merged!")

    def open_visual_editor(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path: VisualEditor(self.root, path)

    def start_translation(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"EN_{os.path.basename(path)}")
        if out:
            self.trans_btn.config(state="disabled")
            threading.Thread(target=self.translate_logic, args=(path, out), daemon=True).start()

    def translate_logic(self, path, out_path):
        try:
            # Open the existing document to use as a template
            doc = fitz.open(path)
            translator = GoogleTranslator(source='de', target='en')
            total = len(doc)

            for i in range(total):
                self.root.after(0, lambda: self.prog_label.config(text=f"Processing page {i+1}/{total}"))
                self.root.after(0, lambda: self.progress.configure(value=(i/total)*100))
                
                page = doc.load_page(i)
                # Get text blocks with metadata (including color and coordinates)
                dict_text = page.get_text("dict")
                
                for block in dict_text["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                german_text = span["text"].strip()
                                
                                # Ignore empty strings or pure numbers
                                if german_text and not german_text.isdigit() and len(german_text) > 1:
                                    try:
                                        english_text = translator.translate(german_text)
                                        
                                        # 1. Cover the old text with a rectangle matching the background
                                        # In many PDFs, background is white (1, 1, 1)
                                        page.draw_rect(span["bbox"], color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                                        
                                        # 2. Insert the new English text in the same spot
                                        # We try to match the original font size
                                        page.insert_text(
                                            (span["bbox"][0], span["bbox"][1] + span["size"]), 
                                            english_text,
                                            fontsize=span["size"],
                                            color=(0, 0, 0) # Black text
                                        )
                                    except:
                                        continue

            # Save the modified template
            doc.save(out_path)
            doc.close()
            self.root.after(0, lambda: messagebox.showinfo("Success", "Translation overlaid on original layout!"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Overlay failed: {e}"))
        finally:
            self.root.after(0, lambda: (self.trans_btn.config(state="normal"), self.progress.configure(value=0), self.prog_label.config(text="Ready")))

    def compress_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf")
        if out:
            reader = PdfReader(path); writer = PdfWriter()
            for page in reader.pages: page.compress_content_streams(); writer.add_page(page)
            with open(out, "wb") as f: writer.write(f)
            messagebox.showinfo("Done", "Compressed!")

if __name__ == "__main__":
    root = tk.Tk(); app = PDFMasterTool(root); root.mainloop()
