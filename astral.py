from stlr.config import CONFIG
from stlr.astral import AstralApp


def main():
    AstralApp("astral", themename=CONFIG.ui_themes.astral).mainloop()


if __name__ == "__main__":
    main()
