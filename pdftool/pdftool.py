import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os

class VisualEditor(tk.Toplevel):
    """Visual window for deleting and reordering pages."""
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.title(f"Visual Editor: {os.path.basename(file_path)}")
        self.geometry("1200x900")
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        # List of dicts: {orig_idx, selected, frame}
        self.pages_list = [] 
        
        self.setup_ui()
        self.load_pages()

    def setup_ui(self):
        # Header Info
        control_panel = tk.Frame(self, bg="#2c3e50", pady=10)
        control_panel.pack(fill="x")
        
        instructions = (
            "INSTRUCTIONS: Click the IMAGE to toggle Delete (Red) / Keep (Green).\n"
            "Use the ◀ and ▶ buttons below images to change the page sequence."
        )
        tk.Label(control_panel, text=instructions, bg="#2c3e50", fg="white", 
                 font=("Helvetica", 10, "bold")).pack()

        # Scrollable Canvas
        self.canvas = tk.Canvas(self, bg="#ecf0f1", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ecf0f1")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", expand=True, fill="both")
        self.scrollbar.pack(side="right", fill="y")

        # Footer Actions
        footer = tk.Frame(self, pady=15, bg="#bdc3c7")
        footer.pack(fill="x")
        ttk.Button(footer, text="💾 Save Changes to New PDF", command=self.save_edits).pack(side="right", padx=20)
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(side="right")

    def load_pages(self):
        """Generates thumbnails and builds the initial grid."""
        for i in range(len(self.doc)):
            page = self.doc.load_page(i)
            # Create a 20% scale thumbnail
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)

            # Container for the page
            frame = tk.Frame(self.scrollable_frame, bd=4, relief="flat", bg="#2ecc71")
            
            # Thumbnail label
            lbl_img = tk.Label(frame, image=photo, cursor="hand2")
            lbl_img.image = photo # Prevent garbage collection
            lbl_img.pack(padx=5, pady=5)

            # Reorder control buttons
            btn_frame = tk.Frame(frame, bg="white")
            btn_frame.pack(fill="x")
            
            left_btn = tk.Button(btn_frame, text="◀", bg="#ecf0f1")
            left_btn.pack(side="left", expand=True, fill="x")
            
            right_btn = tk.Button(btn_frame, text="▶", bg="#ecf0f1")
            right_btn.pack(side="right", expand=True, fill="x")

            page_info = {"orig_idx": i, "selected": True, "frame": frame}
            
            # Clicking the image toggles Keep/Delete
            lbl_img.bind("<Button-1>", lambda e, p=page_info: self.toggle_page(p))
            
            self.pages_list.append(page_info)
        
        self.refresh_grid()

    def toggle_page(self, page_info):
        page_info["selected"] = not page_info["selected"]
        color = "#2ecc71" if page_info["selected"] else "#e74c3c"
        page_info["frame"].configure(bg=color)

    def move_page(self, current_list_idx, direction):
        """Swaps page position in the list and redraws."""
        new_idx = current_list_idx + direction
        if 0 <= new_idx < len(self.pages_list):
            self.pages_list[current_list_idx], self.pages_list[new_idx] = \
                self.pages_list[new_idx], self.pages_list[current_list_idx]
            self.refresh_grid()

    def refresh_grid(self):
        """Clears and rebuilds the grid to reflect the new order."""
        for item in self.pages_list:
            item["frame"].grid_forget()
        
        for i, item in enumerate(self.pages_list):
            item["frame"].grid(row=i // 4, column=i % 4, padx=15, pady=15)
            
            # Update button commands to the NEW index
            for child in item["frame"].winfo_children():
                if isinstance(child, tk.Frame): # The button row
                    btns = child.winfo_children()
                    btns[0].configure(command=lambda idx=i: self.move_page(idx, -1))
                    btns[1].configure(command=lambda idx=i: self.move_page(idx, 1))

    def save_edits(self):
        output_path = filedialog.asksaveasfilename(
            title="Save Reorganized PDF",
            defaultextension=".pdf",
            initialfile="final_reordered.pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output_path: return

        writer = PdfWriter()
        reader = PdfReader(self.file_path)
        
        count = 0
        for p in self.pages_list:
            if p["selected"]:
                writer.add_page(reader.pages[p["orig_idx"]])
                count += 1

        if count == 0:
            messagebox.showwarning("Empty Selection", "You must keep at least one page!")
            return

        with open(output_path, "wb") as f:
            writer.write(f)
        
        messagebox.showinfo("Success", f"Exported {count} pages successfully!")
        self.destroy()


class PDFMasterTool:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Master Tool Pro")
        self.root.geometry("600x700")
        self.root.configure(bg="#f5f5f7")

        self.selected_merge_files = []
        self.setup_main_ui()

    def setup_main_ui(self):
        main_frame = tk.Frame(self.root, bg="#f5f5f7", padx=40, pady=40)
        main_frame.pack(expand=True, fill="both")

        tk.Label(main_frame, text="PDF Master Tool", font=("Helvetica", 24, "bold"), 
                 bg="#f5f5f7", fg="#2c3e50").pack(pady=(0, 30))

        # --- 1. MERGE SECTION ---
        m_frame = tk.LabelFrame(main_frame, text=" Merge & Order Multiple PDFs ", padx=15, pady=15, bg="white")
        m_frame.pack(fill="x", pady=10)
        
        list_container = tk.Frame(m_frame, bg="white")
        list_container.pack(fill="x")
        
        self.file_listbox = tk.Listbox(list_container, height=4, font=("Helvetica", 10))
        self.file_listbox.pack(side="left", expand=True, fill="x")
        
        order_btns = tk.Frame(list_container, bg="white")
        order_btns.pack(side="right", padx=5)
        ttk.Button(order_btns, text="▲", width=3, command=self.move_file_up).pack()
        ttk.Button(order_btns, text="▼", width=3, command=self.move_file_down).pack()

        btn_row = tk.Frame(m_frame, bg="white")
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="➕ Add Files", command=self.add_files).pack(side="left", expand=True)
        ttk.Button(btn_row, text="🧹 Clear", command=self.clear_merge).pack(side="left", expand=True)
        ttk.Button(btn_row, text="💾 Merge & Save", command=self.process_merge).pack(side="left", expand=True)

        # --- 2. VISUAL EDITOR SECTION ---
        v_frame = tk.LabelFrame(main_frame, text=" Visual Reorganize / Delete Pages ", padx=15, pady=15, bg="white")
        v_frame.pack(fill="x", pady=10)
        ttk.Button(v_frame, text="👁️ Open Single PDF in Visual Editor", command=self.open_visual_editor).pack(fill="x")

        # --- 3. COMPRESS SECTION ---
        c_frame = tk.LabelFrame(main_frame, text=" Optimize / Compress Size ", padx=15, pady=15, bg="white")
        c_frame.pack(fill="x", pady=10)
        ttk.Button(c_frame, text="🗜️ Select PDF to Compress", command=self.compress_pdf).pack(fill="x")

    # --- MAIN LOGIC ---
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for f in files:
            self.selected_merge_files.append(f)
            self.file_listbox.insert(tk.END, os.path.basename(f))

    def clear_merge(self):
        self.selected_merge_files = []
        self.file_listbox.delete(0, tk.END)

    def move_file_up(self):
        idx = self.file_listbox.curselection()
        if not idx or idx[0] == 0: return
        i = idx[0]
        self.selected_merge_files[i], self.selected_merge_files[i-1] = self.selected_merge_files[i-1], self.selected_merge_files[i]
        self.sync_listbox(i-1)

    def move_file_down(self):
        idx = self.file_listbox.curselection()
        if not idx or idx[0] == len(self.selected_merge_files)-1: return
        i = idx[0]
        self.selected_merge_files[i], self.selected_merge_files[i+1] = self.selected_merge_files[i+1], self.selected_merge_files[i]
        self.sync_listbox(i+1)

    def sync_listbox(self, select_idx):
        self.file_listbox.delete(0, tk.END)
        for f in self.selected_merge_files:
            self.file_listbox.insert(tk.END, os.path.basename(f))
        self.file_listbox.select_set(select_idx)

    def process_merge(self):
        if not self.selected_merge_files: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="merged_doc.pdf")
        if out:
            writer = PdfWriter()
            for f in self.selected_merge_files: writer.append(f)
            with open(out, "wb") as f_out: writer.write(f_out)
            messagebox.showinfo("Success", "Merged PDF saved!")

    def open_visual_editor(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path: VisualEditor(self.root, path)

    def compress_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="compressed.pdf")
        if out:
            reader = PdfReader(path); writer = PdfWriter()
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            with open(out, "wb") as f: writer.write(f)
            messagebox.showinfo("Success", "Compression finished!")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMasterTool(root)
    root.mainloop()
