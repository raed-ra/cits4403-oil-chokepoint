"""Path helper so notebooks can import the model modules in src/."""
import sys, os

def add_src_to_path():
    """Make src/ importable from a notebook in notebooks/."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    return root

def figures_dir():
    root = add_src_to_path()
    d = os.path.join(root, "figures")
    os.makedirs(d, exist_ok=True)
    return d
