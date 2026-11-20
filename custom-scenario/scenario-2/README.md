A custom RAMSES scenario with things happening in quick succession.

# Using this scenario
## Prerequisites

Need:
* docker
* gradle (version 8.x)
* java (version <= 21)

## Building and running
Build with:

1. `gradle build`
2. `docker build -t custom-scenario2 .`

Then run:

```docker run -P -d --network ramses-sas-net custom-scenario2```

Copied / adapted from the `managed-system/rest-client` in https://zenodo.org/records/10400821.
