# -*- coding: utf-8 -*-
try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

from encryption import new_random_password, PASSWORD_CHARACTERS, character_ranges

PASSWORD_CHARACTER = u'\u25CF'


def dialog(create_dialog_content):
    def create_dialog(*args, **kw):
        root = tk.Toplevel()
        content_frame = tk.Frame(root)
        content_frame.pack(fill = tk.BOTH, expand = True)        
        def ok(event = None):
            result.append(return_function())
            root.quit()
            root.destroy()
        def cancel(event = None):
            result.append(None)
            root.quit()
            root.destroy()
        buttons_frame = tk.Frame(master = root)
        buttons_frame.pack()
        ok_button = tk.Button(master = buttons_frame, text = '  OK  ', command = ok)
        ok_button.pack(side = tk.LEFT)
        cancel_button = tk.Button(master = buttons_frame, text = '   X   ', command = cancel)
        cancel_button.pack(side = tk.LEFT)
        result = []
        root.bind("<KeyPress-Return>", ok)
        root.bind("<KeyPress-Escape>", cancel)
        root.protocol("WM_DELETE_WINDOW", cancel)
        values = create_dialog_content(content_frame, *args, **kw)
        title, return_function = values
        root.title(title)
        root.mainloop()
        return (result[0] if result else None)
    return create_dialog

@dialog
def ask_password(root, question):
    question_label = tk.Label(master = root, text = question)
    question_label.pack(fill = tk.BOTH, expand = True)
    password_entry = tk.Entry(master = root, show = PASSWORD_CHARACTER)
    password_entry.pack(fill = tk.X, expand = True)
    password_entry.focus_set()
    password_entry.bind('<FocusIn>', lambda e: password_entry.configure(background = 'white'))
    def focus_out(event):
        password_entry.configure(background = 'red')
        password_entry.bell()
    password_entry.bind('<FocusOut>', focus_out)
    return 'password?', password_entry.get

@dialog
def ask_add_password(entry_frame, name = '', password = None, text = ''):
    name_label = tk.Label(master = entry_frame, text = 'name')
    name_label.grid(column = 0, row = 0)
    name_entry = tk.Entry(master = entry_frame)
    name_entry.grid(column = 1, row = 0, sticky = tk.W + tk.E,
                    columnspan = 2)
    name_entry.insert(0, name)
    
    password_label = tk.Label(master = entry_frame, text = 'password')
    password_label.grid(column = 0, row = 1)
    password_entry = tk.Entry(master = entry_frame, show = PASSWORD_CHARACTER)
    password_entry.grid(column = 1, row = 1, sticky = tk.W + tk.E)
    if password is None:
        password = new_random_password()
    password_entry.insert(0, password)
    bind_copy(password_entry)

    def new_password(event = None):
        password = ask_new_password()
        password_entry.delete(0, tk.END)
        password_entry.insert(0, password)
    new_password_button = tk.Button(master = entry_frame, text = "new",
                                     command = new_password)
    new_password_button.grid(column = 2, row = 1)
    
    text_label = tk.Label(master = entry_frame, text = 'info')
    text_label.grid(column = 0, row = 2, sticky = tk.E + tk.S + tk.N)
    textbox = tk.Text(master = entry_frame, height = 3, width = 20)
    textbox.grid(column = 1, row = 2, sticky = tk.W + tk.E + tk.S + tk.N,
                 columnspan = 2)
    textbox.insert(tk.END, text)
    def return_press(event):
        textbox.insert(tk.INSERT, '\n')
        return "break"
    textbox.bind("<KeyPress-Return>", return_press)
    name_entry.focus_set()
    return 'New Password', lambda: (name_entry.get(),
                                    password_entry.get(),
                                    textbox.get('0.0', tk.END))

def bind_copy(password_entry):
    def copy_password(event = None):
        password_entry.clipboard_clear()
        password_entry.clipboard_append(password_entry.get())
        notify_about_copy()
        return "break"
    password_entry.bind('<Control-c>', copy_password)
    password_entry.bind('<Control-C>', copy_password)
    def enter(event = None):
        password_entry.selection_range(0, tk.END)
    password_entry.bind('<FocusIn>', enter)

