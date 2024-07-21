## Digital.ai Hybrid JavaScript Protection - Code Lifting Detection Plugin

### Plugin Installation

#### Requirements for running protect-hybrid-install-plugin.py
1. Preserve the script directory structure as it exists in the protect-hybrid-js installation archive.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
3. Install `tokenize` Python module.
4. If protecting iOS platform, install `pbxproj` Python module.

#### Run options
```
-h                            Show help message and exit.
-p <PATH>                     Path to the project directory (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js (REQUIRED).
-ph <PATH>                    Path to the protect-hybrid-js binary.
-pa <PATH>                    Path to Digital.ai Apple Native Protection root folder.
-t                            Xcode targets to be updated.
-aap <PATH>                   Path to add-arxan.py script.
-acfg <PATH>                  Path to configuration json file used by add-arxan.py script. Default would be created if not provided.
```
#### Run information
##### Android
Run `python3 hybrid-install-plugin.py -p <PROJECT_DIRECTORY> -b4h <BLUEPRINT_PATH>`. 

The plugin will be installed to the Android platform. 
The application can then be protected with Digital.ai Hybrid JavaScript Protection and Digital.ai Android App Protection.
##### iOS
Run `python3 hybrid-install-plugin.py -p <PROJECT_DIRECTORY> -b4h <BLUEPRINT> -t <TARGETS> -aap <ADD_ARXAN_SCRIPT> -acfg <ADD_ARXAN_CONFIG>`. 

The plugin will be installed to the iOS platform and the Xcode project will be updated to protect the application with Digital.ai Hybrid JavaScript Protection and Digital.ai Apple Native Protection at build time.

---