# Changelog

## 2.0.0 (TBD): New and improved with JMESPath Community

Improvements:

* Added support for non-ASCII characters
* Added support for multivalue input fields
* Performance improvements
* `jmespath` command:
  * Changed the library to [JMESPath Community](https://jmespath.site)
  * Added option to expand multivalue results
  * Added optional argument to `unroll()` to manage conflicts
* `jsonformat` command:
  * Added option for `error` field
  * Added output of array to wildcard fields
  * Added support for field rename in `output_mode=makeresults`
  * Migrated to custom search command protocol version 2
* Show icon in app menus

Breaking changes:

* Dropped support for Splunk 7.x: JMESPath 1.0 dropped support for Python 2
* New app ID `jmespath_community`
* Removed custom logging
* `jmespath` command:
  * Use the `query` option instead of unnamed input
  * Adopted JMESPath community function nomenclature:
    * `from_string()` renamed to `parse_json()`
    * `to_object()` renamed to `from_items()`
  * `unroll()` puts the value into an array by default (affects only subsequent
    JMESPath processing)
  * Changed the default output field to `jmespath`
  * Field and key names are not sanitized anymore
  * Removed legacy options (`field`, `outfield`)
  * Use default value in case of processing errors
  * Wildcard field is not modified if the output is neither an object nor an
    array
* `jsonformat` command:
  * Do not output unparsed fields
  * Do not update *linecount* when writing to *_raw*
  * Dropped support for `order=undefined`: not applicable to Python 3
  * Errors are displayed by default in the `_jmespath_error` field


## 1.9.5 (July 17, 2020): Splunk 8 support

* Add support for Splunk 8 using Python 3.
  Earlier versions worked fine on Splunk 8, but used Python 2.
* Update Python libraries:
    * jmespath 0.9.4 → 0.10.0
    * splunk-sdk 1.6.6 → 1.6.13
    * six 1.15.0 (new)
* Removed newlines from the jsonformat `output=makeresults` output.
  Whoops.
* Add Python 3 optimization for `jsonformat order=preserve`
* Minor internal exception handling improvements
* Logging level is now `WARNING` by default: less noise


## 1.9.4 (March 20, 2019): Fifth public 2.0 release candidate

* Several minor bug fixes
* Added a new output mode to `jsonformat` that allows for the creation of run-anywhere examples.
  Use `output_mode=makeresults`.
* Update `jsonformat` to use order preservation by default.
  You can revert to the older, faster, behavior with `order=undefined`.
* External library refresh: jmespath 0.9.4 and splunk-sdk 1.6.6
* Many docs updates and typo fixes


## 1.9.4 (Nov 14, 2018): Fourth public 2.0 release candidate

* Fix bug with mvlist inputs.
  More of a just-dont-crash-workaround for the moment.
* Enhance output so that mvfields are only used as needed.
  Also eliminated the scenario where a single value could be unnecessarily wrapped in a single item
  list and therefore be returned as a JSON string.


## 1.9.3 (Nov 13, 2018): Third public 2.0 release candidate

* Adds wildcard support for the output argument.
  This allows hashes to be expanded into multiple output fields in one invocation to `jmespath`.
* Fixed bug in the `unroll()` function
* Added support for quoting within the JMESpath expression, thus allowing support for keys that
  contain symbols


## 1.9.2 (Nov 13, 2018): Second public 2.0 release candidate

* Adds secondary search command: `jsonformat`
* Supports formatting JSON events and/or fields, syntax validation, control over key ordering and
  so on.
  Also contains an Easter egg where it can convert a Python repr string into a valid JSON object,
  helpful for debugging splunklib searchcommand logs.
* Adds the Splunk Python SDK (1.6.5) for use with `jsonformat` and eventually `jmespath`


## 1.9.1 (Nov 12, 2018): First public 2.0 release candidate

* Add several custom functions to JMESPath core to simplify common Splunk data scenarios
* Add support for `spath`-style options
* Ensure that complex results are always returned as a JSON string, not as a Python representation
  format.
  This allows subsequent processing with less hassle.
* Significant expansion of docs and UI feedback

Deprecations:

* `xpath`-style options `field` and `outfield` have been deprecated.
  Will be removed in v2.


## 1.0.2 (Nov 9, 2018): Added logo

Add appIcon images to avoid AppInspect violations


## 1.0.1 (Nov 9, 2018): Lowell's first release (stability of existing code)

* Upgraded jmsepath Python library to 0.9.3
* Added error reporting for JMESpath errors (JSON decoding errors are still silently ignored)
* Fixed bug where 'default' would overwrite query output
* Add inline help and hints to the UI (`searchbnf`)


## 1.0 RC2 (July 26, 2016): Pre-release by John Berwick

Add flatten procedure.


## 1.0 RC (July 24, 2016): Pre-release by John Berwick

First public release
.