@dialog
def ask_new_password(root, title = 'Generate Password'):
    password_frame = tk.Frame(root)
    password_frame.pack(fill = tk.X)
    password_entry = tk.Entry(password_frame, show = PASSWORD_CHARACTER)
    bind_copy(password_entry)
    password_entry.pack(side = tk.LEFT, fill = tk.X, expand = True)

    def new_password(event = None):
        password_length = number_of_chracters_entry.get()
        if not password_length.isdigit():
            if not password_length and event:
                return
            else:
                password_length = '16'
            number_of_chracters_entry.delete(0, tk.END)
            number_of_chracters_entry.insert(0, password_length)
        password_length = int(password_length)
        characters = get_characters()
        if not characters:
            return
        new_password = new_random_password(password_length, characters)
        password_entry.delete(0, tk.END)
        root.after(100, password_entry.insert, 0, new_password)

    number_of_chracters_entry = tk.Entry(password_frame, width = 2)
    number_of_chracters_entry.insert(0, '16')
    number_of_chracters_entry.bind('<KeyRelease>', new_password)
    number_of_chracters_entry.pack(side = tk.LEFT)
        
    new_password_button = tk.Button(password_frame, command = new_password,
                                    text = 'new')
    new_password_button.pack(side = tk.LEFT)

    characters_frame = tk.Frame(root)
    characters_frame.pack(fill = tk.X)

    characters_text = tk.Text(root,  width = 30, height = 5)
    characters_text.insert('0.0', PASSWORD_CHARACTERS)
    characters_text.pack(fill = tk.BOTH, expand = True)
    def get_characters():
        characters = characters_text.get('0.0', tk.END)
        characters = [character for character in characters if ord(character) > 32]
        return ''.join(characters)
    def toggle_characters(new_characters):
        characters = get_characters()
        if any(character in characters for character in new_characters):
            for character in new_characters:
                characters = characters.replace(character, '')
        else:
            characters = ''.join(new_characters) + characters
        characters_text.delete('0.0', tk.END)
        characters_text.insert('0.0', characters)
        new_password()


    alhabet_button = tk.Button(characters_frame, text = 'a-zA-Z',
        command = lambda: toggle_characters(character_ranges('az', 'AZ')))
    alhabet_button.pack(side = tk.LEFT)

    numbers_button = tk.Button(characters_frame, text = '0-9',
        command = lambda: toggle_characters(character_ranges('09')))
    numbers_button.pack(side = tk.LEFT)

    specials_button = tk.Button(characters_frame, text = '!-~',
        command = lambda: toggle_characters(character_ranges('!/', ':@', '[`', '{~')))
    specials_button.pack(side = tk.LEFT)

    russian_button = tk.Button(characters_frame, text = 'а-яА-Я',
        command = lambda: toggle_characters(character_ranges('ая', 'АЯ')))
    russian_button.pack(side = tk.LEFT)
    new_password()
    return title, lambda: password_entry.get()

def notify(text, duration_seconds):
    root = tk.Toplevel()
    textbox = tk.Text(master = root, width = 40, height = 2)
    textbox.insert(tk.END, text)
    textbox.pack(fill = tk.BOTH, expand = True)
    if duration_seconds:
        _cancel = root.after(int(duration_seconds * 1000), root.destroy)
    def cancel():
        root.destroy()
        if duration_seconds:
            root.after_cancel(_cancel)
    button = tk.Button(master = root, text = '   X   ', command = cancel)
    button.pack(side = tk.LEFT)

def notify_about_copy():
    notify("The password was copied.", 1)
    
def notify_file(file):
    try:
        file.seek(0)
    except:
        pass
    notify(file.read(), None)

__all__ = ['ask_password', 'ask_add_password', 'notify_about_copy', 'notify',
           'notify_file', 'ask_new_password']

if __name__ == '__main__':
    print(ask_add_password())
