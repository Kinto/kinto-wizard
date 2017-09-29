import asyncio
from kinto_http import exceptions as kinto_exceptions
from .logger import logger


def _sorted_principals(permissions):
    return {perm: sorted(principals) for perm, principals in permissions.items()}


async def gather_dict(dct):
    """Utility function to do asyncio.gather for dictionaries

    Do asyncio.gather on the dictionary's values, and return the
    dictionary with the futures' results replacing the futures.

    >>> promise = Future()
    >>> promise.set_result("value")
    >>> await gather_dict({"key": promise})
    {"key": "value"}
    """
    items = dct.items()
    results = await asyncio.gather(*(item[1] for item in items))
    return dict(zip((item[0] for item in items), results))


async def introspect_server(client, bucket=None, collection=None, data=False, records=False):
    if bucket:
        logger.info("Only inspect bucket `{}`.".format(bucket))
        bucket_info = await introspect_bucket(client, bucket, collection=collection,
                                              data=data, records=records)
        if bucket_info:
            return {bucket: bucket_info}
        return {}

    logger.info("Fetch buckets list.")
    buckets = await client.get_buckets()
    return await gather_dict({
        bucket['id']: introspect_bucket(client, bucket['id'], collection=collection,
                                        data=data, records=records)
        for bucket in buckets
    })


async def introspect_bucket(client, bid, collection=None, data=False, records=False):
    logger.info("Fetch information of bucket {!r}".format(bid))
    try:
        bucket = await client.get_bucket(id=bid)
    except kinto_exceptions.BucketNotFound:
        logger.error("Could not read bucket {!r}".format(bid))
        return None

    permissions = bucket.get('permissions', {})
    if len(permissions) == 0:
        logger.warn('Could not read permissions of bucket {!r}'.format(bid))

    if collection:
        result = {
            'permissions': _sorted_principals(permissions),
            'collections': {
                collection: await introspect_collection(client, bid, collection,
                                                        data=data, records=records)
            }
        }
    else:
        (collections, groups) = await asyncio.gather(
            client.get_collections(bucket=bid),
            client.get_groups(bucket=bid)
        )
        introspect_collections = gather_dict({
            collection['id']: introspect_collection(client, bid, collection['id'],
                                                    data=data, records=records)
            for collection in collections
        })
        introspect_groups = gather_dict({
            group['id']: introspect_group(client, bid, group['id'], data=data)
            for group in groups
        })
        (introspected_collections, introspected_groups) = await asyncio.gather(
            introspect_collections, introspect_groups
        )
        result = {
            'permissions': _sorted_principals(permissions),
            'collections': introspected_collections,
            'groups': introspected_groups,
        }
    if data:
        result['data'] = bucket['data']
    return result


async def introspect_collection(client, bid, cid, data=False, records=False):
    logger.info("Fetch information of collection {!r}/{!r}".format(bid, cid))
    collection = await client.get_collection(bucket=bid, id=cid)
    result = {
        'permissions': _sorted_principals(collection['permissions']),
    }
    if data:
        result['data'] = collection['data']

    if records:
        records = await client.get_records(bucket=bid, collection=cid)
        result['records'] = {
            # XXX: we don't show permissions, until we have a way to fetch records
            # in batch (see Kinto/kinto-http.py#145)
            record['id']: {"data": record, "permissions": {}} for record in records
        }
    return result


async def introspect_group(client, bid, gid, data=False):
    logger.info("Fetch information of group {!r}/{!r}".format(bid, gid))
    group = await client.get_group(bucket=bid, id=gid)
    result = {
        'permissions': _sorted_principals(group['permissions'])
    }
    data = group['data'] if data else {}
    data['members'] = sorted(group['data']['members'])
    result['data'] = data
    return result
