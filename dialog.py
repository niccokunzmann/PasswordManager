try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk


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
    return 'password?', password_entry.get

@dialog
def ask_add_password(entry_frame, name = '', password = None, text = ''):
    name_label = tk.Label(master = entry_frame, text = 'name')
    name_label.grid(column = 0, row = 0)
    name_entry = tk.Entry(master = entry_frame)
    name_entry.grid(column = 1, row = 0, sticky = tk.W + tk.E)
    name_entry.insert(0, name)
    
    password_label = tk.Label(master = entry_frame, text = 'password')
    password_label.grid(column = 0, row = 1)
    password_entry = tk.Entry(master = entry_frame, show = PASSWORD_CHARACTER)
    password_entry.grid(column = 1, row = 1, sticky = tk.W + tk.E)
    password_entry.insert(0, password)
    
    text_label = tk.Label(master = entry_frame, text = 'info')
    text_label.grid(column = 0, row = 2, sticky = tk.E + tk.S + tk.N)
    textbox = tk.Text(master = entry_frame, height = 3, width = 20)
    textbox.grid(column = 1, row = 2, sticky = tk.W + tk.E + tk.S + tk.N)
    textbox.insert(tk.END, text)
    def enter(event = None):
        password_entry.selection_range(0, tk.END)
    password_entry.bind('<FocusIn>', enter)
    name_entry.focus_set()
    return 'New Password', lambda: (name_entry.get(),
                                    password_entry.get(),
                                    textbox.get('0.0', tk.END))

__all__ = ['ask_password', 'ask_add_password']
