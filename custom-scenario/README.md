A custom longer RAMSES scenario.

# Using this scenario
## Prerequisites

Need:
* docker
* gradle (version 8.x)
* java (version <= 21)

## Building and running
Build with:

1. `gradle build`
2. `docker build -t custom-scenario .`

Then run:

```docker run -P -d --network ramses-sas-net custom-scenario```

Copied / adapted from the `managed-system/rest-client` in https://zenodo.org/records/10400821.
