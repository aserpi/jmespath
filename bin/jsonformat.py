import ast
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class JsonFormatCommand(StreamingCommand):
    """Formats JSON strings as specified.

    .. code-block::
        | jsonformat (errors=<field>)? (indent=<int>)? (input_mode=(json|python))? (order=(preserve|sort))? (output_mode=(json|makeresults))? (<field> (AS <field>)?)+
    """
    errors = Option(doc="Field in which to store errors. Default: _jmespath_error.",
                    default="_jmespath_error", require=False, validate=validators.Fieldname())
    indent = Option(doc="How many spaces for each indentation. Default: 2.",
                    default=2, require=False, validate=validators.Integer(0, 10))
    input_mode = Option(doc="Input mode: json (default), python (repr format, literals only).",
                        default="json", require=False, validate=validators.Set("json", "python"))
    order = Option(doc="Order keys in objects: preserve (default), sort.",
                   default="preserve", require=False, validate=validators.Set("preserve", "sort"))
    output_mode = Option(doc="Output mode: json (default), makeresults (for example creation).",
                         default="json", require=False,
                         validate=validators.Set("json", "makeresults"))
    _special_chars_pattern = re.compile("|".join(('\\', "\n", "\t", '"')))

    @staticmethod
    def _parse_field(field_value, parse_function):
        parsing_errors = []
        if isinstance(field_value, (list, tuple)):
            parsed_field = []
            for value in field_value:
                try:
                    parsed_field.append(parse_function(value))
                except (json.decoder.JSONDecodeError, ValueError) as e:
                    parsing_errors.append(str(e))
        else:
            try:
                parsed_field = parse_function(field_value)
            except (json.decoder.JSONDecodeError, ValueError) as e:
                parsed_field = None
                parsing_errors.append(str(e))
        return parsed_field, parsing_errors

    def _output_json(self, data, _):
        """Formats a JSON object."""
        return json.dumps(data, ensure_ascii=False, indent=self.indent,
                          sort_keys=(self.order == "sort"))

    def _output_makeresults(self, data, field):
        """Builds a "makeresults" (run-anywhere) output sample."""
        json_min = json.dumps(data, ensure_ascii=False, indent=None, separators=(",", ":"))
        json_min = self._special_chars_pattern.sub(lambda m: f"\\{re.escape(m.group(0))}",
                                                   json_min)
        return f'| makeresults | eval {field}="{json_min}"'

    def _rename_fields(self):
        """Convert a list of fields in a list of (old_field, new_field) tuples.
        The list of names may include renames with the syntax "old_field as new_field".
        """
        fields = collections.deque(self.fieldnames)
        renamed_fields = []
        while fields:
            field = fields.popleft()
            if len(fields) > 1 and fields[0].lower() == "as":
                field.popleft()
                renamed_fields.append((field, field.popleft()))
            else:
                renamed_fields.append((field, field))
        return renamed_fields

    def stream(self, records):
        parse_function = ast.literal_eval if self.input_mode == "python" else json.loads
        renamed_fields = self._rename_fields() if self.fieldnames else [("_raw", "_raw")]
        self.logger.info(f"Found field mapping {renamed_fields}")

        if self.output_mode == "makeresults":
            output_field = self._output_makeresults
        else:
            output_field = self._output_json

        for record in records:
            errors = {}
            for (src_field, dest_field) in renamed_fields:
                field_value = record.get(src_field)
                if not field_value:
                    continue

                parsed_field, parsing_errors = self._parse_field(field_value, parse_function)
                if parsing_errors:
                    errors[src_field] = parsing_errors
                if not parsed_field:
                    continue

                try:
                    text = output_field(parsed_field, dest_field)
                    self.add_field(record, dest_field, text)
                except ValueError as e:
                    if src_field in errors:
                        errors[src_field].append(e)
                    else:
                        errors[src_field] = [e]
            if errors:
                self.add_field(record, self.errors, json.dumps(errors))
            yield record


dispatch(JsonFormatCommand, sys.argv, sys.stdin, sys.stdout, __name__)
