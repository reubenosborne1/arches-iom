from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models import models

RESOURCE_ID_KEY = "@resource_id"
NODE_ID_KEY = "@node_id"
TILE_ID_KEY = "@tile_id"

NON_DATA_COLLECTING_NODE = "NON_DATA_COLLECTING_NODE"


class LabelBasedNode(object):
    def __init__(self, name, node_id, tile_id, value, cardinality=None):
        self.name = name
        self.node_id = node_id
        self.tile_id = tile_id
        self.cardinality = cardinality
        self.value = value
        self.child_nodes = []

    def is_empty(self):
        is_empty = True

        if self.value and self.value is not NON_DATA_COLLECTING_NODE:
            is_empty = False
        else:
            for child_node in self.child_nodes:
                if not child_node.is_empty():
                    is_empty = False

        return is_empty

    def as_json(self, compact=False, include_empty_nodes=True):
        display_data = {}

        for child_node in self.child_nodes:
            formatted_node = child_node.as_json(compact=compact, include_empty_nodes=include_empty_nodes)

            formatted_node_name, formatted_node_value = formatted_node.popitem()

            if include_empty_nodes or not child_node.is_empty():
                previous_val = display_data.get(formatted_node_name)
                cardinality = child_node.cardinality

                # let's handle multiple identical node names
                if not previous_val:
                    should_create_new_array = cardinality == "n" and self.tile_id != child_node.tile_id
                    display_data[formatted_node_name] = [formatted_node_value] if should_create_new_array else formatted_node_value
                elif isinstance(previous_val, list):
                    display_data[formatted_node_name].append(formatted_node_value)
                else:
                    display_data[formatted_node_name] = [previous_val, formatted_node_value]

        val = self.value
        if compact and display_data:
            if self.value is not NON_DATA_COLLECTING_NODE:
                if self.value is not None:
                    display_data.update(self.value)
        elif compact and not display_data:  # if compact and no child nodes
            display_data = self.value
        elif not compact:
            display_data[NODE_ID_KEY] = self.node_id
            display_data[TILE_ID_KEY] = self.tile_id
            if self.value is not None and self.value is not NON_DATA_COLLECTING_NODE:
                display_data.update(self.value)

        return {self.name: display_data}


