from collections import ChainMap
from copy import deepcopy

from unittest import mock, TestCase

from arches.app.models import models
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.utils.label_based_graph_v2 import LabelBasedGraph, LabelBasedNode, NODE_ID_KEY, TILE_ID_KEY

# these tests can be run from the command line via
# python manage.py test tests/utils/label_based_graph_test_v2.py --pattern="*.py" --settings="tests.test_settings"


class LabelBasedNodeTests(TestCase):
    @classmethod
    def setUp(cls):
        cls.VALUE_KEY = "@display_value"

        cls.test_node = LabelBasedNode(
            name="test_node_name", node_id="test_node_node_id", tile_id="test_node_tile_id", value={cls.VALUE_KEY: "test_node_value"}
        )

        cls.test_node_json_data = {NODE_ID_KEY: cls.test_node.node_id, TILE_ID_KEY: cls.test_node.tile_id, cls.VALUE_KEY: "test_node_value"}

        cls.empty_node = LabelBasedNode(name="empty_node_name", node_id="empty_node_node_id", tile_id="empty_node_tile_id", value=None)

        cls.child_node_1 = LabelBasedNode(
            name="child_node_val", node_id="child_node_node_id", tile_id="child_node_tile_id", value={cls.VALUE_KEY: "child_node_value"}
        )

        cls.child_node_2 = LabelBasedNode(
            name="child_node_val", node_id="child_node_node_id", tile_id="child_node_tile_id", value={cls.VALUE_KEY: "child_node_value"}
        )

        cls.child_node_3 = LabelBasedNode(
            name="child_node_val", node_id="child_node_node_id", tile_id="child_node_tile_id", value={cls.VALUE_KEY: "child_node_value"}
        )

    def test_is_empty_with_node_with_child_nodes(self):
        self.empty_node.child_nodes.append(self.test_node)
        self.assertFalse(self.empty_node.is_empty())

    def test_is_node_empty_with_empty_node(self):
        self.assertTrue(self.empty_node.is_empty())

    def test_as_json(self):
        self.assertEqual(self.test_node.as_json(), {self.test_node.name: self.test_node_json_data})

    def test_as_json_compact(self):
        self.assertEqual(self.test_node.as_json(compact=True), {self.test_node.name: self.test_node.value})

    def test_as_json_compact_data_collecting_node_with_child(self):
        self.test_node.child_nodes.append(self.child_node_1)
        self.assertEqual(
            self.test_node.as_json(compact=True),
            {self.test_node.name: {self.child_node_1.name: self.child_node_1.value, self.VALUE_KEY: self.test_node.value[self.VALUE_KEY]}},
        )

    def test_as_json_single_child_node(self):
        self.test_node.child_nodes.append(self.child_node_1)

        self.test_node_json_data[self.child_node_1.name] = {
            NODE_ID_KEY: self.child_node_1.node_id,
            TILE_ID_KEY: self.child_node_1.tile_id,
            self.VALUE_KEY: self.child_node_1.value[self.VALUE_KEY],
        }

        self.assertEqual(self.test_node.as_json(), {self.test_node.name: self.test_node_json_data})

    def test_as_json_two_child_nodes(self):
        self.test_node.child_nodes.append(self.child_node_1)
        self.test_node.child_nodes.append(self.child_node_2)

        self.test_node_json_data[self.child_node_1.name] = [
            {
                NODE_ID_KEY: self.child_node_1.node_id,
                TILE_ID_KEY: self.child_node_1.tile_id,
                self.VALUE_KEY: self.child_node_1.value[self.VALUE_KEY],
            },
            {
                NODE_ID_KEY: self.child_node_2.node_id,
                TILE_ID_KEY: self.child_node_2.tile_id,
                self.VALUE_KEY: self.child_node_2.value[self.VALUE_KEY],
            },
        ]

        self.assertEqual(self.test_node.as_json(), {self.test_node.name: self.test_node_json_data})

    def test_as_json_many_child_nodes(self):
        self.test_node.child_nodes.append(self.child_node_1)
        self.test_node.child_nodes.append(self.child_node_2)
        self.test_node.child_nodes.append(self.child_node_3)

        self.test_node_json_data[self.child_node_1.name] = [
            {
                NODE_ID_KEY: self.child_node_1.node_id,
                TILE_ID_KEY: self.child_node_1.tile_id,
                self.VALUE_KEY: self.child_node_1.value[self.VALUE_KEY],
            },
            {
                NODE_ID_KEY: self.child_node_2.node_id,
                TILE_ID_KEY: self.child_node_2.tile_id,
                self.VALUE_KEY: self.child_node_2.value[self.VALUE_KEY],
            },
            {
                NODE_ID_KEY: self.child_node_3.node_id,
                TILE_ID_KEY: self.child_node_3.tile_id,
                self.VALUE_KEY: self.child_node_3.value[self.VALUE_KEY],
            },
        ]

        self.assertEqual(self.test_node.as_json(), {self.test_node.name: self.test_node_json_data})


