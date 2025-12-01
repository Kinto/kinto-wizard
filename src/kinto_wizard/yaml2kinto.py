from __future__ import print_function

import copy
import json
import os

from .kinto2yaml import introspect_server, sorted_principals
from .logger import logger


def data_changed(existing_data, new_data):
    """
    Let's apply the PATCH and compare if data remains
    the same.
    """
    patched_data = copy.deepcopy(existing_data)
    patched_data.update(new_data)
    return patched_data != existing_data


def perms_changed(existing_perms, new_perms, user_id):
    """
    Let's apply the permissions changes and compare if permissions
    remain the same.
    """
    patched_perms = copy.deepcopy(existing_perms)
    patched_perms.update(new_perms)
    # Kinto adds the user automatically.
    patched_perms.setdefault("write", []).append(user_id)
    # Kinto does not return empty lists, and uniquifies entries.
    stripped_patched_perms = {k: set(v) for k, v in patched_perms.items() if v}
    stripped_existing_perms = {k: set(v) for k, v in existing_perms.items() if v}
    return stripped_patched_perms != stripped_existing_perms


async def initialize_server(
    async_client,
    config,
    bucket=None,
    collection=None,
    force=False,
    delete_missing_records=False,
    attachments=None,
    load_buckets=True,
    load_collections=True,
    load_records=True,
    load_groups=True,
    load_data=True,
    load_permissions=True,
):
    logger.debug("Converting YAML config into a server batch.")
    bid = bucket
    cid = collection
    # 1. Introspect current server state.
    if not force or delete_missing_records:
        current_server_status = await introspect_server(
            async_client, bucket=bucket, collection=collection, data=True, records=True
        )
        existing_server_buckets = current_server_status["buckets"]
    else:
        # We don't need to load it because we will override it nevertheless.
        existing_server_buckets = {}

    # Find out user_id to compare permissions later.
    user_info = await async_client.server_info()
    # If no user info, Kinto will assign permissions to `system.Everyone`.
    user_id = user_info.get("user", {"id": "system.Everyone"}).get("id")

    # 2. For each bucket
    buckets = config["buckets"]
    with await async_client.batch() as batch:
        for bucket_id, bucket in buckets.items():
            # Skip buckets that we don't want to import.
            if bid and bucket_id != bid:
                logger.debug("Skip bucket {}".format(bucket_id))
                continue
            bucket_exists = bucket_id in existing_server_buckets
            bucket_data = bucket.get("data", {}) if load_data else {}
            bucket_permissions = (
                sorted_principals(bucket.get("permissions", {})) if load_permissions else {}
            )
            bucket_groups = bucket.get("groups", {}) if load_groups else {}
            bucket_collections = bucket.get("collections", {}) if load_collections else {}

            # Skip bucket if we don't have a collection in them
            if cid and cid not in bucket_collections:
                logger.debug("Skip bucket {}".format(bucket_id))
                continue

            if load_buckets:
                if not bucket_exists:
                    existing_bucket_groups = {}
                    existing_bucket_collections = {}

                    # Create the bucket if not present in the introspection
                    await batch.create_bucket(
                        id=bucket_id,
                        data=bucket_data if load_data else None,
                        permissions=bucket_permissions if load_permissions else None,
                        safe=(not force),
                    )
                else:
                    existing_bucket = existing_server_buckets[bucket_id]
                    existing_bucket_groups = {}
                    existing_bucket_collections = {}
                    existing_bucket_data = {}
                    existing_bucket_permissions = {}

                    if existing_bucket:
                        existing_bucket_groups = existing_bucket.get("groups", {})
                        existing_bucket_collections = existing_bucket.get("collections", {})

                        # Patch the bucket if mandatory
                        existing_bucket_data = existing_bucket.get("data", {})
                        existing_bucket_permissions = existing_bucket.get("permissions", {})

                    if data_changed(existing_bucket_data, bucket_data) or perms_changed(
                        existing_bucket_permissions, bucket_permissions, user_id
                    ):
                        await batch.patch_bucket(
                            id=bucket_id,
                            data=bucket_data if load_data else None,
                            permissions=bucket_permissions if load_permissions else None,
                        )

            # 2.1 For each group, patch it if needed
            if load_groups:
                for group_id, group_info in bucket_groups.items():
                    group_exists = bucket_exists and group_id in existing_bucket_groups
                    group_data = group_info.get("data", {}) if load_data else {}
                    group_permissions = (
                        sorted_principals(group_info.get("permissions", {}))
                        if load_permissions
                        else {}
                    )

                    if not group_exists:
                        await batch.create_group(
                            id=group_id,
                            bucket=bucket_id,
                            data=group_data if load_data else None,
                            permissions=group_permissions if load_permissions else None,
                            safe=(not force),
                        )
                    else:
                        existing_group = existing_bucket_groups[group_id]
                        existing_group_data = existing_group.get("data", {})
                        existing_group_permissions = existing_group.get("permissions", {})

                        if data_changed(existing_group_data, group_data) or perms_changed(
                            existing_group_permissions, group_permissions, user_id
                        ):
                            await batch.patch_group(
                                id=group_id,
                                bucket=bucket_id,
                                data=group_data if load_data else None,
                                permissions=group_permissions if load_permissions else None,
                            )

            # 2.2 For each collection patch it if mandatory
            if load_collections:
                for collection_id, collection in bucket_collections.items():
                    # Skip collections that we don't want to import.
                    if cid and collection_id != cid:
                        logger.debug("Skip collection {}/{}".format(bucket_id, collection_id))
                        continue
                    collection_exists = (
                        bucket_exists and collection_id in existing_bucket_collections
                    )
                    collection_data = collection.get("data", {})
                    collection_permissions = sorted_principals(collection.get("permissions", {}))

                    if not collection_exists:
                        await batch.create_collection(
                            id=collection_id,
                            bucket=bucket_id,
                            data=collection_data if load_data else None,
                            permissions=collection_permissions if load_permissions else None,
                            safe=(not force),
                        )
                    else:
                        existing_collection = existing_bucket_collections[collection_id]
                        existing_collection_data = existing_collection.get("data", {})
                        existing_collection_permissions = existing_collection.get(
                            "permissions", {}
                        )

                        if data_changed(
                            existing_collection_data, collection_data
                        ) or perms_changed(
                            existing_collection_permissions, collection_permissions, user_id
                        ):
                            await batch.patch_collection(
                                id=collection_id,
                                bucket=bucket_id,
                                data=collection_data if load_data else None,
                                permissions=collection_permissions if load_permissions else None,
                            )
        logger.debug("Sending batch:\n\n%s" % batch.session.requests)
    logger.info("Buckets, groups, and collections uploaded")

    if not load_records:
        # We're done here.
        return

    with await async_client.batch() as batch:
        for bucket_id, bucket in buckets.items():
            if bid and bucket_id != bid:
                continue

            bucket_collections = bucket.get("collections", {})
            existing_bucket = existing_server_buckets.get(bucket_id, {})
            existing_bucket_collections = existing_bucket.get("collections", {})

            for collection_id, collection in bucket_collections.items():
                if cid and collection_id != cid:
                    continue

                existing_collection = existing_bucket_collections.get(collection_id)
                existing_records = (
                    existing_collection.get("records", {}) if existing_collection else {}
                )
                collection_exists = existing_collection is not None

                # For each collection, create its records.
                collection_records = collection.get("records", {})
                for record_id, record in collection_records.items():
                    record_exists = collection_exists and record_id in existing_records
                    record_data = record.get("data", {})
                    record_permissions = sorted_principals(record.get("permissions", None))

                    # If 'attachment' field is present on record, then we look whether we have
                    # to upload it from the local folder `attachments`.
                    # If the collection has a JSON schema where the attachment field is mandatory,
                    # creation will fail.
                    # But if the attachment is not present, we warn and try anyway.
                    must_upload_attachment = False
                    if attachments is not None and "attachment" in record_data:
                        location = record_data["attachment"]["location"]
                        attachment_path = os.path.join(attachments, location)

                        if not os.path.exists(attachment_path):
                            # No local file, we simply ignore the 'attachment' field
                            # and will proceed with the upsert below.
                            record_data.pop("attachment")
                            if not record_exists:
                                # For creations, warn because it may fail because of mandatory field in JSON schema.
                                logger.warning(
                                    "Attachment for %s/%s/%s not found: %s",
                                    bucket_id,
                                    collection_id,
                                    record_id,
                                    attachment_path,
                                )
                        else:
                            # Attachment exists on disk.
                            must_upload_attachment = True
                            if record_exists:
                                existing_record = existing_records[record_id]
                                # We compare the attachment metadata and only upload if necessary.
                                existing_metadata = existing_record.get("attachment")
                                must_upload_attachment = (
                                    existing_metadata is None
                                    or existing_metadata["size"]
                                    != record_data["attachment"]["size"]
                                    or existing_metadata["hash"]
                                    != record_data["attachment"]["hash"]
                                )
                            if must_upload_attachment:
                                # If there is a .meta.json file, then read it to get original filename.
                                try:
                                    with open(f"{attachment_path}.meta.json", "rb") as f:
                                        metadata = json.load(f)
                                        filename = metadata["attachment"]["filename"]
                                except (FileNotFoundError, json.JSONDecodeError) as e:
                                    logger.error("Failed to read attachment metadata: %s", e)
                                    filename = None

                                # We upload the new attachment, and update its attributes together.
                                await async_client.add_attachment(
                                    id=record_id,
                                    bucket=bucket_id,
                                    collection=collection_id,
                                    data=record_data if load_data else None,
                                    permissions=record_permissions if load_permissions else None,
                                    filepath=attachment_path,
                                    filename=filename,
                                )

                    if not must_upload_attachment:
                        if not record_exists:
                            await batch.create_record(
                                id=record_id,
                                bucket=bucket_id,
                                collection=collection_id,
                                data=record_data if load_data else None,
                                permissions=record_permissions if load_permissions else None,
                                safe=(not force),
                            )
                        else:
                            existing_record = existing_records[record_id]
                            existing_record_data = existing_record.get("data", {})
                            existing_record_permissions = existing_record.get("permissions", {})
                            if data_changed(existing_record_data, record_data) or perms_changed(
                                existing_record_permissions, record_permissions, user_id
                            ):
                                await batch.update_record(
                                    id=record_id,
                                    bucket=bucket_id,
                                    collection=collection_id,
                                    data=record_data if load_data else None,
                                    permissions=record_permissions if load_permissions else None,
                                )

                if delete_missing_records and collection_exists and collection_records:
                    # Fetch all records IDs
                    file_records_ids = set(collection_records.keys())
                    server_records_ids = set(existing_collection["records"].keys())

                    to_delete = server_records_ids - file_records_ids
                    if not force:
                        message = (
                            "Are you sure that you want to delete the "
                            "following {} records?".format(len(list(to_delete)))
                        )
                        value = input(message)
                        if value.lower() not in ["y", "yes"]:
                            print("Exiting")
                            exit(1)
                    for record_id in to_delete:
                        await batch.delete_record(
                            id=record_id, bucket=bucket_id, collection=collection_id
                        )

        logger.debug("Sending batch:\n\n%s" % batch.session.requests)
    logger.info("Records uploaded")
