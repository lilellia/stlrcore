from stlr.config import CONFIG
from stlr.ui import STLRApp


if __name__ == "__main__":
    STLRApp("stlr", themename=CONFIG.ui_themes.stlr).mainloop()
