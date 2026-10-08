"""Path helper so notebooks can import the model modules in src/."""
import sys, os                                           # Python settings (sys.path) and folder paths

def add_src_to_path():
    """Make src/ importable from a notebook in notebooks/."""
    here = os.path.dirname(os.path.abspath(__file__))    # this file's folder: .../utils
    root = os.path.dirname(here)                         # one level up: the project root
    src = os.path.join(root, "src")                      # .../src
    if src not in sys.path:                              # not already on the search list?
        sys.path.insert(0, src)                          # put src/ first in the list
    return root                                          # hand back the root folder

def figures_dir():
    """Return the project's figures/ folder, creating it if needed."""
    root = add_src_to_path()                             # make sure src/ is findable; get the root
    d = os.path.join(root, "figures")                    # .../figures
    os.makedirs(d, exist_ok=True)                        # create it if missing
    return d                                             # hand back the figures folder path