class LabelBasedGraphTests(TestCase):
    @classmethod
    def setUp(cls):
        cls.node_1 = LabelBasedNode(name="node_1_val", node_id="node_1_node_id", tile_id="node_1_tile_id", value="node_1_value")
        cls.node_2 = LabelBasedNode(name="node_2_val", node_id="node_2_node_id", tile_id="node_2_tile_id", value=None)

    @mock.patch("arches.app.utils.label_based_graph.models.NodeGroup")
    def test_generate_node_ids_to_tiles_reference_and_nodegroup_cardinality_reference(self, mock_NodeGroup):
        mock_tile = mock.Mock(data={self.node_1.node_id: "test_val"}, nodegroup_id=self.node_1.node_id)
        mock_cardinality = "1"

        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": mock_tile.nodegroup_id, "cardinality": mock_cardinality}
        ]

        (
            node_ids_to_tiles_reference,
            nodegroup_cardinality_reference,
        ) = LabelBasedGraph.generate_node_ids_to_tiles_reference_and_nodegroup_cardinality_reference(resource=mock.Mock(tiles=[mock_tile]))

        self.assertEqual(mock_tile, node_ids_to_tiles_reference.get(self.node_1.node_id)[0])
        self.assertEqual(nodegroup_cardinality_reference, {mock_tile.nodegroup_id: mock_cardinality})

    @mock.patch.object(LabelBasedGraph, "_build_graph", side_effect=None)
    def test_from_tile(self, mock__build_graph):
        with mock.patch("arches.app.utils.label_based_graph.models.Node", return_value=None):
            LabelBasedGraph.from_tile(tile=mock.Mock(nodegroup_id=1), node_ids_to_tiles_reference=mock.Mock())
            mock__build_graph.assert_called_once()


