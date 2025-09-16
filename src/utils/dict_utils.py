from xml.etree import ElementTree


def remove_empty_and_none_recursive(d):
    """
    Recursively removes keys from a dictionary whose values are None, empty strings, empty lists,
    or empty dictionaries.
    Args:
        d (dict): The input dictionary to clean.
    Returns:
        dict: A new dictionary with all keys removed where the value is None, an empty string,
        an empty list, or an empty dictionary. Nested dictionaries are processed recursively.
    Example:
        >>> remove_empty_and_none_recursive({
        ...     "a": None,
        ...     "b": "",
        ...     "c": [],
        ...     "d": {},
        ...     "e": {"f": "", "g": 1},
        ...     "h": 2
        ... })
        {'e': {'g': 1}, 'h': 2}
    """

    if not isinstance(d, dict):
        return d
    return {
        k: remove_empty_and_none_recursive(v)
        for k, v in d.items()
        if v is not None
        and v != ""
        and v != []
        and remove_empty_and_none_recursive(v) != {}
    }


def xml_to_dict(root: ElementTree.ElementTree) -> dict:
    def parseXml(node: ElementTree.Element):
        children = list(node)
        if len(children) == 0:
            return node.text

        res = {}
        for child in node:
            if child.tag in res:
                if type(res[child.tag]) == list:
                    res[child.tag].append(parseXml(child))
                else:
                    res[child.tag] = [res[child.tag], parseXml(child)]
            else:
                res[child.tag] = parseXml(child)
        return res

    # Convert the XML to a Python dictionary
    data = {}
    for child in root.iter():
        data[child.tag] = parseXml(child)
    return data
