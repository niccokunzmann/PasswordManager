import json
import os

try:
    import Tkinter as tk
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
except ImportError:
    import tkinter as tk
    import tkinter.messagebox as messagebox
    import tkinter.filedialog as filedialog
import ScrolledList

from database import Database
    
class MainWindow(tk.Tk, object):

    password_file = 'passwords.json'

    def __init__(self, *args, **kw):
        tk.Tk.__init__(self, *args, **kw)
        self.title('Password Manager')

        self.database = Database(self.password_file)

        self.paned_window = tk.PanedWindow(self)
        self.paned_window.pack(fill= tk.BOTH, expand = True)

        self.password_list_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.password_list_frame)
        
        self.password_list = ScrolledList.ScrolledList(self.password_list_frame)
        self.password_list.fill_menu = self.fill_menu
        self.password_list.on_select = self.on_select
        self.password_list.on_double = self.on_double

        self.info_frame = info_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.info_frame)

        self.entry_name_label = tk.Label(info_frame)
        self.entry_name_label.pack(fill = tk.X)
        self.entry_text = tk.Text(info_frame, height = 1, width = 30)
        self.entry_text.pack(fill = tk.BOTH, expand = True)

        self.entry_show_password_frame = tk.Frame(info_frame)
        self.entry_show_password_frame.pack(fill = tk.X)
        self.entry_password_button = tk.Button(self.entry_show_password_frame,
                                               text = 'show password')
        self.entry_password_entry = tk.Entry(self.entry_show_password_frame)
        def enter(event = None):
            self.entry_password_entry.selection_range(0, tk.END)
        self.entry_password_entry.bind('<FocusIn>', enter)

        self.show_deleted_entries = tk.BooleanVar(self)
        self.show_deleted_entries.set(False)

        self.bind('<Control-n>', self.new_password)
        self.bind('<KeyPress-Escape>', self.close)

        self.update_list()

    def close(self, event = None):
        self.quit()
        self.destroy()

    def new_password(self, event = None):
        with self.database:
            self.database.add_new_password_from_user()
        self.update_list()

    def update_list(self):
        selection = self.password_list.listbox.curselection()
        self.password_list.clear()
        for entry in self.password_entries:
            self.password_list.append(entry.name)
            if entry.deleted:
                self.password_list.listbox.itemconfigure(tk.END,
                                                         background = 'gray80')
        if not self.password_entries:
            self.password_list.listbox.delete(0, tk.END)
        if selection:
            self.password_list.select(selection[0])

    @property
    def password_entries(self):
        with self.database:
            entries = self.database.passwords
        if not self.show_deleted_entries.get():
            entries = [entry for entry in entries if not entry.deleted]
        return entries

    def update_info_frame(self, entry):
        self.entry_name_label['text'] = entry.name
        self.entry_text.delete("0.0", tk.END)
        self.entry_text.insert(tk.END, entry.text)
        self.entry_password_button['command'] = lambda: self.show_password(entry)
        self.entry_password_button.pack(fill = tk.X)
        self.entry_password_entry.delete(0, tk.END)
        self.entry_password_entry.pack_forget()

    def show_password(self, entry):
        password = entry.password
        self.entry_password_entry.delete(0, tk.END)
        self.entry_password_entry.insert(0, password)
        self.entry_password_button.pack_forget()
        self.entry_password_entry.pack(fill = tk.X)

    def copy_password_to_clipboard(self, event = None):
        password = self.current_entry.password
        self.clipboard_clear()
        self.clipboard_append(password)
        # TODO: notify about copy

    def show_deleted_passwords(self, event = None):
        self.update_list()

    def delete_password(self, event = None):
        with self.database:
            if self.current_entry.deleted:
                message = 'Do you want to delete {} for ever?'.format(self.current_entry.name)
                if messagebox.askokcancel('Delete?', message):
                    self.current_entry.remove()
            else:
                self.current_entry.deleted = True
        self.update_list()

    def restore_password(self, event = None):
        with self.database:
            self.current_entry.deleted = False
        self.update_list()

    @property
    def current_entry(self):
        index = self.password_list.listbox.index("active")
        if not self.password_entries:
            return None
        return self.password_entries[index]

    def import_passwords(self, event = None):
        file_name = filedialog.askopenfilename(filetypes = [("all files", "*")])
        import_config(file_name)

    def fill_menu(self):
        # after current_entry is updated
        self.after(1, self.menu_posted, self.password_list.menu)
        

    def menu_posted(self, menu):
        self.password_list.menu = None
        if self.current_entry:
            deletion_text = "delete"
            if self.current_entry.deleted:
                deletion_text += " for ever"
            menu.add_command(label = deletion_text, underline = 0, 
                             command = self.delete_password)
            menu.add_separator()
            if self.current_entry.deleted:
                menu.add_command(label = "undo deletion", underline = 0, 
                                 command = self.restore_password)
            menu.add_command(label = "copy password", underline = 0, 
                             accelerator = 'double click',
                             command = self.copy_password_to_clipboard)
            menu.add_separator()
        menu.add_command(label = "new", underline = 0, 
                         accelerator = 'Ctrl+N',
                         command = self.new_password)
        menu.add_checkbutton(label = "show deleted passwords",
                             underline = 0, 
                             variable = self.show_deleted_entries,
                             command = self.update_list)
        menu.add_command(label = "import", underline = 0, 
                         command = self.import_passwords)

    def on_select(self, index):
        if self.current_entry:
            self.update_info_frame(self.current_entry)

    def on_double(self, index):
        if self.current_entry:
            self.copy_password_to_clipboard(self.current_entry)
    
def test_encrypt_and_decrypt_password():
    salt = new_salt()
    p = hash(b'abcdef')
    pe = encrypt_password(p, salt)
    p2 = decrypt_password(pe, salt)
    assert p == p2
    assert pe != p2
    assert pe != p

if __name__ == '__main__':
##    test_encrypt_and_decrypt_password()
    root = MainWindow()
    root.mainloop()
