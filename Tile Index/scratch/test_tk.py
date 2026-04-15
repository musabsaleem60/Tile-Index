import tkinter
try:
    root = tkinter.Tk()
    print("Tkinter initialized")
    root.destroy()
except Exception as e:
    print(f"Tkinter error: {e}")
