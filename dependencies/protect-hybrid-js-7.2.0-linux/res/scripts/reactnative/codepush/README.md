## Digital.ai Hybrid JavaScript Protection - React Native CodePush Set-Up

#### Requirements for running protect-hybrid-codepush-setup.py
1. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
2. Install `appcenter-cli` ([https://github.com/microsoft/appcenter-cli](https://github.com/microsoft/appcenter-cli)).
#### Run options
```
-h                            Show help message and exit.
-ac <PATH>                    Path to the appcenter directory (REQUIRED).
-p <PATH>                     Path to the react-native project directory (REQUIRED).
-b4a <PATH>                   Path to the blueprint file for protect-hybrid-js on Android.
-b4i <PATH>                   Path to the blueprint file for protect-hybrid-js on iOS.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
-r                            Remove protection script from React Gradle.
```
#### Run information
Run `python3 protect-hybrid-codepush-setup.py -ac <appcenter_directory> -p <project_directory>`.
At least one of the blueprints are required. Protection will be applied only to the platforms that had their blueprints provided.
If a default protection is required, provide a `default` value (case-sensitive) to the blueprint option, i.e. `-b4a default` or `-b4i default`

Once the script finishes, the CodePush is updated to protect the bundle before CodePush release and protection hook `protect-hybrid-hook.js` is added to project directory.
To update the protection configurations run the script again with new configurations.

* If using both Hermes and CodePush at the same time, please use only CodePush set-up script. 
---
