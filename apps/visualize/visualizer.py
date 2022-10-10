import os
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Tuple

from django.db import connection
from django.db.migrations.exceptions import NodeNotFoundError
from django.db.migrations.graph import MigrationGraph, Node
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone
from graphviz import Digraph


class TimeBasedMigrationLoader(MigrationLoader):
    def __init__(self, *args, date: datetime = timezone.now(), **kwargs) -> None:
        self.date = date
        super().__init__(*args, **kwargs)

    def build_graph(self) -> None:
        """
        Build a migration dependency graph using both the disk and database.
        You'll need to rebuild the graph if you apply migrations. This isn't
        usually a problem as generally migration stuff runs in a one-shot process.
        """
        # Load disk data
        self.load_disk()
        # Load database data
        if self.connection is None:
            self.applied_migrations = {}
        else:
            recorder = MigrationRecorder(self.connection)
            filtered_migration_qs = recorder.migration_qs.filter(applied__lt=self.date)

            self.applied_migrations = (
                {
                    (migration.app, migration.name): migration
                    for migration in filtered_migration_qs
                }
                if recorder.has_table()
                else {}
            )

        # To start, populate the migration graph with nodes for ALL migrations
        # and their dependencies. Also make note of replacing migrations at this step.
        # TODO: filter disk migrations based if they are in `self.applied_migrations``
        self.graph = MigrationGraph()
        self.replacements = {}
        for key, migration in self.disk_migrations.copy().items():
            # TODO: check this... remove from disk migrations if not applied in db
            if key not in self.applied_migrations:
                del self.disk_migrations[key]
                continue

            self.graph.add_node(key, migration)

            # Replacing migrations.
            if migration.replaces:
                self.replacements[key] = migration
        for key, migration in self.disk_migrations.items():
            # Internal (same app) dependencies.
            self.add_internal_dependencies(key, migration)
        # Add external dependencies now that the internal ones have been resolved.
        for key, migration in self.disk_migrations.items():
            self.add_external_dependencies(key, migration)
        # Carry out replacements where possible and if enabled.
        if self.replace_migrations:
            for key, migration in self.replacements.items():
                # Get applied status of each of this migration's replacement
                # targets.
                applied_statuses = [
                    (target in self.applied_migrations) for target in migration.replaces
                ]
                # The replacing migration is only marked as applied if all of
                # its replacement targets are.
                if all(applied_statuses):
                    self.applied_migrations[key] = migration
                else:
                    self.applied_migrations.pop(key, None)
                # A replacing migration can be used if either all or none of
                # its replacement targets have been applied.
                if all(applied_statuses) or (not any(applied_statuses)):
                    self.graph.remove_replaced_nodes(key, migration.replaces)
                else:
                    # This replacing migration cannot be used because it is
                    # partially applied. Remove it from the graph and remap
                    # dependencies to it (#25945).
                    self.graph.remove_replacement_node(key, migration.replaces)
        # Ensure the graph is consistent.
        try:
            self.graph.validate_consistency()
        except NodeNotFoundError as excp:
            # Check if the missing node could have been replaced by any squash
            # migration but wasn't because the squash migration was partially
            # applied before. In that case raise a more understandable exception
            # (#23556).
            # Get reverse replacements.
            reverse_replacements = {}
            for key, migration in self.replacements.items():
                for replaced in migration.replaces:
                    reverse_replacements.setdefault(replaced, set()).add(key)
            # Try to reraise exception with more detail.
            if excp.node in reverse_replacements:
                candidates = reverse_replacements.get(excp.node, set())
                is_replaced = any(
                    candidate in self.graph.nodes for candidate in candidates
                )
                if not is_replaced:
                    tries = ", ".join("%s.%s" % c for c in candidates)
                    raise NodeNotFoundError(
                        "Migration {0} depends on nonexistent node ('{1}', '{2}'). "
                        "Django tried to replace migration {1}.{2} with any of [{3}] "
                        "but wasn't able to because some of the replaced migrations "
                        "are already applied.".format(
                            excp.origin, excp.node[0], excp.node[1], tries
                        ),
                        excp.node,
                    ) from excp
            raise
        self.graph.ensure_not_cyclic()


class MigrationVisualizer:
    def __init__(
        self,
        *,
        output_format: str = "pdf",
        filename: str = "migration_snapshot",
        delimiter: str = "/",
        **options: dict,
    ) -> None:
        self.graph = TimeBasedMigrationLoader(
            options.get("connection", connection),
            date=options.get("date", timezone.now()),
        ).graph

        self.delimiter = delimiter
        self.filename = os.path.splitext(filename)[0]
        self.digraph = Digraph(comment=options.get("comment"), format=output_format)

    @property
    def source(self) -> str:
        return self.digraph.source

    def _construct_digraph(self) -> None:
        nodes = sorted(self.graph.nodes.values(), key=self._node_details)
        for node in nodes:
            self._add_node(node)
        for node in nodes:
            self._add_deps(node)

    def _format_label(self, tupled_node: Tuple[str, str]) -> str:
        return f"{self.delimiter}".join(tupled_node)

    @staticmethod
    def _node_details(node: Node) -> Tuple[str, str]:
        return (node.app_label, node.name)

    def _add_node(self, node: Node) -> None:
        node_label = self._format_label(self._node_details(node))
        self.digraph.node(node_label, node_label)

    def _add_edges(self, node_to: Node, node_from: Node) -> None:
        self.digraph.edge(self._format_label(node_from), self._format_label(node_to))

    def _add_deps(self, node: Node) -> None:
        for dep in node.dependencies:
            if dep[1] == "__first__":
                self._add_edges(
                    self.graph.root_nodes(dep[0])[0], self._node_details(node)
                )
            elif dep[1] == "__latest__":
                self._add_edges(
                    self.graph.leaf_nodes(dep[0])[0], self._node_details(node)
                )
            else:
                self._add_edges(dep, self._node_details(node))

    def render(self, *, view: bool = False, temp_file: bool = False, **kwargs) -> None:
        self._construct_digraph()
        if temp_file is True:
            with NamedTemporaryFile() as temp:
                self.digraph.render(temp.name, view=True, **kwargs)
        else:
            self.digraph.render(self.filename, view=view, **kwargs)


"""
from visualize.visualizer import MigrationVisualizer
file = MigrationVisualizer().render(temp_file=True)
"""
