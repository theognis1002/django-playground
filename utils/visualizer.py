import random
from datetime import datetime
from tempfile import NamedTemporaryFile

from django.db.migrations.loader import MigrationLoader
from graphviz import Digraph


class MigrationVisualizer:
    def __init__(self, *apps, **options):
        self._censor_cache = {}
        self._censor_enabled = bool(options.get("censor", False))
        if self._censor_enabled:
            random.seed(options.get("random_seed", datetime.now()))
        self.graph = MigrationLoader(None).graph
        comment = options.get("comment")
        self.picture = Digraph(comment=comment)
        save_loc = options.get("filename", "migration-dep-tree")
        self._render(save_loc)

    @property
    def source(self):
        return self.picture.source

    def _create_digraph(self):
        nodes = sorted(self.graph.nodes.values(), key=self._get_tuple)
        for node in nodes:
            self._add_node(node)
        for node in nodes:
            self._add_dependencies(node)

    @staticmethod
    def _censor(text):
        res = []
        for word in text.split("_"):
            if word not in ("auto", "initial", "squashed"):
                chars = []
                for c in word:
                    if c not in "0123456789_":
                        c = chr(random.randint(ord("a"), ord("z")))
                    chars.append(c)
                word = "".join(chars)
            res.append(word)
        return "_".join(res)

    def _censor_using_cache(self, text):
        try:
            return self._censor_cache[text]
        except KeyError:
            while True:
                censored = self._censor(text)
                if censored not in self._censor_cache.values():
                    break
            self._censor_cache[text] = censored
            return censored

    def _style_label(self, tupled_node):
        if self._censor_enabled:
            tupled_node = [self._censor_using_cache(e) for e in tupled_node]

        return "/".join(tupled_node)

    @staticmethod
    def _get_tuple(node):
        return (node.app_label, node.name)

    def _add_node(self, node):
        node_label = self._style_label(self._get_tuple(node))
        self.picture.node(node_label, node_label)

    def _add_edges(self, nodeTo, nodeFrom):
        self.picture.edge(self._style_label(nodeFrom), self._style_label(nodeTo))

    def _add_dependencies(self, node):
        for dep in node.dependencies:
            if dep[1] == "__first__":
                self._add_edges(self.graph.root_nodes(dep[0])[0], self._get_tuple(node))
            elif dep[1] == "__latest__":
                self._add_edges(self.graph.leaf_nodes(dep[0])[0], self._get_tuple(node))
            else:
                self._add_edges(dep, self._get_tuple(node))

    def _render(self, save_loc):
        self._create_digraph()
        if save_loc:
            self.picture.render(save_loc, view=False)
        else:
            with NamedTemporaryFile() as temp:
                self.picture.render(temp.name, view=True)

        print(self.source)
