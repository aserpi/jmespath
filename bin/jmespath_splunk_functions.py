import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import jmespath.functions


class JmespathSplunkFunctions(jmespath.functions.Functions):
    """Custom functions for JMSEPath to solve some typical Splunk use cases."""

    @jmespath.functions.signature({"types": ["array", "string"]})
    def _func_from_string(self, arg):
        """Parse a nested JSON text."""
        if arg is None:
            return None
        if isinstance(arg, (list, tuple)):
            return [json.loads(item) for item in arg]
        try:
            return json.loads(arg)
        except Exception:
            return arg

    @jmespath.functions.signature({"types": ["object"]})
    def _func_items(self, arg):
        """See kvpairs(arg)."""
        return self._func_kvpairs(arg)

    @jmespath.functions.signature({"types": ["object"]})
    def _func_kvpairs(self, arg):
        """Create a [key, value] array for each key value pair in an object."""
        return [list(item) for item in arg.items()]

    @jmespath.functions.signature({"types": ["array"]})
    def _func_to_hash(self, array):
        """Build an object from an array of key value pairs.

        If there are duplicates, the last value wins.
        It is the inverse of items().
        """
        object_ = {}
        for item in array:
            try:
                key, value = item
                object_[key] = value
            except Exception:
                pass
        return object_

    @jmespath.functions.signature({"types": ["array"]}, {"types": ["string"]},
                                  {"types": ["string"]})
    def _func_unroll(self, array, key_key, value_key):
        """Build an object from an array of objects with key value pairs.

        Example: unroll([{"Key": "Pair key", "Value": "Pair value"}], "Key", "Value")
        produces {"Pair key": "Pair value"}.
        """
        object_ = {}
        for item in array:
            try:
                key = item[key_key]
                value = item[value_key]
                if not isinstance(key, str):
                    key = str(key)

                # TODO: User option: Overwrite, keep, or make multivalue.
                if key not in object_:
                    object_[key] = value
                elif isinstance(object_[key], list):
                    object_[key].append(value)
                else:
                    # Opportunistically convert into an array to hold multiple values.
                    # Generally harmful to structured data, but plays nice with Splunk's multivalue
                    # fields.
                    object_[key] = [object_[key], value]
            except KeyError:
                # If either field is missing, just silently move on
                continue
        return object_
