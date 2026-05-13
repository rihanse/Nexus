"""
Generate PNG image of Workplace Buddy LangGraph.

Run:
    python generate_graph_png.py

Output:
    docs/workplace_buddy_graph.png
"""

import importlib
import inspect
from pathlib import Path


GRAPH_MODULE_NAME = "graph"

OUTPUT_DIR = Path("docs")
OUTPUT_FILE = OUTPUT_DIR / "workplace_buddy_graph.png"


POSSIBLE_BUILD_FUNCTIONS = [
    "build_graph",
    "create_graph",
    "get_graph",
    "compile_graph",
    "build_workflow",
    "create_workflow",
]

POSSIBLE_GRAPH_OBJECTS = [
    "graph",
    "workflow",
    "compiled_graph",
    "compiled_workflow",
    "app",
]


def get_compiled_graph():
    graph_module = importlib.import_module(GRAPH_MODULE_NAME)

    # Try common builder functions
    for func_name in POSSIBLE_BUILD_FUNCTIONS:
        func = getattr(graph_module, func_name, None)

        if callable(func):
            try:
                result = func()
                if hasattr(result, "get_graph"):
                    print(f"[INFO] Found graph builder: {func_name}")
                    return result
            except TypeError:
                print(f"[SKIP] {func_name} requires arguments.")
            except Exception as error:
                print(f"[WARN] {func_name} failed: {error}")

    # Try common global graph objects
    for obj_name in POSSIBLE_GRAPH_OBJECTS:
        obj = getattr(graph_module, obj_name, None)

        if obj is not None and hasattr(obj, "get_graph"):
            print(f"[INFO] Found compiled graph object: {obj_name}")
            return obj

    # Scan everything in graph.py
    for name, obj in inspect.getmembers(graph_module):
        if hasattr(obj, "get_graph"):
            print(f"[INFO] Found compiled graph by scanning: {name}")
            return obj

    raise RuntimeError(
        "Could not find compiled LangGraph object in graph.py. "
        "Check the variable/function name used to compile your graph."
    )


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    compiled_graph = get_compiled_graph()
    graph_view = compiled_graph.get_graph()

    print("[INFO] Generating PNG...")

    try:
        # Newer LangGraph/LangChain versions support output_file_path directly
        graph_view.draw_mermaid_png(output_file_path=str(OUTPUT_FILE))
    except TypeError:
        # Fallback for versions that return PNG bytes
        png_bytes = graph_view.draw_mermaid_png()
        OUTPUT_FILE.write_bytes(png_bytes)

    print(f"[SUCCESS] Graph PNG saved at: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()