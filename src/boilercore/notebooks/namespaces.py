"""Notebook namespaces."""

import ast
from ast import NodeVisitor
from collections import defaultdict
from collections.abc import Callable, Iterable
from functools import partial
from inspect import getsource
from textwrap import dedent
from types import SimpleNamespace
from typing import Any, TypeAlias

from cachier import cachier
from nbformat import NO_CONVERT, reads
from ploomber_engine._util import parametrize_notebook
from ploomber_engine.ipython import PloomberClient

from boilercore.hashes import hash_args

Params: TypeAlias = dict[str, Any]
Attributes: TypeAlias = Iterable[str]
SimpleNamespaceReceiver: TypeAlias = Callable[..., Any]
"""Should be a `Callable` with an `ns` parameter expecting a `SimpleNamespace`."""

NO_ATTRS = []
NO_PARAMS = {}


def get_minimal_nb_ns(
    nb: str, receiver: SimpleNamespaceReceiver, params: Params = NO_PARAMS
) -> SimpleNamespace:
    """Get minimal namespace suitable for passing to a receiving function."""
    return get_nb_ns(nb, params, attributes=get_ns_attrs(receiver))


@cachier(hash_func=partial(hash_args, get_minimal_nb_ns))
def get_cached_minimal_nb_ns(
    nb: str, receiver: SimpleNamespaceReceiver, params: Params = NO_PARAMS
) -> SimpleNamespace:
    """Get cached minimal namespace suitable for passing to a receiving function."""
    return get_minimal_nb_ns(nb, receiver, params)


def get_ns_attrs(receiver: SimpleNamespaceReceiver) -> list[str]:
    """Get the list of attribute accesses in the `ns` namespace in the receiver."""
    attributes = AccessedAttributesVisitor()
    attributes.visit(ast.parse(dedent(getsource(receiver))))
    return list(attributes.names["ns"])


def get_nb_ns(
    nb: str, params: Params = NO_PARAMS, attributes: Attributes = NO_ATTRS
) -> SimpleNamespace:
    """Get notebook namespace, optionally parametrizing it."""
    nb_client = get_nb_client(nb)
    # We can't just `nb_client.execute(params=...)` since`nb_client.get_namespace()`
    # would execute all over again
    if params:
        parametrize_notebook(nb_client._nb, parameters=params)  # noqa: SLF001
    namespace = nb_client.get_namespace()
    return SimpleNamespace(
        **(
            {
                attr: namespace[attr]
                for attr in attributes
                if namespace.get(attr) is not None
            }
            if attributes
            else namespace
        )
    )


def get_nb_client(nb: str) -> PloomberClient:
    """Get notebook client."""
    return PloomberClient(reads(nb, as_version=NO_CONVERT))


class AccessedAttributesVisitor(NodeVisitor):
    def __init__(self):
        """Maps accessed attributes to their namespaces."""
        self.names: dict[str, set[str]] = defaultdict(set)

    def visit_Attribute(self, node: ast.Attribute):  # noqa: N802
        if isinstance(node.value, ast.Name) and not node.attr.startswith("__"):
            self.names[node.value.id].add(node.attr)
        self.generic_visit(node)
