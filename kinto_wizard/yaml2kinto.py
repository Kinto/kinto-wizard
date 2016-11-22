from __future__ import print_function
from .logger import logger
from .kinto2yaml import introspect_server


def initialize_server(client, config):
    logger.debug("Converting YAML config into a server batch.")
    # 1. Introspect current server state.
    current_server_status = introspect_server(client)
    # 2. For each bucket
    with client.batch() as batch:
        for bucket_id, bucket in config.items():
            bucket_exists = bucket_id in current_server_status
            bucket_data = bucket.get('data', {})
            bucket_permissions = bucket.get('permissions', {})
            bucket_groups = bucket.get('groups', {})
            bucket_collections = bucket.get('collections', {})

            if not bucket_exists:
                bucket_current_groups = {}
                bucket_current_collections = {}

                # Create the bucket if not present in the introspection
                batch.create_bucket(bucket=bucket_id,
                                    data=bucket_data,
                                    permissions=bucket_permissions)
            else:
                bucket_current_groups = current_server_status[bucket_id]['groups']
                bucket_current_collections = current_server_status[bucket_id]['collections']

                # Patch the bucket if mandatory
                current_bucket = current_server_status[bucket_id]
                current_bucket_data = current_bucket.get('data', {})
                current_bucket_permissions = current_bucket.get('permissions', {})

                if (current_bucket_data != bucket_data or
                        current_bucket_permissions != bucket_permissions):
                    batch.patch_bucket(bucket=bucket_id,
                                       data=bucket_data,
                                       permissions=bucket_permissions)

            # 1.1 For each group, patch it if needed
            for group_id, group_info in bucket_groups.items():
                group_exists = bucket_exists and group_id in bucket_current_groups
                group_data = group_info.get('data', {})
                group_permissions = group_info.get('permissions', {})

                if not group_exists:
                    batch.create_group(group=group_id,
                                       bucket=bucket_id,
                                       data=group_data,
                                       permissions=group_permissions)
                else:
                    current_group = bucket_current_groups[group_id]
                    current_group_data = current_group.get('data', {})
                    current_group_permissions = current_group.get('permissions', {})

                    if (current_group_data != group_data or
                            current_group_permissions != group_permissions):
                        batch.patch_group(group=group_id,
                                          bucket=bucket_id,
                                          data=group_data,
                                          permissions=group_permissions)

            # 1.2 For each collection patch it if mandatory
            for collection_id, collection_info in bucket_collections.items():
                collection_exists = bucket_exists and collection_id in bucket_current_collections
                collection_data = collection_info.get('data', {})
                collection_permissions = collection_info.get('permissions', {})

                if not collection_exists:
                    batch.create_collection(collection=collection_id,
                                            bucket=bucket_id,
                                            data=collection_data,
                                            permissions=collection_permissions)
                else:
                    current_collection = bucket_current_collections[collection_id]
                    current_collection_data = current_collection.get('data', {})
                    current_collection_permissions = current_collection.get('permissions', {})

                    if (current_collection_data != collection_data or
                            current_collection_permissions != collection_permissions):
                        batch.patch_collection(collection=collection_id,
                                               bucket=bucket_id,
                                               data=collection_data,
                                               permissions=collection_permissions)
        logger.debug('Sending batch:\n\n%s' % batch.session.requests)
    logger.info("Batch uploaded")
