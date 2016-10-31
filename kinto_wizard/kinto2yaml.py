from kinto_http import exceptions as kinto_exceptions
from .logger import logger


def introspect_server(client):
    logger.info("Fetch buckets list.")
    buckets = client.get_buckets()
    return {
        bucket['id']: introspect_bucket(client, bucket['id'])
        for bucket in buckets
    }


def introspect_bucket(client, bid):
    logger.info("Fetch information of bucket {!r}".format(bid))
    try:
        bucket = client.get_bucket(bucket=bid)
    except kinto_exceptions.BucketNotFound:
        logger.error("Could not read bucket {!r}".format(bid))
        return None

    permissions = bucket.get('permissions', {})
    if 'write' not in permissions:
        error_msg = 'Could not read permissions of bucket {!r}'.format(bid)
        raise kinto_exceptions.KintoException(error_msg)

    collections = client.get_collections(bucket=bid)
    groups = client.get_groups(bucket=bid)
    return {
        'permissions': permissions,
        'collections': {
            collection['id']: introspect_collection(client, bid, collection['id'])
            for collection in collections
        },
        'groups': {
            group['id']: introspect_group(client, bid, group['id'])
            for group in groups
        }
    }


def introspect_collection(client, bid, cid):
    logger.info("Fetch information of collection {!r}/{!r}".format(bid, cid))
    collection = client.get_collection(bucket=bid, collection=cid)
    return {
        'permissions': collection['permissions'],
    }


def introspect_group(client, bid, gid):
    logger.info("Fetch information of group {!r}/{!r}".format(bid, gid))
    group = client.get_group(bucket=bid, group=gid)
    return {
        'data': {'members': group['data']['members']},
        'permissions': group['permissions']
    }
