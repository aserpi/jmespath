import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import jmespath.exceptions
import jmespath.functions


class JmespathSplunkFunctions(jmespath.functions.Functions):
    """Custom functions for JMSEPath to solve some typical Splunk use cases."""

    @jmespath.functions.signature({"types": ["array", "string"]})
    def _func_parse_json(self, arg):
        """Parse a nested JSON text."""
        if arg is None:
            return None
        if isinstance(arg, (list, tuple)):
            return [json.loads(item) for item in arg]
        try:
            return json.loads(arg)
        except Exception:
            return arg

    @jmespath.functions.signature({"types": ["array"]}, {"types": ["string"]},
                                  {"types": ["string"]}, {"types": ["string"],
                                                          "variadic": True})
    def _func_unroll(self, array, key_key, value_key, *arguments):
        """Build an object from an array of objects with key value pairs.

        The last argument defines the behavior in case of multiple object with
        the same key:
        - all: Create an array with all the objects
        - first: Discard the new value and keep existing objects
        - last: Keep the new value overwriting existing objects

        Example: unroll([{"Key": "Pair key", "Value": "Pair value A"},
                         {"Key": "Pair key", "Value": "Pair value B"}],
                        "Key", "Value", "all")
        produces {"Pair key": ["Pair value A", "Pair value B"]}.
        """
        if len(arguments) != 1:
            raise jmespath.exceptions.JMESPathError(
                f"syntax-error: unroll() expects at most a single 'mode' "
                f"argument, but received {len(arguments)} instead.")

        mode = arguments[0]
        if mode != "all" and mode != "first" and mode != "last":
            raise jmespath.exceptions.JMESPathError(
                f"syntax-error: unroll() expects the mode to be 'all', "
                f"'first', or 'last', but received `{mode}` instead.")

        object_ = {}
        for item in array:
            try:
                key = item[key_key]
                value = item[value_key]
                if not isinstance(key, str):
                    key = str(key)

                if key in object_:
                    if mode == "all":
                        object_[key].append(value)  # Already a list
                    elif mode == "last":
                        object_[key] = value
                else:
                    if mode == "all":
                        object_[key] = [object_[key]]
                    else:
                        object_[key] = value
            except KeyError:
                continue  # If either field is missing, just silently move on
        return object_
