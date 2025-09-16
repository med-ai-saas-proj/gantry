def remove_empty_and_none_recursive(dict):
    """
    Recursively removes keys from a dictionary whose values are None, empty strings, empty lists, 
    or empty dictionaries.
    Args:
        dict (dict): The input dictionary to clean.
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

    """
    if not isinstance(dict, dict):
        return dict
    return {
        k: remove_empty_and_none_recursive(v)
        for k, v in dict.items()
        if v is not None
        and v != ""
        and v != []
        and remove_empty_and_none_recursive(v) != {}
    }