class LabelBasedGraph(object):
    @staticmethod
    def generate_node_ids_to_tiles_reference_and_nodegroup_cardinality_reference(resource):
        """
        Builds a reference of all nodes in a in a given resource,
        paired with a list of tiles in which they exist
        """
        node_ids_to_tiles_reference = {}
        nodegroupids = set()

        for tile in resource.tiles:
            nodegroupids.add(str(tile.nodegroup_id))
            node_ids = list(tile.data.keys())

            if str(tile.nodegroup_id) not in node_ids:
                node_ids.append(str(tile.nodegroup_id))

            for node_id in node_ids:
                tile_list = node_ids_to_tiles_reference.get(node_id, [])
                tile_list.append(tile)
                node_ids_to_tiles_reference[node_id] = tile_list

        nodegroup_cardinality = models.NodeGroup.objects.filter(pk__in=nodegroupids).values("nodegroupid", "cardinality")
        nodegroup_cardinality_reference = {str(nodegroup["nodegroupid"]): nodegroup["cardinality"] for nodegroup in nodegroup_cardinality}

        return node_ids_to_tiles_reference, nodegroup_cardinality_reference

    @classmethod
    def from_tile(
        cls,
        tile,
        node_ids_to_tiles_reference,
        nodegroup_cardinality_reference=None,
        datatype_factory=None,
        node_cache=None,
        compact=False,
        hide_empty_nodes=False,
        as_json=True,
    ):
        """
        Generates a label-based graph from a given tile
        """
        if not datatype_factory:
            datatype_factory = DataTypeFactory()

        if node_cache is None:  # need explicit None comparison
            node_cache = {}

        nodegroup_id = tile.nodegroup_id

        node = node_cache.get(nodegroup_id)
        if not node:
            node = models.Node.objects.get(pk=nodegroup_id)
            node_cache[nodegroup_id] = node

        graph = cls._build_graph(
            input_node=node,
            input_tile=tile,
            parent_tree=None,
            node_ids_to_tiles_reference=node_ids_to_tiles_reference,
            nodegroup_cardinality_reference=nodegroup_cardinality_reference,
            node_cache=node_cache,
            datatype_factory=datatype_factory,
        )

        return graph.as_json(include_empty_nodes=bool(not hide_empty_nodes)) if as_json else graph

    @classmethod
    def from_resource(
        cls, resource, datatype_factory=None, node_cache=None, compact=False, hide_empty_nodes=False, as_json=True, user=None, perm=None
    ):
        """
        Generates a label-based graph from a given resource
        """
        if not datatype_factory:
            datatype_factory = DataTypeFactory()

        if node_cache is None:  # need explicit None comparison
            node_cache = {}

        if not resource.tiles:
            resource.load_tiles(user, perm)

        (
            node_ids_to_tiles_reference,
            nodegroup_cardinality_reference,
        ) = cls.generate_node_ids_to_tiles_reference_and_nodegroup_cardinality_reference(resource=resource)

        root_label_based_node = LabelBasedNode(name=None, node_id=None, tile_id=None, value=None, cardinality=None)

        for tile in resource.tiles:
            label_based_graph = LabelBasedGraph.from_tile(
                tile=tile,
                node_ids_to_tiles_reference=node_ids_to_tiles_reference,
                nodegroup_cardinality_reference=nodegroup_cardinality_reference,
                datatype_factory=datatype_factory,
                node_cache=node_cache,
                compact=compact,
                hide_empty_nodes=hide_empty_nodes,
                as_json=False,
            )

            if label_based_graph:
                root_label_based_node.child_nodes.append(label_based_graph)

        if as_json:
            root_label_based_node_json = root_label_based_node.as_json(compact=compact, include_empty_nodes=bool(not hide_empty_nodes))

            _dummy_resource_name, resource_graph = root_label_based_node_json.popitem()

            # removes unneccesary ( None ) top-node values
            for key in [NODE_ID_KEY, TILE_ID_KEY]:
                resource_graph.pop(key, None)

            # adds metadata that was previously only accessible via API
            return {
                "displaydescription": resource.displaydescription,
                "displayname": resource.displayname,
                "graph_id": resource.graph_id,
                "legacyid": resource.legacyid,
                "map_popup": resource.map_popup,
                "resourceinstanceid": resource.resourceinstanceid,
                "resource": resource_graph,
            }
        else:  # pragma: no cover
            return root_label_based_node

    @classmethod
    def from_resources(cls, resources, compact=False, hide_empty_nodes=False, as_json=True):
        """
        Generates a list of label-based graph from given resources
        """

        datatype_factory = DataTypeFactory()
        node_cache = {}

        resource_label_based_graphs = []

        for resource in resources:
            resource_label_based_graph = cls.from_resource(
                resource=resource,
                datatype_factory=datatype_factory,
                node_cache=node_cache,
                compact=compact,
                hide_empty_nodes=hide_empty_nodes,
                as_json=as_json,
            )

            resource_label_based_graph[RESOURCE_ID_KEY] = str(resource.pk)
            resource_label_based_graphs.append(resource_label_based_graph)

        return resource_label_based_graphs

    @classmethod
    def _get_display_value(cls, tile, node, datatype_factory):
        display_value = None

        # if the node is unable to collect data, let's explicitly say so
        if datatype_factory.datatypes[node.datatype].defaultwidget is None:
            display_value = NON_DATA_COLLECTING_NODE
        elif tile.data:
            datatype = datatype_factory.get_instance(node.datatype)

            # `get_display_value` varies between datatypes,
            # so let's handle errors here instead of nullguarding all models
            try:
                display_value = datatype.to_json(tile=tile, node=node)
            except:  # pragma: no cover
                pass

        return display_value

    @classmethod
    def _build_graph(
        cls, input_node, input_tile, parent_tree, node_ids_to_tiles_reference, nodegroup_cardinality_reference, node_cache, datatype_factory
    ):
        for associated_tile in node_ids_to_tiles_reference.get(str(input_node.pk), [input_tile]):
            parent_tile = associated_tile.parenttile

            if associated_tile == input_tile or parent_tile == input_tile:
                if (  # don't instantiate `LabelBasedNode`s of cardinality `n` unless they are semantic or have value
                    input_node.datatype == "semantic" or str(input_node.pk) in associated_tile.data
                ):
                    label_based_node = LabelBasedNode(
                        name=input_node.name,
                        node_id=str(input_node.pk),
                        tile_id=str(associated_tile.pk),
                        value=cls._get_display_value(tile=associated_tile, node=input_node, datatype_factory=datatype_factory),
                        cardinality=nodegroup_cardinality_reference.get(str(associated_tile.nodegroup_id)),
                    )

                    if not parent_tree:  # if top node and
                        if not parent_tile:  # if not top node in separate card
                            parent_tree = label_based_node
                    else:
                        parent_tree.child_nodes.append(label_based_node)

                    for child_node in input_node.get_direct_child_nodes():
                        if not node_cache.get(child_node.pk):
                            node_cache[child_node.pk] = child_node

                        cls._build_graph(
                            input_node=child_node,
                            input_tile=associated_tile,
                            parent_tree=label_based_node,
                            node_ids_to_tiles_reference=node_ids_to_tiles_reference,
                            nodegroup_cardinality_reference=nodegroup_cardinality_reference,
                            node_cache=node_cache,
                            datatype_factory=datatype_factory,
                        )

        return parent_tree
