import sys
from typing import Iterator, Optional, TextIO

import docutils

from . import rstfmt


class DumpVisitor(docutils.nodes.GenericNodeVisitor):
    def __init__(self, document: docutils.nodes.document, file: Optional[TextIO] = None) -> None:
        super().__init__(document)
        self.depth = 0
        self.file = file or sys.stdout

    def default_visit(self, node: docutils.nodes.Node) -> None:
        t = type(node).__name__
        print("    " * self.depth + f"- \x1b[34m{t}\x1b[m", end=" ", file=self.file)
        if isinstance(node, docutils.nodes.Text):
            print(repr(node.astext()[:100]), end="", file=self.file)
        else:
            print({k: v for k, v in node.attributes.items() if v}, end="", file=self.file)
        print(file=self.file)

        self.depth += 1

    def default_departure(self, node: docutils.nodes.Node) -> None:
        self.depth -= 1


def dump_node(node: docutils.nodes.Node, file: TextIO) -> None:
    node.walkabout(DumpVisitor(node, file))


def iter_descendants(node: docutils.nodes.Node) -> Iterator[docutils.nodes.Node]:
    for c in node.children:
        yield c
        yield from iter_descendants(c)


def text_contents(node: docutils.nodes.Node) -> str:
    return "".join(n.astext() for n in iter_descendants(node) if isinstance(n, docutils.nodes.Text))


def node_eq(d1: docutils.nodes.Node, d2: docutils.nodes.Node) -> bool:
    if type(d1) is not type(d2):
        print("different type")
        return False

    if isinstance(d1, docutils.nodes.Text):
        return bool(d1.astext().split() == d2.astext().split())
    else:
        sentinel = object()
        for k in ["name", "refname", "refuri"]:
            if d1.attributes.get(k, sentinel) != d2.attributes.get(k, sentinel):
                print("different attributes")
                print(d1.attributes)
                print(d2.attributes)
                return False

    if isinstance(d1, docutils.nodes.literal_block):
        if "python" in d1["classes"]:
            import black

            # Check that either the outputs are equal or both calls to Black fail to parse.
            t1 = t2 = object()
            try:
                t1 = black.format_str(text_contents(d1), mode=black.FileMode())
            except black.InvalidInput:
                pass
            try:
                t2 = black.format_str(text_contents(d2), mode=black.FileMode())
            except black.InvalidInput:
                pass
            return bool(t1 == t2)

    if len(d1.children) != len(d2.children):
        print("different num children")
        for i, c in enumerate(d1.children):
            print(1, i, c)
        for i, c in enumerate(d2.children):
            print(2, i, c)
        return False
    return all(node_eq(c1, c2) for c1, c2 in zip(d1.children, d2.children))


def run_test(doc: docutils.nodes.document) -> None:
    if isinstance(doc, str):
        doc = rstfmt.parse_string(doc)

    for width in [1, 2, 3, 5, 8, 13, 34, 55, 89, 144, 72, None]:
        output = rstfmt.format_node(width, doc)
        doc2 = rstfmt.parse_string(output)
        output2 = rstfmt.format_node(width, doc2)

        try:
            assert node_eq(doc, doc2)
            assert output == output2
        except AssertionError:
            with open("/tmp/dump1.txt", "w") as f:
                dump_node(doc, f)
            with open("/tmp/dump2.txt", "w") as f:
                dump_node(doc2, f)

            with open("/tmp/out1.txt", "w") as f:
                print(output, file=f)
            with open("/tmp/out2.txt", "w") as f:
                print(output2, file=f)

            raise
