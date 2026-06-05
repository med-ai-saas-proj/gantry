from typing import TypeVar, Any
from xml.etree import ElementTree
import yaml

T = TypeVar("T", list, dict, float, int, str)


class DictUtils:
    @staticmethod
    def remove_empty_and_none_recursive(d: T) -> T:
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

        if isinstance(d, dict):
            res = {}
            for k, v in d.items():
                if not v:
                    continue
                pruned = DictUtils.remove_empty_and_none_recursive(v)
                if pruned:
                    res[k] = pruned
            return res
        elif isinstance(d, list):
            res = []
            for it in d:
                if not it:
                    continue
                pruned = DictUtils.remove_empty_and_none_recursive(it)
                if pruned:
                    res.append(pruned)
            return res
        else:
            return d

    @staticmethod
    def yaml_dump(d: Any) -> str:
        return yaml.safe_dump(
            d,
            indent=2,
            allow_unicode=True,
        )

    @staticmethod
    def yaml_dump_prune_empty(d: Any) -> str:
        return DictUtils.yaml_dump(
            DictUtils.remove_empty_and_none_recursive(d),
        )

    @staticmethod
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
