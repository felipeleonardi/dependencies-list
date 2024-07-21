## Digital.ai Hybrid JavaScript Protection - React Native Hermes Set-up

#### Requirements for running protect-hybrid-hermes-setup.py
1. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).

#### Run options
```
-h                                                      Show help message and exit.
-p <PATH>                                               Path to the react-native project directory (REQUIRED).
--blueprint-for-hybrid-android <PATH>                   Path to the blueprint file for protect-hybrid-js Android target.
--blueprint-for-hybrid-ios <PATH>                       Path to the blueprint file for protect-hybrid-js iOS target.
-ph <PATH>                                              Path to the protect-hybrid-js binary (default: PATH).
-r                                                      Remove protection script from React Native.
```
#### Run information
Run:
```
python3 protect-hybrid-hermes-setup.py -p <project_directory> --blueprint-for-hybrid-android <blueprint_path> --blueprint-for-hybrid-ios <blueprint_path>
```

Blueprint has to be provided for at least one of the platforms. Protection will be integrated only to the platforms that had blueprints specified.

Once the script finishes, the React Native is updated to protect the bundle before Hermes is used on it.
To update the protection configurations run the script again with new configurations.

* If using both Hermes and CodePush at the same time, please use only the CodePush set-up script. 
