def extend_by_id(a, b):
    a_ids = list(map(lambda item: item.get("id"), a))
    a.extend(list(filter(lambda item: item.get("id") not in a_ids, b)))
    return a