@mock.patch("arches.app.utils.label_based_graph.models.NodeGroup")
@mock.patch("arches.app.utils.label_based_graph.models.Node")
class LabelBasedGraph_FromResourceTests(TestCase):
    @classmethod
    def setUp(cls):
        cls.VALUE_KEY = "@display_value"

        cls.RESOURCE_KEY = "resource"
        cls.DISPLAY_DESCRIPTION_KEY = "displaydescription"
        cls.DISPLAY_NAME_KEY = "displayname"
        cls.GRAPH_ID_KEY = "graph_id"
        cls.LEGACY_ID_KEY = "legacyid"
        cls.MAP_POPUP_KEY = "map_popup"
        cls.RESOURCE_INSTANCE_ID_KEY = "resourceinstanceid"

        cls.parent_nodegroup = models.NodeGroup()
        cls.nodegroup = models.NodeGroup(parentnodegroup=cls.parent_nodegroup)
        cls.grouping_node = models.Node(datatype="semantic", name="Test Node Grouping", nodegroup=cls.nodegroup)
        cls.string_node = models.Node(datatype="string", name="Test Node", nodegroup=cls.nodegroup)
        cls.grouping_tile = models.TileModel(data={}, nodegroup_id=str(cls.grouping_node.pk))
        cls.string_tile = models.TileModel(data={str(cls.string_node.pk): "value_1"}, nodegroup_id=str(cls.string_node.pk))

        cls.grouping_node.nodegroupid = cls.grouping_node.nodeid
        cls.string_node.nodegroupid = cls.string_node.nodeid

        # let's mock Resource since it's minimally used
        # and complex to get `displayname`
        cls.test_resource = mock.Mock(displayname="Test Resource", tiles=[])

    def test_smoke(self, mock_Node, mock_NodeGroup):
        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
                self.RESOURCE_KEY: {},
            },
        )

    def test_handles_node_with_single_value(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.return_value = self.string_node
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.string_tile.nodegroup_id, "cardinality": "1"}
        ]

        self.test_resource.tiles.append(self.string_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.string_node.name: {
                        NODE_ID_KEY: str(self.string_node.pk),
                        TILE_ID_KEY: str(self.string_tile.pk),
                        self.VALUE_KEY: self.string_tile.data[str(self.string_node.pk)],
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_handles_node_with_multiple_values(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.return_value = self.string_node
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.string_tile.nodegroup_id, "cardinality": "1"}
        ]

        duplicate_node_tile = models.TileModel(data={str(self.string_node.pk): "value_2"}, nodegroup_id=str(self.string_node.pk))

        self.test_resource.tiles.append(self.string_tile)
        self.test_resource.tiles.append(duplicate_node_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.string_node.name: [
                        {
                            NODE_ID_KEY: str(self.string_node.pk),
                            TILE_ID_KEY: str(self.string_tile.pk),
                            self.VALUE_KEY: self.string_tile.data[str(self.string_node.pk)],
                        },
                        {
                            NODE_ID_KEY: str(self.string_node.pk),
                            TILE_ID_KEY: str(duplicate_node_tile.pk),
                            self.VALUE_KEY: duplicate_node_tile.data[str(self.string_node.pk)],
                        },
                    ],
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_handles_empty_semantic_node(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.return_value = self.grouping_node
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.grouping_tile.nodegroup_id, "cardinality": "1"}
        ]

        self.test_resource.tiles.append(self.grouping_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.grouping_node.name: {
                        NODE_ID_KEY: str(self.grouping_node.pk),
                        TILE_ID_KEY: str(self.grouping_tile.pk),
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_semantic_node_with_child(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.return_value = self.grouping_node
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.grouping_tile.nodegroup_id, "cardinality": "1"}
        ]

        self.grouping_node.get_direct_child_nodes = mock.Mock(return_value=[self.string_node])

        self.grouping_tile.data = {str(self.string_node.pk): "value_2"}
        self.test_resource.tiles.append(self.grouping_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.grouping_node.name: {
                        NODE_ID_KEY: str(self.grouping_node.pk),
                        TILE_ID_KEY: str(self.grouping_tile.pk),
                        self.string_node.name: {
                            NODE_ID_KEY: str(self.string_node.pk),
                            TILE_ID_KEY: str(self.grouping_tile.pk),
                            self.VALUE_KEY: self.grouping_tile.data[str(self.string_node.pk)],
                        },
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_handles_node_grouped_in_separate_card(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.side_effect = [self.grouping_node, self.string_node]
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.grouping_tile.nodegroup_id, "cardinality": "1"},
            {"nodegroupid": self.string_tile.nodegroup_id, "cardinality": "1"},
        ]

        self.grouping_node.get_direct_child_nodes = mock.Mock(return_value=[self.string_node])

        self.string_tile.parenttile = self.grouping_tile

        self.test_resource.tiles.append(self.grouping_tile)
        self.test_resource.tiles.append(self.string_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.grouping_node.name: {
                        NODE_ID_KEY: str(self.grouping_node.pk),
                        TILE_ID_KEY: str(self.grouping_tile.pk),
                        self.string_node.name: {
                            NODE_ID_KEY: str(self.string_node.pk),
                            TILE_ID_KEY: str(self.string_tile.pk),
                            self.VALUE_KEY: self.string_tile.data[str(self.string_node.pk)],
                        },
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_handles_node_grouped_in_separate_card_with_cardinality_n(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.side_effect = [self.grouping_node, self.string_node]
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.grouping_tile.nodegroup_id, "cardinality": "1"},
            {"nodegroupid": self.string_tile.nodegroup_id, "cardinality": "n"},
        ]

        self.grouping_node.get_direct_child_nodes = mock.Mock(return_value=[self.string_node])

        self.string_tile.parenttile = self.grouping_tile

        self.test_resource.tiles.append(self.grouping_tile)
        self.test_resource.tiles.append(self.string_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.grouping_node.name: {
                        NODE_ID_KEY: str(self.grouping_node.pk),
                        TILE_ID_KEY: str(self.grouping_tile.pk),
                        self.string_node.name: [
                            {
                                NODE_ID_KEY: str(self.string_node.pk),
                                TILE_ID_KEY: str(self.string_tile.pk),
                                self.VALUE_KEY: self.string_tile.data[str(self.string_node.pk)],
                            }
                        ],
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )

    def test_handles_empty_node_grouped_in_separate_card_with_cardinality_n(self, mock_Node, mock_NodeGroup):
        mock_Node.objects.get.side_effect = [self.grouping_node, self.string_node]
        mock_NodeGroup.objects.filter.return_value.values.return_value = [
            {"nodegroupid": self.grouping_tile.nodegroup_id, "cardinality": "1"},
            {"nodegroupid": self.string_tile.nodegroup_id, "cardinality": "n"},
        ]

        self.grouping_node.get_direct_child_nodes = mock.Mock(return_value=[self.string_node])

        self.string_tile.parenttile = self.grouping_tile

        self.test_resource.tiles.append(self.grouping_tile)

        label_based_graph = LabelBasedGraph.from_resource(resource=self.test_resource, compact=False, hide_empty_nodes=False)

        self.assertEqual(
            label_based_graph,
            {
                self.RESOURCE_KEY: {
                    self.grouping_node.name: {
                        NODE_ID_KEY: str(self.grouping_node.pk),
                        TILE_ID_KEY: str(self.grouping_tile.pk),
                    },
                },
                self.DISPLAY_DESCRIPTION_KEY: mock.ANY,
                self.DISPLAY_NAME_KEY: mock.ANY,
                self.GRAPH_ID_KEY: mock.ANY,
                self.LEGACY_ID_KEY: mock.ANY,
                self.MAP_POPUP_KEY: mock.ANY,
                self.RESOURCE_INSTANCE_ID_KEY: mock.ANY,
            },
        )
