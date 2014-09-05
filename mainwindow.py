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

from database import Database
from dialog import notify_about_copy, notify_file, ask_new_password, notify

LAST_PRESSED_TIME_INTERVAL = 0.5
    
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
        
        self.password_list.listbox.bind('<Any-KeyPress>', self.select_by_letter)
        self.password_list.listbox.bind('<Any-Return>', self.copy_current_password_to_clipboard)
        self.reset_last_pressed()

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
        self.bind('<KeyPress-Escape>', self.minimize)

        self.database_updated()
        self.hide_password()
        self.select(0)

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
            self.update_info_frame(self.current_entry)

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

    last_pressed_time_interval = LAST_PRESSED_TIME_INTERVAL
    
    def select_by_letter(self, event = None):
        letter = event.keysym
        if not letter:
            return
        if letter != ' ':
            found = False
            for name in self.entry_names:
                if letter in name:
                    found = True
            if not found:
                return
        self.last_pressed += letter
        self.restart_last_pressed_reset()
        self.select_entry_by_name(self.last_pressed,
                                  select_next_best_entry = True)

    def restart_last_pressed_reset(self):
        if self.last_pressed_after_identifier:
            self.after_cancel(self.last_pressed_after_identifier)
        self.last_pressed_after_identifier = self.after(
            int(self.last_pressed_time_interval * 1000),
            self.reset_last_pressed)

    def reset_last_pressed(self):
        self.last_pressed_after_identifier = None
        self.last_pressed = ""

    @property
    def entry_names(self):
        return [entry.as_list_entry.lower() for entry in self.password_entries]

    def select_entry_by_name(self, name, select_next_best_entry = False):
        to_find = name.lower()
        names = self.entry_names
        index = None
        # find entry by starting string
        for i, name in enumerate(names):
            if name.startswith(to_find):
                index = i
                break
        # find entry by containing
        if index is None:
            for i, name in enumerate(names):
                if to_find in name:
                    index = i
                    break
        if index is not None:
            self.select(index)
        elif select_next_best_entry:
            # select next best entry
            index = self.current_index
            if index is not None and index < len(names) - 1:
                self.select(index + 1)

    def switched_entries(self, selects):
        return selects != self.selected_count

    def close(self, event = None):
        self.quit()
        self.destroy()

    def minimize(self, event = None):
        self.iconify()

    def new_password(self, event = None):
        with self.updating_database:
            self.database.add_new_password_from_user()

    def update_list(self):
        selection = self.password_list.listbox.curselection()
        self.password_list.clear()
        for entry in self.password_entries:
            self.password_list.append(entry.as_list_entry)
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
        self.update_info_frame(self.current_entry)

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
        if not self.password_entries:
            return None
        return self.password_entries[index]

    def import_passwords(self, event = None):
        file_name = filedialog.askopenfilename(filetypes = [("all files", "*")])
        log_file = io.StringIO()
        try:
            with open(file_name) as file:
                self.database.import_all_json(file, log_file)
        except:
            traceback.print_exc(file = log_file)
        finally:
            log_file.seek(0)
            notify_file(log_file)
        self.update_list()
        if self.current_entry:
            self.update_info_frame(self.current_entry)
        

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
            self.update_info_frame(self.current_entry)

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
    test_encrypt_and_decrypt_password()
##    root = MainWindow()
##    root.mainloop()
