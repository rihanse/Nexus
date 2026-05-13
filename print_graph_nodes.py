"""
Print LangGraph nodes and edges for Workplace Buddy.

Run:
    python print_graph_nodes.py
"""

import importlib
import inspect
import sys


GRAPH_MODULE_NAME = "graph"

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
    "app",
    "compiled_graph",
    "compiled_workflow",
]


def get_compiled_graph():
    """
    Tries to find the LangGraph compiled graph from graph.py.
    Supports both:
    1. build_graph() style functions
    2. global compiled graph variables
    """

    graph_module = importlib.import_module(GRAPH_MODULE_NAME)

    # First try common graph builder functions
    for func_name in POSSIBLE_BUILD_FUNCTIONS:
        func = getattr(graph_module, func_name, None)

        if callable(func):
            print(f"[INFO] Found graph builder function: {func_name}")

            try:
                result = func()

                if hasattr(result, "get_graph"):
                    return result

            except TypeError:
                print(f"[SKIP] {func_name} requires arguments.")
            except Exception as error:
                print(f"[ERROR] Calling {func_name} failed: {error}")

    # Then try common global graph variables
    for obj_name in POSSIBLE_GRAPH_OBJECTS:
        obj = getattr(graph_module, obj_name, None)

        if obj is not None:
            print(f"[INFO] Found graph object: {obj_name}")

            if hasattr(obj, "get_graph"):
                return obj

    # Last attempt: scan all objects in graph.py
    for name, obj in inspect.getmembers(graph_module):
        if hasattr(obj, "get_graph"):
            print(f"[INFO] Found compiled graph by scanning module: {name}")
            return obj

    raise RuntimeError(
        "Could not find a compiled LangGraph object. "
        "Check graph.py and update POSSIBLE_BUILD_FUNCTIONS or POSSIBLE_GRAPH_OBJECTS."
    )


def print_nodes(graph_view):
    print("\n==============================")
    print("LANGGRAPH NODES")
    print("==============================")

    nodes = getattr(graph_view, "nodes", None)

    if not nodes:
        print("No nodes found.")
        return

    if isinstance(nodes, dict):
        for index, node_name in enumerate(nodes.keys(), start=1):
            print(f"{index}. {node_name}")
    else:
        for index, node in enumerate(nodes, start=1):
            print(f"{index}. {node}")


def print_edges(graph_view):
    print("\n==============================")
    print("LANGGRAPH EDGES")
    print("==============================")

    edges = getattr(graph_view, "edges", None)

    if not edges:
        print("No edges found.")
        return

    for index, edge in enumerate(edges, start=1):
        source = getattr(edge, "source", None)
        target = getattr(edge, "target", None)

        if source is not None and target is not None:
            print(f"{index}. {source}  -->  {target}")
        else:
            print(f"{index}. {edge}")


def print_ascii_graph(graph_view):
    print("\n==============================")
    print("ASCII GRAPH")
    print("==============================")

    if hasattr(graph_view, "draw_ascii"):
        try:
            print(graph_view.draw_ascii())
            return
        except Exception as error:
            print(f"[WARN] Could not draw ASCII graph: {error}")

    if hasattr(graph_view, "draw_mermaid"):
        try:
            print("\nMermaid diagram:")
            print(graph_view.draw_mermaid())
            return
        except Exception as error:
            print(f"[WARN] Could not draw Mermaid graph: {error}")

    print("ASCII/Mermaid drawing is not available for this graph object.")


def main():
    try:
        compiled_graph = get_compiled_graph()
        graph_view = compiled_graph.get_graph()

        print_nodes(graph_view)
        print_edges(graph_view)
        print_ascii_graph(graph_view)

    except Exception as error:
        print("\n[FAILED] Could not print graph.")
        print(f"Reason: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()