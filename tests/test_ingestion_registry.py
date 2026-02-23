from agentic_maas.ingestion import IngestionRegistry, ModbusAdapter, MqttAdapter, OpcUaAdapter


def test_ingestion_registry_and_discovery() -> None:
    registry = IngestionRegistry()
    registry.register(OpcUaAdapter())
    registry.register(ModbusAdapter())
    registry.register(MqttAdapter())

    assert registry.protocols() == ["modbus", "mqtt", "opcua"]

    points = registry.get("opcua").discover_points("opc.tcp://localhost:4840", {"mock_points": "A,B"})
    assert len(points) == 2
    assert points[0].protocol.value == "opcua"
