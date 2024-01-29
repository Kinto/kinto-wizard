try:
    from jsonschema import Draft7Validator as SchemaValidator
except ImportError:  # pragma: no cover
    from jsonschema import Draft4Validator as SchemaValidator
from jsonschema import SchemaError, ValidationError, validate

from .logger import logger


IGNORED_FIELDS = (
    "id",
    "last_modified",
    "schema",
    "attachment",
)


def check_schema(data):
    try:
        SchemaValidator.check_schema(data)
    except SchemaError as e:
        message = e.path.pop() + e.message
        raise ValidationError(message)


def validate_schema(data, schema, ignore_fields=[]):
    required_fields = [f for f in schema.get("required", []) if f not in ignore_fields]
    # jsonschema doesn't accept 'required': [] yet.
    # See https://github.com/Julian/jsonschema/issues/337.
    # In the meantime, strip out 'required' if no other fields are required.
    if required_fields:
        schema = {**schema, "required": required_fields}
    else:
        schema = {f: v for f, v in schema.items() if f != "required"}

    data = {f: v for f, v in data.items() if f not in ignore_fields}

    try:
        validate(data, schema)
    except ValidationError as e:  # pragma: no cover
        if e.path:
            field = e.path[-1]
        elif e.validator_value:
            field = e.validator_value[-1]
        else:
            field = e.schema_path[-1]
        e.field = field
        raise e


def validate_export(config):
    everything_is_fine = True
    if "buckets" in config:
        buckets = config.get("buckets", {})
    else:  # pragma: no cover
        # Legacy for file before kinto-wizard 4.0
        logger.warning(
            "Your file seems to be in legacy format. " "Please add a `buckets:` root level."
        )
        buckets = config
    for bid, bucket in buckets.items():
        logger.info(f"- Bucket {bid}")
        bucket_collections = bucket.get("collections", {})
        for cid, collection in bucket_collections.items():
            logger.info(f"  - Collection {cid}")
            collection_data = collection.get("data", {})
            if "schema" not in collection_data:
                logger.info("    No schema\n")
                continue

            schema = collection_data["schema"]
            try:
                check_schema(schema)
            except ValidationError:
                logger.exception(f"Collection {cid!r} validation failed.")
                everything_is_fine = False
                continue

            collection_records = collection.get("records", {})

            for record_id, record in collection_records.items():
                try:
                    validate_schema(record["data"], schema, ignore_fields=IGNORED_FIELDS)
                except ValidationError:
                    logger.exception(f"Record {record_id!r} validation failed.")
                    everything_is_fine = False
    return everything_is_fine
