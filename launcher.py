import sys, os
from streamlit.web import cli as stcli

def base():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    os.chdir(base())
    sys.argv = ["streamlit", "run", os.path.join(base(), "dashboard", "app.py"),
                "--global.developmentMode=false", "--server.headless=false"]
    sys.exit(stcli.main())