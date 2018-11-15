import warlock
import jsonschema
from typing import Any, List

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
    "log"
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

NODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
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
    "$schema": "http://json-schema.org/draft-04/schema#",
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


def get_itsim_object_types() -> List[str]:
    return itsim_object_types


def check_validity(data: Any, schema: Any) -> bool:
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print("Invalid input query. JSON schema error: {}".format(e.message))
        assert False


def create_json_item(sim_uuid: str, timestamp: str, item_type: str = None, **kwargs) -> Any:
    # TODO: assert required kwargs for each type
    json_item = None

    if item_type.lower() == 'node':
        creator = warlock.model_factory(NODE_SCHEMA)
        json_item = creator(sim_uuid=sim_uuid, timestamp=timestamp, type=item_type.lower(),
                            uuid=kwargs['uuid'], node_label=kwargs['node_label'])
    elif item_type.lower() == 'log':
        creator = warlock.model_factory(LOG_SCHEMA)
        json_item = creator(sim_uuid=sim_uuid, timestamp=timestamp, type=item_type.lower(),
                            uuid=kwargs['uuid'], content=kwargs['content'], level=kwargs['level'])
    else:
        raise ValueError("Wrong item type")

    check_validity(json_item, LOG_SCHEMA)
    return json_item
