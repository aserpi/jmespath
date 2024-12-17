# Common data formats

### Extract all the URLs from the `relatedContent` object
```
jmespath output=url "relatedContent[].url"
```

### Unroll a list of nested hashes
Unroll a list of nested hashes into a set of fields with a custom prefix.  In this example an input like:

```
{ "config" : [ {"Name": "ip", "Value": "10.1.1.9"}, ...] }
```
Will extract a new field: cfg.ip="10.1.1.9"

Command:
```
jmespath output=cfg.* "config[] | unroll(@,'Name','Value')
```

### Extract nested JSON
Extract nested JSON from `additionalTagets` contained within an Office 365 Azure AD management event
```
jmespath output=additionalTargets "ExtendedProperties[?Name=='additionalTargets'].Value | from_string(@)"
```

## Office 365 management events

Example events from a search like this:

```sourcetype="o365:management:activity" Operation="Enable Strong Authentication."```

Example JSON event (truncated for brevity)
```json
{
  "ActorIpAddress": "<null>",
  "RecordType": 8,
  "AzureActiveDirectoryEventType": 1,
  "ExtendedProperties": [
    {
      "Name": "actorObjectClass",
      "Value": "User"
    },
    {
      "Name": "actorUPN",
      "Value": "actor@example.com"
    },
    {
      "Name": "targetUPN",
      "Value": "target@example.com"
    },
    {
      "Name": "targetIncludedUpdatedProperties",
      "Value": "[\"StrongAuthenticationRequirement\"]"
    },
    {
      "Name": "targetUpdatedProperties",
      "Value": "[{\"Name\":\"StrongAuthenticationRequirement\",\"OldValue\":[],\"NewValue\":[{\"RelyingParty\":\"*\",\"State\":1,\"RememberDevicesNotIssuedBefore\":\"2018-11-08T19:37:42.7363619Z\"}]},{\"Name\":\"Included Updated Properties\",\"OldValue\":null,\"NewValue\":\"StrongAuthenticationRequirement\"}]"
    }
  ],
  "Id": "ec50000f-32cc-40e0-820c-565abcdefe00",
  "UserId": "actor@example.com",
  "Target": [
    {
      "ID": "User",
      "Type": 2
    },
    {
      "ID": "target@example.com",
      "Type": 5
    }
  ],
  "CreationTime": "2018-11-08T19:37:43",
  "Workload": "AzureActiveDirectory",
  "Version": 1,
  "Actor": [
    {
      "ID": "actor@example.com",
      "Type": 5
    }
  ],
  "ResultStatus": "Success",
  "ObjectId": "target@splunko365.com",
  "UserKey": "1004BFDDDEABBB1F@example.com",
  "Operation": "Enable Strong Authentication."
}
```

Observations:
1. Interesting data is under `ExtendedProperties`.  Which is a list of objects, each object has a `Name` and `Value`.  This requires several Splunk search commands to handle properly.
1. The `targetUpdatedProperties` section seems to have values of interest, but note that the content of `Values` is a nested JSON object.  (A json string instead of a JSON object, hence extra escape characters around all double quotes.)  This isn't the only occurrence of nested JSON but it's the on we're probably most interested in.  (Note that sometimes this particular field is truncated at the source, in which case the JSON is invalid and cannot be parsed this way.  This is a feature request #7)


### Extract targetUPN
The first use case is rather simple, extract the `tagetUPN` extended property
```
... | jmespath output=targetUPN "ExtendedProperties[?Name=='targetUPN'].Value"
```

Output:

| **targetUPN**      |
|--------------------|
| `jane@example.com` |

### Extract all the ExtendedProperties into their own fields
```
... | jmespath output=ep.* "unroll(ExtendedProperties, 'Name', 'Value')"
```

Output:

