import json
import os
import sys
import io
import traceback
from contextlib import contextmanager

try:
    import Tkinter as tk
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
except ImportError:
    import tkinter as tk
    import tkinter.messagebox as messagebox
    import tkinter.filedialog as filedialog
import idlelib.ScrolledList as ScrolledList
import idlelib.macosxSupport as macosxSupport

from database import Database
from dialog import notify_about_copy, notify_file, ask_new_password, notify

REMOVE_SUBSET_AFTER_MILLISECONDS = 300000
    
class MainWindow(tk.Tk, object):

    password_file = 'passwords.json'

    def __init__(self, *args, **kw):
        tk.Tk.__init__(self, *args, **kw)
        macosxSupport._initializeTkVariantTests(self)
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
        
        self.last_pressed_variable = tk.StringVar(master = self)
        self.choose_list_entry = None
        self.subset_removal_after_id = None
        
        self.password_list.listbox.bind('<Any-KeyPress>', self.select_by_letter)
        self.password_list.listbox.bind('<Return>', self.copy_current_password_to_clipboard)

        self.selected_count = 0

        self.info_frame = info_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.info_frame)

        self.name_frame = tk.Frame(info_frame)
        self.name_frame.pack(fill = tk.X)
        self.entry_name_entry = tk.Entry(self.name_frame)
        self.entry_name_entry.pack(fill = tk.X, side = tk.LEFT, expand = True)
        self.save_info_button = tk.Button(self.name_frame, text = "save", 
                                          command = self.save_info)
        self.save_info_button.pack(side = tk.LEFT)
        
        self.entry_text = tk.Text(info_frame, height = 1, width = 30)
        self.entry_text.pack(fill = tk.BOTH, expand = True)

        self.entry_show_password_frame = tk.Frame(info_frame)
        self.entry_show_password_frame.pack(fill = tk.X)
        self.entry_toggle_password_frame = tk.Frame(self.entry_show_password_frame)
        self.entry_toggle_password_frame.pack(fill = tk.BOTH, side = tk.LEFT, expand = True)
        self.entry_password_button = tk.Button(self.entry_toggle_password_frame,
                                               text = 'show password')

        self.entry_password_entry = tk.Entry(self.entry_toggle_password_frame)
        def enter(event = None):
            self.entry_password_entry.selection_range(0, tk.END)
        self.entry_password_entry.bind('<FocusIn>', enter)
        self.entry_password_entry.pack(fill = tk.X, expand = True,
                                       side = tk.LEFT)
        
        self.entry_new_password = tk.Button(self.entry_show_password_frame,
                                            text = 'new',
                                            command = self.replace_password)
        self.entry_new_password.pack(side = tk.RIGHT)

        self.show_deleted_entries = tk.BooleanVar(self)
        self.show_deleted_entries.set(False)

        self.bind('<Control-n>', self.new_password)
        self.bind('<Double-Escape>', self.minimize)
        self.bind('<KeyPress-Escape>', self.reset_last_pressed)

        self.database_updated()
        self.hide_password()
        self.reset_last_pressed()
        self.select(0)
    
    def move_list_up(self, event=None):
        self.select(self.current_index - 1)
        
    def move_list_down(self, event=None):
        self.select(self.current_index + 1)

    def update_choose_list_entry(self):
        if self.last_pressed and self.choose_list_entry is None:
            self.choose_list_entry = tk.Entry(self.password_list_frame, textvariable = self.last_pressed_variable)
            self.choose_list_entry.pack(side = tk.BOTTOM, fill = tk.X, before = self.password_list.frame)
            self.choose_list_entry.bind('<Any-KeyPress>', self.last_pressed_changed)
            self.choose_list_entry.bind('<Key-Up>', self.move_list_up)
            self.choose_list_entry.bind('<Key-Down>', self.move_list_down)
            self.choose_list_entry.bind('<Key-Return>', self.copy_current_password_to_clipboard)
        elif not self.last_pressed and self.choose_list_entry is not None:
            self.choose_list_entry.pack_forget()
            self.choose_list_entry = None

    @property
    def current_entry_name(self):
        selection = self.password_list.listbox.curselection()
        if selection:
            index = selection[0]
            name = self.password_list.get(index)
            return name

    @property
    @contextmanager
    def updating_database(self):
        current_entry_name = self.current_entry_name
        with self.database:
            yield
        self.database_updated()
        if current_entry_name:
            self.select_entry_by_name(current_entry_name)

    def database_updated(self):
        self.update_list()
        if self.current_entry:
            self.update_info_frame()

    def select(self, index):
        """use this to select an entry"""
        self.password_list.select(index)
        self.on_select(index)

    def replace_password(self):
        selects = self.selected_count
        entry = self.current_entry
        if entry is None:
            return 
        new_password = ask_new_password() # lasts a while
        if new_password is None:
            return 
        if selects == self.selected_count and \
           self.current_entry == entry:
            self.set_current_password_in_entry(new_password)
            self.save_info()
        else:
            self.copy_password_to_clipboard(new_password)
            text = "A different list entry was selected. \n"\
                   "The new password was copied to the clipboard. \n"
            if not self.switched_entries(selects):
                text += "The current password entry should be the "\
                        "same but has changed although "\
                        "you did not click. Maybe the application "\
                        "is open twice?"
            notify(text, 0)
    
    def select_by_letter(self, event = None):
        letter = event.char
        if not letter:
            return
        if event.keysym == "BackSpace":
            while True:
                self.last_pressed = self.last_pressed[:-1]
                if not self.last_pressed or self.last_pressed[-1] != " ":
                    break
        else:
            self.last_pressed += letter
        # list already updated
        beginnings = self.last_pressed.split()
        entries = self.password_entries
        if entries:
            self.select(max(enumerate(entries),
                            key=lambda i_entry: sum(any(part.startswith(beginning) for beginning in beginnings)
                                                for part in i_entry[1].name.lower().split()))[0])
        if self.subset_removal_after_id is not None:
            self.after_cancel(self.subset_removal_after_id)
        self.subset_removal_after_id = self.after(REMOVE_SUBSET_AFTER_MILLISECONDS, self.reset_last_pressed)

    def reset_last_pressed(self, event=None):
        self.subset_removal_after_id = None
        self.last_pressed = ""
        
    def entry_matches(self, entry):
        matches = self.last_pressed.split()
        name = entry.name.lower()
        return all(match in name for match in matches)
    
    @property
    def last_pressed(self):
        return self.last_pressed_variable.get()
    @last_pressed.setter
    def last_pressed(self, value):
        self.last_pressed_variable.set(value.lower())
        self.last_pressed_changed()
        
    def last_pressed_changed(self, event=None):
        self.update_list()
        self.update_choose_list_entry()

    @property
    def switched_entries(self, selects):
        return selects != self.selected_count

    def close(self, event = None):
        self.quit()
        self.destroy()

    def minimize(self, event = None):
        self.iconify()
        self.reset_last_pressed()

    def new_password(self, event = None):
        with self.updating_database:
            self.database.add_new_password_from_user()

    def update_list(self):
        current_entry = self.current_entry
        self.password_list.clear()
        for entry in self.password_entries:
            self.password_list.append(entry.as_list_entry)
            if entry.deleted:
                self.password_list.listbox.itemconfigure(tk.END,
                                                         background = 'gray80')
            if current_entry and current_entry.name == entry.name:
                self.password_list.select(tk.END)
        if not self.password_entries:
            self.password_list.listbox.delete(0, tk.END)
        self.update_info_frame()

    @property
    def password_entries(self):
        with self.database:
            entries = self.database.passwords
        if not self.show_deleted_entries.get():
            entries = [entry for entry in entries if not entry.deleted]
        selected_entries = [entry for entry in entries if self.entry_matches(entry)]
        return selected_entries

    def update_info_frame(self, entry = None):
        if entry is None:
            entry = self.current_entry
            if entry is None:
                return
        self.entry_name_entry.delete(0, tk.END)
        self.entry_name_entry.insert(0, entry.name)
        self.entry_text.delete("0.0", tk.END)
        self.entry_text.insert(tk.END, entry.text)
        self.entry_password_button['command'] = lambda: self.show_password(entry)
        self.hide_password()

    def save_info(self, event = None):
        name = self.entry_name_entry.get()
        text = self.entry_text.get("0.0", tk.END)
        new_password = self.entry_password_entry.get()
        old_password = self.password_shown
        set_password = old_password != new_password and \
                       messagebox.askyesno("Change Password?", "Should the password be changed?")
        with self.database:
            current_entry = self.current_entry
            current_entry.name = name
            current_entry.text = text
            if set_password:
                # do not delete the password
                duplicate_entry = current_entry.duplicate(password = new_password)
                assert duplicate_entry.password == new_password
                current_entry.deleted = True
        self.update_list()
        self.update_info_frame()

    def hide_password(self):
        self.entry_password_button.pack(fill = tk.X)
        self.copy_password_from_database('')
        self.entry_password_entry.pack_forget()

    def show_password(self, entry):
        password = entry.password
        self.copy_password_from_database(password)
        self.entry_password_button.pack_forget()
        self.entry_password_entry.pack(fill = tk.X)

    def copy_password_from_database(self, password):
        self.password_shown = password
        self.set_current_password_in_entry(password)

    def set_current_password_in_entry(self, password):
        self.entry_password_entry.delete(0, tk.END)
        self.entry_password_entry.insert(0, password)
        
    def copy_current_password_to_clipboard(self, event = None):
        password = self.current_entry.password
        self.copy_password_to_clipboard(password)

    def copy_password_to_clipboard(self, password):
        self.clipboard_clear()
        self.clipboard_append(password)
        notify_about_copy()

    def show_deleted_passwords(self, event = None):
        self.database_updated()

    def delete_password(self, event = None):
        with self.updating_database:
            if self.current_entry.deleted:
                message = 'Do you want to delete {} for ever?'.format(self.current_entry.name)
                if messagebox.askokcancel('Delete?', message):
                    self.current_entry.remove()
            else:
                self.current_entry.deleted = True

    def restore_password(self, event = None):
        with self.updating_database:
            self.current_entry.deleted = False

    @property
    def current_index(self):
        return self.password_list.listbox.index("active")

    @property
    def current_entry(self):
        index = self.current_index
        entries = self.password_entries
        if index not in range(len(entries)):
            return None
        return entries[index]

    def import_passwords(self, event = None):
        file_name = filedialog.askopenfilename(filetypes = [("all files", "*")])
        log_file = io.StringIO()
        try:
            self.database.import_all_json(file_name, log_file)
        except:
            traceback.print_exc(file = log_file)
        finally:
            log_file.seek(0)
            notify_file(log_file)
        self.update_list()
        if self.current_entry:
            self.update_info_frame()
        

    def fill_menu(self):
        # after current_entry is updated
        self.after(1, self.menu_posted, self.password_list.menu)

    def export_passwords(self):
        file_name = filedialog.asksaveasfilename(filetypes = [("all files", "*")])
        if not file_name:
            return 
        with open(file_name, 'w') as file:
            self.database.export_all_json(file)

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
                             command = self.copy_current_password_to_clipboard)
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
        menu.add_command(label = "export all", underline = 0, 
                         command = self.export_passwords)

    def on_select(self, index):
        self.selected_count += 1
        if self.current_entry:
            self.update_info_frame()

    def on_double(self, index):
        if self.current_entry:
            self.copy_current_password_to_clipboard(self.current_entry)
    
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
