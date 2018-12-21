import warlock
import jsonschema
from typing import Any, List, Tuple
from uuid import UUID

UUID_SCHEMA = {
    "description": "UUID",
    "type": "string",
    "minLength": 36,
    "maxLength": 36,
    "pattern": "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$"
}

itsim_object_types = [
    "node",
    "link",
    "log",
    "network_event"
]

log_levels = [
    "DEBUG",
    "CRITICAL",
    "INFO",
    "WARNING",
    "ERROR"
]

ITSIM_OBJECT_TYPE_SCHEMA = {
    "description": "Itsim object types",
    "enum": itsim_object_types
}


TAGS_SCHEMA = {
    "description": "Tags passed from a computation to telemetry",
    "type": "array",
    "items": {"type": "string"}
}


NODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema#",
    "description": "A node object",
    "type": "object",
    "properties": {
        "sim_uuid": UUID_SCHEMA,
        "timestamp": {
            "description": "timestamp when last updated",
            "type": "string"
        },
        "type": ITSIM_OBJECT_TYPE_SCHEMA,
        "uuid": UUID_SCHEMA,
        "node_label": {
            "description": "node label",
            "type": "string"
        },
    }
}


LOG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema#",
    "description": "A Log object",
    "type": "object",
    "properties": {
        "sim_uuid": UUID_SCHEMA,
        "timestamp": {
            "description": "log timestamp",
            "type": "string"
        },
        "type": ITSIM_OBJECT_TYPE_SCHEMA,
        "uuid": UUID_SCHEMA,
        "content": {
            "description": "log content",
            "type": "string"
        },
        "level": {
            "description": "Log Lvel",
            "enum": log_levels
        }
    }
}


network_event_types = [
    "open",
    "close",
    "send",
    "recv"
]

NETWORK_EVENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema#",
    "description": "A network event object",
    "type": "object",
    "properties": {
        "sim_uuid": UUID_SCHEMA,
        "timestamp": {
            "description": "timestamp when last updated",
            "type": "string"
        },
        "type": ITSIM_OBJECT_TYPE_SCHEMA,
        "uuid": UUID_SCHEMA,
        "tags": TAGS_SCHEMA,
        "uuid_node": UUID_SCHEMA,
        "network_event_type": {
            "description": "Network event type",
            "enum": network_event_types
        },
        "pid": {
            "description": "PID",
            "type": "number"
        },
        "protocol": {
            "description": "Protocol",
            "enum": ["TCP", "UDP", "NONE"]
        },
        "src": {
            "type": "array",
            "items": [
                {
                    "type": "string"
                },
                {
                    "type": "number"
                }
            ]
        },
        "dst": {
            "type": "array",
            "items": [
                {
                    "type": "string"
                },
                {
                    "type": "number"
                }
            ]
        }
    }
}


def get_itsim_object_types() -> List[str]:
    return itsim_object_types


def check_validity(data: Any, schema: Any) -> None:
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print("Invalid input query. JSON schema error: {}".format(e.message))
        assert False


def create_json_node(sim_uuid: UUID, timestamp: str, uuid: UUID, node_label: str) -> Any:
    creator = warlock.model_factory(NODE_SCHEMA)
    json_item = creator(sim_uuid=str(sim_uuid),
                        timestamp=timestamp,
                        type='node',
                        uuid=str(uuid),
                        node_label=node_label)
    check_validity(json_item, NODE_SCHEMA)
    return json_item


def create_json_log(sim_uuid: UUID, timestamp: str, uuid: UUID, content: str, level: int) -> Any:
    creator = warlock.model_factory(LOG_SCHEMA)
    json_item = creator(sim_uuid=str(sim_uuid),
                        timestamp=timestamp,
                        type='log',
                        uuid=str(uuid),
                        content=content,
                        level=level)
    check_validity(json_item, LOG_SCHEMA)
    return json_item


def create_json_network_event(sim_uuid: UUID,
                              timestamp: str,
                              uuid: UUID,
                              tags: List[str],
                              uuid_node: UUID,
                              network_event_type: str,
                              protocol: str,
                              pid: int,
                              src: Tuple[str, int],
                              dst: Tuple[str, int]) -> Any:

    creator = warlock.model_factory(NETWORK_EVENT_SCHEMA)
    json_item = creator(sim_uuid=str(sim_uuid), timestamp=timestamp, type="network_event",
                        uuid=str(uuid),
                        tags=list(tags),
                        uuid_node=str(uuid_node),
                        network_event_type=network_event_type,
                        protocol=protocol,
                        pid=pid,
                        src=list(src),
                        dst=list(dst))
    check_validity(json_item, NETWORK_EVENT_SCHEMA)
    return json_item
