import tkinter as tk

class TransparentWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Transparent Overlay')
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.5)  # Set the transparency level (0.0 to 1.0)
        self.root.geometry('400x400')  # Set window size
        self.root.configure(bg='blue')  # Set background color

        # Make the window click-through
        self.root.wm_attributes('-disabled', True)
        self.root.wm_attributes('-transparentcolor', 'blue')

        self.label = tk.Label(self.root, text='This is a transparent overlay', bg='blue', fg='white')
        self.label.pack(pady=20)

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    window = TransparentWindow()
    window.run()