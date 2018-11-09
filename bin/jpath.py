import json
import os
import re
import sys

import splunk.Intersplunk as si

ERROR_FIELD = "_jmespath_error"

DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(DIR, "lib"))

import jmespath
from jmespath import functions
from jmespath.exceptions import ParseError, JMESPathError, UnknownFunctionError


# Custom functions for the JMSEPath language to make some typical splunk use cases easier to manage
class JmesPathSplunkExtraFunctions(functions.Functions):

    @functions.signature({'types': ['string', 'array']})
    def _func_parse(self, s):
        """
        Possible name options:
            parse           Nice, but parse what?
            from_string     Parity with to_string (exports data AS a json string)
            from_json?      Maybe more clear?  not sure
            unnest          Can't get past the double "n"s
            jsonstr         My first option, but don't like it.
        """
        # XXX: Figure out how to make this properly support (pass-through) a 'null' type
        if s is None:
            return None
        if isinstance(s, (list,tuple)):
            return [ json.loads(i) for i in s ]
        try:
            return json.loads(s)
        except:
            return s

    @functions.signature({'types': ['array']}, {'types':['string']}, {'types':['string']})
    def _func_unroll(self, objs, key, value):
        """ What to call this"?
            unroll
            to_hash     Called hash in JSON
            zipdict     ?
            kvarray2hash    a bit long
            xyseries    haha
            table/untable
            make_hash
            unzip       Maybe
        """
        d = dict()
        for item in objs:
            try:
                k = item[key]
                v = item[value]
                if not isinstance(k, (str, unicode)):
                    k = str(k)
                k = sanitize_fieldname(k)
                # XXX: User option:  Overwrite, or make mvlist  (Possibly just make 2 different functions?)
                if k not in d:
                    d[k] = v
                else:
                    # Opportunistically turn this into a container to hold more than on value.
                    # Generally harmful to structured data, but plays nice with Splunk's mvfields
                    if not isinstance(d[k], list):
                        d[k] = [ d[k] ]
                    d[k].append(v)
            except KeyError:
                # If either field is missing, just silently move on
                continue
            except Exception as e:
                # FOR DEBUGGING ONLY
                return "ERROR:  Couldn't find key={} value={} in {}".format(key, value, item)
        return d


jp_options = jmespath.Options(custom_functions=JmesPathSplunkExtraFunctions())


def sanitize_fieldname(field):
    # XXX: Add caching, if needed
    clean = re.sub(r'[^A-Za-z0-9_.{}\[\]]', "_", field)
    # Remove leading/trailing underscores
    # It would be nice to preserve explicit underscores but don't wnat to complicate the code for
    # a not-yet-existing corner case.  Generally it's better to avoid hidden fields.
    clean = clean.trim("_")


def flatten(container):
    if isinstance(container, (list, tuple)):
        for i in container:
            if isinstance(i, (list, tuple)):
                for j in flatten(i):
                    yield str(j)
            else:
                yield str(i)
    else:
        yield str(container)



if __name__ == '__main__':
    try:
        keywords, options = si.getKeywordsAndOptions()
        defaultval = options.get('default', None)
        field = options.get('field', '_raw')
        outfield = options.get('outfield', 'jpath')
        if len(keywords) != 1:
            si.generateErrorResults('Requires exactly one path argument.')
            sys.exit(0)
        path = keywords[0]

        try:
            jp = jmespath.compile(path)
        except ParseError as e:
            # Todo:  Consider stripping off the last line "  ^" pointing to the issue.
            # Not helpful since Splunk wraps the error message in a really ugly way.
            si.generateErrorResults("Invalid JMESPath expression '{}'. {}".format(path, e))
            sys.exit(0)

        results, dummyresults, settings = si.getOrganizedResults()
        # for each results
        for result in results:
            # get field value
            ojson = result.get(field, None)
            added = False
            if ojson is not None:
                try:
                    json_obj = json.loads(ojson)
                except ValueError:
                    # Invalid JSON.  Move on, nothing to see here.
                    continue
                try:
                    values = jp.search(json_obj, options=jp_options)
                    result[outfield] = list(flatten(values))
                    result[ERROR_FIELD] = None
                    added = True
                except UnknownFunctionError as e:
                    # Can't detect invalid function names during the compile, but we want to treat
                    # these like syntax errors:  Stop processing immediately
                    si.generateErrorResults("Issue with JMESPath expression. {}".format(e))
                    sys.exit(0)
                except JMESPathError as e:
                    # Not 100% sure I understand what these errors mean. Should they halt?
                    result[ERROR_FIELD] = "JMESPath error: {}".format(e)
                except Exception as e:
                    result[ERROR_FIELD] = "Exception: {}".format(e)

            if not added and defaultval is not None:
                result[outfield] = defaultval
        si.outputResults(results)
    except Exception as e:
        import traceback

        stack = traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
