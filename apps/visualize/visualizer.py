from tempfile import NamedTemporaryFile

from django.db import connection
from django.db.migrations.exceptions import NodeNotFoundError
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone
from graphviz import Digraph


class TimeBasedMigrationLoader(MigrationLoader):
    def __init__(self, *args, date=timezone.now(), **kwargs):
        self.date = date
        super().__init__(*args, **kwargs)

    def build_graph(self):
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
        except NodeNotFoundError as exc:
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
            if exc.node in reverse_replacements:
                candidates = reverse_replacements.get(exc.node, set())
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
                            exc.origin, exc.node[0], exc.node[1], tries
                        ),
                        exc.node,
                    ) from exc
            raise
        self.graph.ensure_not_cyclic()


class MigrationVisualizer:
    def __init__(
        self, *apps, output_format=None, filename="migration-tree-dep", **options
    ):
        self.graph = TimeBasedMigrationLoader(
            connection,
            date=options.get("date", timezone.now()),  # TODO: use no connection?
        ).graph
        comment = options.get("comment")
        self.picture = Digraph(comment=comment, format=output_format)
        self.filename = filename

    @property
    def source(self):
        return self.picture.source

    def _create_digraph(self):
        nodes = sorted(self.graph.nodes.values(), key=self._get_tuple)
        for node in nodes:
            self._add_node(node)
        for node in nodes:
            self._add_dependencies(node)

    def _style_label(self, tupled_node):
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

    def render(self, save_loc=None, view=False, **kwargs):
        if save_loc is None:
            save_loc = self.filename

        self._create_digraph()
        if save_loc:
            self.picture.render(save_loc, view=view, **kwargs)
        else:
            with NamedTemporaryFile() as temp:
                self.picture.render(temp.name, view=True, **kwargs)

        # temp = NamedTemporaryFile()
        # self.picture.render(temp.name, view=False)
        # temp.seek(0)
        # return temp


"""
from visualize.visualizer import MigrationVisualizer
file = MigrationVisualizer(None, filename=None).render()
"""