| **field**                          | **value**                                                                                  |
|------------------------------------|--------------------------------------------------------------------------------------------|
| ep.actorObjectClass                | User                                                                                       |
| ep.actorUPN                        | `john@example.com`                                                                         |
| ep.targetUPN                       | `jane@example.com`                                                                         |
| ep.targetIncludedUpdatedProperties | ["StrongAuthenticationRequirement"]                                                        |
| ep.targetUpdatedProperties         | [{"Name":"StrongAuthenticationRequirement","OldValue":[],"NewValue":[{"RelyingParty":\...} |
### Extract the nested JSON
Pull out the `targetUpdatedProperties` Value and parse it
```
... | jmespath output=props "ExtendedProperties[?Name=='targetUpdatedProperties'].Value | from_string(@[0])"
````

Output:

| **props**                                                                                                                                                                                                                                                                    |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `[{"Name":"StrongAuthenticationRequirement","OldValue":[],"NewValue":[{"RelyingParty":"*","State":1,"RememberDevicesNotIssuedBefore":"2018-11-08T19:37:42.7363619Z"}]},{"Name":"Included Updated Properties","OldValue":null,"NewValue":"StrongAuthenticationRequirement"}]` |

Note that the `from_string()` function is (1) a custom jmsepath function extension specific to this plugin, and (2) isn't very useful in this exact use case because whenever the search commands saves the values it has to convert the data back into JSON anyways.  So to make this truly valuable, the `from_string()` can be followed up with additional operations.  This way multiple calls to `jmespath` (or `jmespath` followed by `spath` can be avoided).

Here's an updated example that grabs the first `NewValue` from the nested JSON content:

    ... | jmespath output=new_prop_values.* "ExtendedProperties[?Name=='targetUpdatedProperties'].Value | from_string(@[0])[0].NewValue[0]"

Output:

| **field**                                      | **value**                    |
|------------------------------------------------|------------------------------|
| new_prop_values.RelyingParty                   | *                            |
| new_prop_values.State                          | 1                            |
| new_prop_values.RememberDevicesNotIssuedBefore | 2018-11-08T19:37:42.7363619Z |


### Trick to extract multiple fields at once
Use a single `jmespath` command to extract multiple fields at once to avoid multiple search command executions:

    ... | jmespath output=ep.*UPN "{target:ExtendedProperties[?Name=='targetUPN'].Value|[0], actor:ExtendedProperties[?Name=='actorUPN'].Value|[0]}"

Note:  This results in `ep.targetUPN` and `ep.actorUPN`, but both are an array with a single string element.  Needs some review.



## AWS CloudTrail

Here is a typical AWS CloudTrail log showing a request to start instances.  In this example, we've started 2 instances at the same time and want to review the state of the instances both before and after the command was processed.  This information is at the top of the JSON payload in a section called `responseElements`.

```json
{
    "eventID": "a9c98349-e77a-4446-8995-d6f360cb9d15",
    "responseElements": {
        "instancesSet": {
            "items": [
                {
                    "previousState": {
                        "name": "stopped",
                        "code": 80
                    },
                    "instanceId": "i-c103dcc9",
                    "currentState": {
                        "name": "pending",
                        "code": 0
                    }
                },
                {
                    "previousState": {
                        "name": "stopped",
                        "code": 80
                    },
                    "instanceId": "i-d206eb9c",
                    "currentState": {
                        "name": "stopped",
                        "code": 80
                    }
                }
            ]
        }
    },
    "requestParameters": {
        "instancesSet": {
            "items": [
                {
                    "instanceId": "i-c103dcc9"
                },
                {
                    "instanceId": "i-d206eb9c"
                }
            ]
        }
    },
    "eventVersion": "1.01",
    "sourceIPAddress": "signin.amazonaws.com",
    "userAgent": "signin.amazonaws.com",
    "eventName": "StartInstances",
    "eventTime": "2018-11-16T19:04:44Z",
    "userIdentity": {
        "sessionContext": {
            "attributes": {
                "creationDate": "2014-05-02T23:59:08Z",
                "mfaAuthenticated": "false"
            }
        },
        "type": "IAMUser",
        "invokedBy": "signin.amazonaws.com",
        "accessKeyId": "KR4ZYM0NK3YN00DL3BOA",
        "arn": "arn:aws:iam::987654321955:user/bitcoin_miner",
        "accountId": "987654321955",
        "userName": "bitcoin_miner",
        "principalId": "AIDAJRC0ULS3NU43KZZEA"
    },
    "requestID": "ee81767e-c8b0-4445-a69b-2c7c052ba32b",
    "eventSource": "ec2.amazonaws.com",
    "awsRegion": "us-west-2"
}
```

The information we are looking for can be extracted with following `jmespath` command:

```
... | jsonformat | jmespath output=response "responseElements.instancesSet.items[].{instanceId: instanceId, state_now:currentState.name, state_before:previousState.name}"
```

This results in the following output:

| response                                                                          |
|-----------------------------------------------------------------------------------|
| `{"state_before": "stopped", "state_now": "pending", "instanceId": "i-c103dcc9"}` |
| `{"state_before": "stopped", "state_now": "stopped", "instanceId": "i-d206eb9c"}` |


Note that since the output is provided in JSON format (because our response is returns an array), multiple values are returned in the same field. Therefore we can use some simple post-processing to split this out into individual fields across 2 events.

Here's an example with post-processing included:

```
...
| jmespath output=response "responseElements.instancesSet.items[].{instanceId: instanceId, state_now:currentState.name, state_before:previousState.name}"
| mvexpand response
| spath input=response
| table instanceId state_now, state_before
```

Output:

| instanceId | state_now | state_before |
|------------|-----------|--------------|
| i-c103dcc9 | pending   | stopped      |
| i-d206eb9c | stopped   | stopped      |

From this output we can clearly see that there's an issue with `i-d206eb9c`, because despite our start request, it's still in the stopped state.

We could also do some other string manipulation directly in JMESPath for human consumption:
```
| jmespath output=response "responseElements.instancesSet.items[].join(': ', [instanceId, join(' -> ', [currentState.name, previousState.name])])"
```
Output:

| response                       |
|--------------------------------|
| i-c103dcc9: pending -> stopped |
| i-d206eb9c: stopped -> stopped |



# Reference Samples

If you'd like to test any of the above examples and `jmespath` expression yourself, you can use these "run-anywhere" commands to load any of the sample events discussed above.

## Sample - Office 365 management
```
| makeresults | eval _raw="{\"Workload\": \"AzureActiveDirectory\", \"RecordType\": 8, \"ActorIpAddress\": \"<null>\", \"CreationTime\": \"2018-11-08T19:37:43\", \"ExtendedProperties\": [{\"Name\": \"actorObjectClass\", \"Value\": \"User\"}, {\"Name\": \"actorUPN\", \"Value\": \"john@example.com\"}, {\"Name\": \"targetUPN\", \"Value\": \"jane@example.com\"}, {\"Name\": \"targetIncludedUpdatedProperties\", \"Value\": \"[\\\"StrongAuthenticationRequirement\\\"]\"}, {\"Name\": \"targetUpdatedProperties\", \"Value\": \"[{\\\"Name\\\":\\\"StrongAuthenticationRequirement\\\",\\\"OldValue\\\":[],\\\"NewValue\\\":[{\\\"RelyingParty\\\":\\\"*\\\",\\\"State\\\":1,\\\"RememberDevicesNotIssuedBefore\\\":\\\"2018-11-08T19:37:42.7363619Z\\\"}]},{\\\"Name\\\":\\\"Included Updated Properties\\\",\\\"OldValue\\\":null,\\\"NewValue\\\":\\\"StrongAuthenticationRequirement\\\"}]\"}], \"UserId\": \"john@example.com\", \"Actor\": [{\"Type\": 5, \"ID\": \"john@example.com\"}], \"AzureActiveDirectoryEventType\": 1, \"Version\": 1, \"ResultStatus\": \"Success\", \"UserKey\": \"1004BFDDDEABBB1F@example.com\", \"Operation\": \"Enable Strong Authentication.\", \"ObjectId\": \"jane@splunko365.com\", \"Id\": \"ec50000f-32cc-40e0-820c-565abcdefe00\", \"Target\": [{\"Type\": 2, \"ID\": \"User\"}, {\"Type\": 5, \"ID\": \"jane@splunko365.com\"}]}" | jsonformat
```

## Sample - AWS CloudTrail
```
| makeresults | eval _raw="{\"eventID\":\"a9c98349-e77a-4446-8995-d6f360cb9d15\",\"responseElements\":{\"instancesSet\":{\"items\":[{\"previousState\":{\"name\":\"stopped\",\"code\":80},\"instanceId\":\"i-c103dcc9\",\"currentState\":{\"name\":\"pending\",\"code\":0}},{\"previousState\":{\"name\":\"stopped\",\"code\":80},\"instanceId\":\"i-d206eb9c\",\"currentState\":{\"name\":\"stopped\",\"code\":80}}]}},\"requestParameters\":{\"instancesSet\":{\"items\":[{\"instanceId\":\"i-c103dcc9\"},{\"instanceId\":\"i-d206eb9c\"}]}},\"eventVersion\":\"1.01\",\"sourceIPAddress\":\"signin.amazonaws.com\",\"userAgent\":\"signin.amazonaws.com\",\"eventName\":\"StartInstances\",\"eventTime\":\"2018-11-16T19:04:44Z\",\"userIdentity\":{\"sessionContext\":{\"attributes\":{\"creationDate\":\"2014-05-02T23:59:08Z\",\"mfaAuthenticated\":\"false\"}},\"type\":\"IAMUser\",\"invokedBy\":\"signin.amazonaws.com\",\"accessKeyId\":\"KR4ZYM0NK3YN00DL3BOA\",\"arn\":\"arn:aws:iam::987654321955:user/bitcoin_miner\",\"accountId\":\"987654321955\",\"userName\":\"bitcoin_miner\",\"principalId\":\"AIDAJRC0ULS3NU43KZZEA\"},\"requestID\":\"ee81767e-c8b0-4445-a69b-2c7c052ba32b\",\"eventSource\":\"ec2.amazonaws.com\",\"awsRegion\":\"us-west-2\"}" | jsonformat
```


# Uses case still under development

Pardon the mess.  These use cases aren't fully developed yet.


## KVstore introspection data

Search:
```
index="_introspection" component=KVStoreServerStats
| table _time _raw
| jmespath output=commands "items(data.metrics.commands) | to_string(@) | from_string(@) | map(&{NAME:[0], value:[1]}, @) | [?value.total>`0`] | map(&merge({NAME:NAME}, value), @)"
| rename _*error as ERROR*
```

Note that in this case, the first value "`<UNKNOWN>`" has a different set of attributes than the others.
