"""Test graph input guards without running the batch export entry point."""

import importlib
import math
import unittest

import pandas as pd


builder = importlib.import_module("scripts.02_graph_builder")


def original_distance(src, dst):
    """Original Haversine arithmetic, retained as a compatibility reference."""
    lat1, lon1 = map(math.radians, src)
    lat2, lon2 = map(math.radians, dst)
    value = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371 * math.asin(math.sqrt(max(0, min(1, value))))


class HaversineValidationTests(unittest.TestCase):
    def test_invalid_coordinate_fields_at_either_endpoint(self):
        for field, position, values in (
            ("lat", 0, (math.nan, None, math.inf, -math.inf, 90.01, -90.01)),
            ("lon", 1, (math.nan, None, math.inf, -math.inf, 180.01, -180.01)),
        ):
            for airport in ("A", "B"):
                for value in values:
                    with self.subTest(field=field, airport=airport, value=value):
                        point = [0.0, 0.0]
                        point[position] = value
                        coords = {"A": (0, 0), "B": (0, 0), airport: point}
                        with self.assertRaisesRegex(ValueError, f"{airport}.*{field}="):
                            builder.haversine_distance("A", "B", coords)

    def test_missing_coordinate_entry(self):
        for coords in ({"A": (0, 0)}, {"B": (0, 0)}):
            with self.subTest(coords=coords):
                with self.assertRaisesRegex(ValueError, "缺少 lat/lon"):
                    builder.haversine_distance("A", "B", coords)

    def test_valid_coordinates_match_original_exactly(self):
        for src, dst in (
            ((0, 0), (0, 0)),
            ((90, -180), (-90, 180)),
            ((10, 179.9), (10, -179.9)),
            ((9.0038, 96.8732), (32.3057, 114.2951)),
        ):
            with self.subTest(src=src, dst=dst):
                self.assertEqual(
                    builder.haversine_distance("A", "B", {"A": src, "B": dst}),
                    original_distance(src, dst),
                )


class GraphValidationTests(unittest.TestCase):
    def setUp(self):
        self.airports = pd.DataFrame([
            {"airport_id": "A", "active": 1, "lat": 0.0, "lon": 0.0},
            {"airport_id": "B", "active": 1, "lat": 0.0, "lon": 0.0},
            {"airport_id": "C", "active": 0, "lat": 0.0, "lon": 0.0},
        ])
        self.routes = pd.DataFrame([{
            "src": "A", "dst": "B", "airline": "CA", "duration_min": 20.0,
            "distance_km": 10.0, "stops": 0, "codeshare": 0,
        }])
        self.ground = pd.DataFrame([{
            "src": "A", "dst": "B", "mode": "bus", "duration_min": 30.0, "stops": 0,
        }])

    def test_duplicate_or_empty_airport_id(self):
        for value in ("A", None, " "):
            with self.subTest(value=value):
                airports = self.airports.copy()
                airports.at[1, "airport_id"] = value
                with self.assertRaisesRegex(ValueError, "airport_id"):
                    builder.build_graph(airports, self.routes, self.ground)

    def test_invalid_endpoints_report_edge_type_and_field(self):
        for side in ("src", "dst"):
            for airport_id in ("UNKNOWN", "C"):
                with self.subTest(side=side, airport_id=airport_id):
                    with self.assertRaisesRegex(ValueError, f"地面边.*{side}='{airport_id}'"):
                        builder.build_graph(self.airports, self.routes,
                                            self.ground.assign(**{side: airport_id}))
                    with self.assertRaisesRegex(ValueError, f"航空边.*{side}='{airport_id}'"):
                        builder.build_graph(self.airports,
                                            self.routes.assign(**{side: airport_id}), self.ground)

    def test_invalid_ground_coordinate_reports_edge_and_airport(self):
        self.airports.at[1, "lon"] = math.nan
        with self.assertRaisesRegex(ValueError, "地面边.*机场 'B'.*lon="):
            builder.build_graph(self.airports, self.routes, self.ground)

    def test_invalid_weights(self):
        for value in (math.nan, math.inf, -math.inf, -1.0, 0.0):
            for field in ("duration_min", "distance_km"):
                with self.subTest(value=value, field=field):
                    with self.assertRaisesRegex(ValueError, f"航空边.*{field}="):
                        builder.build_graph(self.airports, self.routes.assign(**{field: value}),
                                            self.ground)
            with self.subTest(value=value, field="ground duration_min"):
                with self.assertRaisesRegex(ValueError, "地面边.*duration_min="):
                    builder.build_graph(self.airports, self.routes,
                                        self.ground.assign(duration_min=value))

    def test_valid_parallel_edges_keep_order_and_zero_ground_distance(self):
        routes = pd.concat([self.routes, self.routes.assign(airline="MU")], ignore_index=True)
        graph = builder.build_graph(self.airports, routes, self.ground)
        self.assertEqual([edge["airline"] for edge in graph["A"]], ["CA", "MU", None])
        self.assertEqual(graph["A"][2]["distance_km"], 0.0)
        self.assertEqual(graph["B"], [])

    def test_invalid_od_records_are_reported_together(self):
        graph = builder.build_graph(self.airports, self.routes, self.ground)
        invalid = pd.DataFrame([
            {"pair_id": 1, "src": "A", "dst": "UNKNOWN"},
            {"pair_id": 1, "src": "", "dst": "B"},
            {"pair_id": 2, "src": "A", "dst": None},
        ])
        with self.assertRaises(ValueError) as caught:
            builder.validate_od(invalid, graph)
        for detail in ("pair_id 重复", "dst='UNKNOWN'", "src=''", "dst=None", "pair_id=2"):
            self.assertIn(detail, str(caught.exception))
        builder.validate_od(pd.DataFrame([{"pair_id": 1, "src": "A", "dst": "B"}]), graph)


if __name__ == "__main__":
    unittest.main()
