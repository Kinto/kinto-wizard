from kinto_http import exceptions as kinto_exceptions
from .logger import logger


def _sorted_principals(permissions):
    return {perm: sorted(principals) for perm, principals in permissions.items()}


def introspect_server(client, bucket=None, collection=None, data=False, records=False):
    if bucket:
        logger.info("Only inspect bucket `{}`.".format(bucket))
        bucket_info = introspect_bucket(client, bucket, collection=collection,
                                        data=data, records=records)
        if bucket_info:
            return {bucket: bucket_info}
        return {}

    logger.info("Fetch buckets list.")
    buckets = client.get_buckets()
    return {
        bucket['id']: introspect_bucket(client, bucket['id'], collection=collection,
                                        data=data, records=records)
        for bucket in buckets
    }


def introspect_bucket(client, bid, collection=None, data=False, records=False):
    logger.info("Fetch information of bucket {!r}".format(bid))
    try:
        bucket = client.get_bucket(id=bid)
    except kinto_exceptions.BucketNotFound:
        logger.error("Could not read bucket {!r}".format(bid))
        return None

    permissions = bucket.get('permissions', {})
    if len(permissions) == 0:
        logger.warn('Could not read permissions of bucket {!r}'.format(bid))

    if collection:
        result = {
            'permissions': _sorted_principals(permissions),
            'collections': {collection: introspect_collection(client, bid, collection,
                                                              data=data, records=records)}
        }
    else:
        collections = client.get_collections(bucket=bid)
        groups = client.get_groups(bucket=bid)
        result = {
            'permissions': _sorted_principals(permissions),
            'collections': {
                collection['id']: introspect_collection(client, bid, collection['id'],
                                                        data=data, records=records)
                for collection in collections
            },
            'groups': {
                group['id']: introspect_group(client, bid, group['id'], data=data)
                for group in groups
            }
        }
    if data:
        result['data'] = bucket['data']
    return result


def introspect_collection(client, bid, cid, data=False, records=False):
    logger.info("Fetch information of collection {!r}/{!r}".format(bid, cid))
    collection = client.get_collection(bucket=bid, id=cid)
    result = {
        'permissions': _sorted_principals(collection['permissions']),
    }
    if data:
        result['data'] = collection['data']

    if records:
        records = client.get_records(bucket=bid, collection=cid)
        result['records'] = {
            # XXX: we don't show permissions, until we have a way to fetch records
            # in batch (see Kinto/kinto-http.py#145)
            record['id']: {"data": record, "permissions": {}} for record in records
        }
    return result


def introspect_group(client, bid, gid, data=False):
    logger.info("Fetch information of group {!r}/{!r}".format(bid, gid))
    group = client.get_group(bucket=bid, id=gid)
    result = {
        'permissions': _sorted_principals(group['permissions'])
    }
    data = group['data'] if data else {}
    data['members'] = sorted(group['data']['members'])
    result['data'] = data
    return result
