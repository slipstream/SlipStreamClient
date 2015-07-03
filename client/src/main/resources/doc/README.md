
## Update the examples from Nuvla&trade;
To fetch the current version of the examples from Nuvla&trade;, clone this repository and then execute the following script into this directory:
```bash
#!/bin/env bash -x

ss-module-download -u <username> -p <password> \
  --flat \
  --remove-cloud-specific \
  --remove-group-members \
  --reset-commit-message \
  examples
```

`<username>` and `<password>` should be valid credentials for the Nuvla&trade; service.


