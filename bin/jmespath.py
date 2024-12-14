import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import jmespath
import jmespath.exceptions
from splunklib.searchcommands import Configuration, dispatch, Option, StreamingCommand, validators

from jmespath_splunk_functions import JmespathSplunkFunctions


@Configuration()
class JMESPath(StreamingCommand):
    """Resolve a JMESPath query.

    .. code-block::
        | jmespath (default=<string>)? (error=<field>)? (input=<field>)? (mvexpand=<boolean>)? (output=<field>)? <jmespath-expression>
    """
    default = Option(doc="Default value for empty results.", default=None, require=False)
    errors = Option(doc="Field in which to store errors. Default: _jmespath_error.",
                    default="_jmespath_error", require=False)
    input = Option(doc="Input field. Default: _raw.", default="_raw", require=False)
    mvexpand = Option(doc="If the result is an array, expand its values into separate events. "
                          "Default: false.",
                      default=False, require=False, validate=validators.Boolean())
    output = Option(doc="Output field. Default: jmespath", default="jmespath", require=False)
    query = Option(doc="JMESPath query.", require=True)

    @staticmethod
    def flatten(arg):
        if isinstance(arg, dict):
            yield json.dumps(arg, ensure_ascii=False)
        elif isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, (list, tuple, dict)):
                    yield json.dumps(item, ensure_ascii=False)
                else:
                    yield str(item)
        else:
            yield str(arg)

    def output_to_field(self, record, values):
        self.write_output(record, self.output, values)

    def output_to_wildcard_fields(self, record, values):
        if isinstance(values, dict):
            for (key, value) in values.items():
                self.write_output(record, self.output.replace("*", key, 1), value)
        elif isinstance(values, list):
            for idx, value in enumerate(values):
                self.write_output(record, self.output.replace("*", str(idx), 1), value)
        else:
            self.write_output(record, self.output, values)

    def write_output(self, record, field, values):
        flat_values = list(self.flatten(values))
        if not flat_values:
            flat_values = None
        elif len(flat_values) == 1:
            # Avoid the overhead of multivalue field encoding
            flat_values = flat_values[0]
        self.add_field(record, field, flat_values)

    def stream(self, records):
        jmespath_expr = jmespath.compile(self.query)
        jmespath_options = jmespath.Options(custom_functions=JmespathSplunkFunctions())
        output_f = self.output_to_wildcard_fields if "*" in self.output else self.output_to_field

        for record in records:
            field = record.get(self.input)

            try:
                if isinstance(field, list):
                    field_json = [json.loads(v) for v in field]
                else:
                    field_json = json.loads(field)
            except ValueError:
                self.add_field(record, self.errors, "Invalid JSON.")
                if self.default:
                    self.add_field(record, self.output, self.default)
                yield record
                continue

            try:
                jmespath_result = jmespath_expr.search(field_json, options=jmespath_options)
                if isinstance(jmespath_result, list) and jmespath_result and self.mvexpand:
                    yield from [output_f(r, record.copy()) for r in jmespath_result]
                    continue
                if jmespath_result is not None:
                    output_f(record, jmespath_result)
                elif self.default is not None:
                    self.add_field(record, self.output, self.default)
            except jmespath.exceptions.UnknownFunctionError as e:
                raise ValueError(f"Issue with JMESPath expression: {e}")
            except jmespath.exceptions.JMESPathError as e:
                # FIXME: Not 100% sure about what these errors mean. Should they halt?
                self.add_field(record, self.errors, f"JMESPath error: {e}")
                if self.default:
                    self.add_field(record, self.output, self.default)
            except Exception as e:
                self.add_field(record, self.errors, f"Exception: {e}")

            yield record


dispatch(JMESPath, sys.argv, sys.stdin, sys.stdout, __name__)
