# JMESPath Community for Splunk

This app provides two custom search commands: `jmespath`, which manipulates JSON
based on a JMESPath query, and `jsonformat`, which formats a JSON.

JMESPath (pronounced *James path*) Community makes dealing with JSON data in
Splunk easier by leveraging a standardized query language.
This allows you to declaratively specify how to manipulate and extract elements
from a JSON document.
More information can be found at [jmespath.site](https://jmespath.site)
(community) and [jmespath.org](https://jmespath.org) (original).

* [Why JMESPath Community](#why-jmespath-community)
* [jmespath](#jmespath)
* [jsonformat](#jsonformat)
  * [Extensions](#extensions)
  * [Output modes](#output-modes)
* [Examples](#examples)
  * [jmespath examples](#jmespath-examples)
  * [jsonformat examples](#jsonformat-examples)
* [Installation](#installation)
* [Support](#support)
* [Credits](#credits)


## Why JMESPath Community

Splunk's `spath` command and JSON functions allow to efficiently manipulate
JSON documents.
However, they struggle with arrays and complex objects, and the same could be
seen with Splunk's automatic JSON field extraction.

While these issues can often be avoided in simple homogeneous arrays, that's not
always the case.
The following snippet is part of a nested JSON from a Microsoft Office 365
Management Activity event.

```json
[
  {
    "Name": "StrongAuthenticationRequirement",
    "NewValue": [
      {
        "RelyingParty": "*",
        "State": 1,
        "RememberDevicesNotIssuedBefore": "2018-11-08T19:37:42.7363619Z"
      }
    ],
    "OldValue": []
  },
  {
    "Name": "Included Updated Properties",
    "NewValue": "StrongAuthenticationRequirement",
    "OldValue": null
  }
]
```

This results in fields that look like this:

| **Field**                                      | **Values**                                                      |
|------------------------------------------------|-----------------------------------------------------------------|
| `{}.Name`                                      | StrongAuthenticationRequirement<br/>Included Updated Properties |
| `{}.NewValue`                                  | StrongAuthenticationRequirement                                 |
| `{}.NewValue{}.RelyingParty`                   | *                                                               |
| `{}.NewValue{}.RememberDevicesNotIssuedBefore` | 2018-11-08T19:37:42.7363619Z                                    |
| `{}.NewValue{}.State`                          | 1                                                               |
| `{}.OldValue`                                  | null                                                            |


The correlation between property name and its values is lost.
Note also the use of the `{}.` prefix for all the fields because the data is in
an array without a named top-level key.
You can test it in Splunk with this search:

```
| makeresults
| eval _raw="[{\"Name\":\"StrongAuthenticationRequirement\",\"OldValue\":[],\"NewValue\":[{\"RelyingParty\":\"*\",\"State\":1,\"RememberDevicesNotIssuedBefore\":\"2018-11-08T19:37:42.7363619Z\"}]},{\"Name\":\"Included Updated Properties\",\"OldValue\":null,\"NewValue\":\"StrongAuthenticationRequirement\"}]"
| spath
```

JMESPath allows JSONs to be parsed and further processed in Splunk without
losing any information.
JMESPath Community introduces many new features over the original, such as

* Lexical scoping
* Object manipulation
* String slicing
* Arithmetic expressions

In addition, this app includes some functions not in the JMESPath Community
specification that simplify common Splunk use cases.
Thanks to that, finding which properties have been updated requires a single
command:

[//]: # (TODO: Check)
```
| jmespath output="updated_properties" query="from_items([].[Name, NewValue]).\"Included Updated Properties\""
```

## jmespath

```
jmespath (default=<string>)? (error=<field>)? (input=<field>)? (mvexpand=<boolean>)? (output=<field>)? query=<jmespath-expression>
```

* *query*: JMESPath expression to be applied to the JSON. **Required**.
* *default*: Default value for empty results.
* *errors*: Field in which to store errors. Default: `_jmespath_error`.
* *input*: Input field. Default: `_raw`.
* *mvexpand*: If the result is an array, expand its elements into separate
  events. Default: `false`.
* *output*: Output field. Default: `jmespath`.

See the GitHub repository for some [examples](https://github.com/aserpi/jmespath/blob/main/examples/jmespath.md).

### Extensions

In addition to the functions defined by the JMESPath Community standard,
`jmespath` supports two new extra functions.

#### parse_json()

`parse_json(@)` parses a JSON object or array from a string.

Example: `{"nested": "{\"key\": \"value\"}"} | parse_json(@.nested)` produces
`{"key": "value"}`.

This functionality is being [discussed](https://github.com/jmespath-community/jmespath.spec/discussions/22)
by the JMESPath community, but has not yet been added to the specification.

#### unroll()

`unroll(@, key, value, [mode])` creates an object from an array of multiple
object with the same key.

*mode* is an optional argument that defines the behavior in case of conflicts:
- `all` (default): Keep all values in an array
- `first`: Keep only the first value
- `last`: Keep only the last value

Example: `[{"Key": "Pair key", "Value": "Pair value A"}, {"Key": "Pair key", "Value": "Pair value B"}] | unroll(@, "Key", "Value", "all")`
produces `{"Pair key": ["Pair value A", "Pair value B"]}`.

`unroll()` was introduced to make it easier to parse this type of log, which has
been adopted by several vendors.
However, it is not strictly necessary, as its output can be reproduced while
remaining fully compliant with the JMESPath Community standard.
Considering the example above, all three modes can be replaced:

- `all` with `from_items(items(group_by(@, &Key))[*][let $key = [0], $value = [1][*].Value in [$key, $value]][])`
- `first` with `from_items([::-1].[Key, Value])`
- `last` with `from_items([].[Key, Value])`

### Output modes

The `jmespath` search command has two different modes for handling output
variables: a field or a wildcard field template.

With a field, only that specific field is updated. If the result is a complex
object, then a JSON formatted string is returned instead of the raw value.
This preserves data accuracy and allows for multistep processing.

When a wildcard output field is given, multiple output fields are created using
the wildcard as a field template.
The JSON object keys (or, in case of arrays, indexes starting from `0`) are
combined with the field template to make the final field names.
The number of fields that will be created depends completely on the result.
If the result is neither a JSON object nor an array, the wildcard is not
replaced and the field name remains unvaried.

#### Example

The following example demonstrates the different means of using the `output`
field for the same JSON input:

```json
{ "colors" :
    {
        "apple" : "yellow",
        "snake" : "black",
        "foobar" : "brown"
    }
}
```

given the expression

```
... | jmespath output=<output> query="colors"
```

| `<output>`  | Field(s) created                                                                                  | Notes                                                                                  |
|-------------|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `colors`    | *colors*=`{ "apple": "yellow", "snake": "black", "foobar" : "brown" }`                            | Simple static output. The output is converted back to JSON since value is structured.  |
| `color.*`   | *color.apple*=`yellow`<br />*color.snake*=`black`<br />*color.foobar*=`brown`                     | The *color.* prefix is applied to all keys.                                            |
| `*_color`   | *apple_color*=`yellow`<br />*snake_color*=`black`<br /> *foobar_color*=`brown`                    | The *_color* suffix is applied to all keys.                                            |
| `*`         | *apple*=`yellow`<br />*snake*=`black`<br />*foobar*=`brown`                                       | Keys are used as is. This could overwrite existing fields if they are already present. |

A few takeaways:

* The static output makes it easy for subsequent processing with additional
  `jmespath` or `spath` commands.
* Prefix and suffix allow fields to be easily grouped by other search commands,
  like `stats` (e.g., `stats values(color.*) as color.*`) or `fields` (e.g.,
  `| fields - color.*`).
* The behavior of `output=*` is generally similar to the one of `spath`.
  However, `jmespath` only unwraps the first level: `{ "a": { "b": { "c": 1}}}`
  would return *a.b*=`{"c":1}`, whereas `spath` would return *a.b.c*=`1`.
* `jmespath` is not subject to the value of `extraction_cutoff` in the `spath`
  stanza of `limits.conf`


## jsonformat

```
jsonformat (errors=<field>)? (indent=<int>)? (input_mode=(json|python))? (order=(preserve|sort))? (output_mode=(json|makeresults))? (<field> (AS <field>)?)+
```

* *errors*: Field in which to store errors. Default: _`jmespath_error`.
* *indent*: How many spaces for each indentation. Default: `2`.
* *order*: Order of keys in objects, can be `preserve` (default) or `sort`.
* *input_mode*: Format of the input, can be `json` (default) or `python`
  (Python `repr()` format, literals only).
  **This option should only be used for debugging purposes and may be removed
  in a future version**.
* *output_mode*: Output format, can be `json` (default) or `makeresults`
  (creates a portable Splunk search snippet).
  **This option should only be used for debugging purposes and may be removed
  in a future version**.


## Examples

Here are some examples for `jmespath` and `jsonformat`, but the use cases are
too numerous to list.

### jsonformat examples

The most obvious use case for `jsonformat` is to prettify JSON objects, but
it's not the only one.

#### Beautifying JSON events

In raw mode, many JSON events are optimized to save space and are therefore
difficult to read.
Take for example this event:

```json
{"glossary":{"title":"example glossary","GlossDiv":{"title":"S","GlossList":{"GlossEntry":{"ID":"SGML","SortAs":"SGML","GlossTerm":"Standard Generalized Markup Language","Acronym":"SGML","Abbrev":"ISO 8879:1986","GlossDef":{"para":"A meta-markup language, used to create markup languages such as DocBook.","GlossSeeAlso":["GML","XML"]},"GlossSee":"markup"}}}}}
```

The most obvious use case for the command is to make it human readable:

```json
{
  "glossary": {
    "title": "example glossary",
    "GlossDiv": {
      "title": "S",
      "GlossList": {
        "GlossEntry": {
          "ID": "SGML",
          "SortAs": "SGML",
          "GlossTerm": "Standard Generalized Markup Language",
          "Acronym": "SGML",
          "Abbrev": "ISO 8879:1986",
          "GlossDef": {
            "para": "A meta-markup language, used to create markup languages such as DocBook.",
            "GlossSeeAlso": [
              "GML",
              "XML"
            ]
          },
          "GlossSee": "markup"
        }
      }
    }
  }
}
```

Using `jsonformat` without any arguments produces the above JSON object:

```
| makeresults
| eval json_raw="{\"glossary\":{\"title\":\"example glossary\",\"GlossDiv\":{\"title\":\"S\",\"GlossList\":{\"GlossEntry\":{\"ID\":\"SGML\",\"SortAs\":\"SGML\",\"GlossTerm\":\"Standard Generalized Markup Language\",\"Acronym\":\"SGML\",\"Abbrev\":\"ISO 8879:1986\",\"GlossDef\":{\"para\":\"A meta-markup language, used to create markup languages such as DocBook.\",\"GlossSeeAlso\":[\"GML\",\"XML\"]},\"GlossSee\":\"markup\"}}}}}"
| jsonformat json_raw as json_pretty
```

#### Comparing JSON objects

Using `jsonformat` with `order="sort"` and a fixed indent level (even the
default one) allows to compare two normalized JSON objects removing key order
and whitespace differences.
Please note that array elements are not sorted because according to RFC 8259

> An array is an ordered sequence of zero or more values.

For example,

```json
{
  "key1": "value1",
  "key2": [
    "array_element1",
    "array_element2"
  ]
}
```

is equivalent to

```json
{"key2":["array_element1","array_element2"],"key1":"value1"}
```

but different from

```json
{
  "key1": "value1",
  "key2": [
    "array_element2",
    "array_element1"
  ]
}
```

This is a Splunk search that illustrates this behavior:

```
| makeresults
| eval json1_raw="{\"key1\": \"value1\", \"key2\": [\"array_element1\", \"array_element2\"]}",
    json2_raw="{\"key2\":[\"array_element1\", \"array_element2\"],\"key1\": \"value1\"}",
    json3_raw="{\"key1\": \"value1\", \"key2\": [\"array_element2\", \"array_element1\"]}"
| jsonformat order="sort" json1_raw as json1_pretty, json2_raw as json2_pretty, json3_raw as json3_pretty
| eval json1_equals_json2=if(json1_pretty=json2_pretty, "Yes", "No"),
    json1_equals_json3=if(json1_pretty=json3_pretty, "Yes", "No")
```

#### Creating a reproducible example (debugging only)

`jsonformat` can create a Splunk search snippet that generates a JSON object
equivalent to the one in the input field.

```
| makeresults
| eval json_raw="{\"key2\": [\"array_element1\", \"array_element2\"], \"key1\": \"value1\"}"
| jsonformat output_mode="makeresults" json_raw as json_makeresults
```

**This functionality should only be used for debugging purposes and may be
removed in a future version.**

#### Converting a Python `repr()` object to JSON (debugging only)

`jsonformat` can convert a Python literal (`repr()` format) to JSON, easing
debugging and allowing for further processing via `spath` or `jmespath`.
Python literals use single quotation marks instead of double.

```
| makeresults
| eval json_raw="{'glossary': {'title': 'example glossary', 'GlossDiv': {'title': 'S', 'GlossList': {'GlossEntry': {'ID': 'SGML', 'SortAs': 'SGML', 'GlossTerm': 'Standard Generalized Markup Language', 'Acronym': 'SGML', 'Abbrev': 'ISO 8879:1986', 'GlossDef': {'para': 'A meta-markup language, used to create markup languages such as DocBook.', 'GlossSeeAlso': ['GML', 'XML']}, 'GlossSee': 'markup'}}}}}"
| jsonformat input_mode="python" json_raw as json_pretty
```

**This functionality should only be used for debugging purposes and may be
removed in a future version.**


## Installation

[//]: # (TODO: Add Splunkbase ID)
Download and install the latest release on search heads from [Splunkbase](https://splunkbase.splunk.com/app/TODO) or [GitHub](https://github/aserpi/jmespath_community/releases/latest).
The app requires no configuration.

## Support

Community support is available on best-effort basis.
For information about commercial support, contact [aserpi](mailto:splunkapps@aserpi.com).
Issues are tracked via [GitHub](https://github.com/aserpi/jmespath_community/issues)


## Credits

 * John Berwick: Original author of [JMESPath for Splunk](https://splunkbase.splunk.com/app/3237)
 * Lowell Alleman: Current maintainer of [JMESPath for Splunk](https://splunkbase.splunk.com/app/3237)
 * JMESPath Community: Maintainer of the [jmespaht-community](https://pypi.org/project/jmespath-community/)
   Python library
 * The app icon is based on the [JMESPath Community](https://jmespath.site/)
   logo
