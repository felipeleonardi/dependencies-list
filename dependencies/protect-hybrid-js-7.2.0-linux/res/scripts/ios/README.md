## Digital.ai Hybrid JavaScript Protection - Integrated Hybrid App Protection for iOS

### Protection with Digital.ai Apple Native Protection (Xcarchive)

#### Requirements for running protect-hybrid-ios.py
1. Install and setup licenses for Digital.ai Hybrid JavaScript Protection and Digital.ai Apple Native Protection products. Refer to relevant Installation Guide documents for more information.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
3. Make sure your environment has ENSUREIT variable set. Alternativelly you can provide path to Digital.ai Apple Native Protection root folder via input parameter.
4. Install Xcode 11 or later

#### Run options
```
-h                            Show help message and exit.
-xc <PATH>                    Path to *.xcarchive file (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js.
-b4a <PATH>                   Path to the blueprint file for protect-apple. (post build protection blueprint).
-rn                           Flag to indicate that the supplied file is a React Native app.
-ns                           Flag to indicate that the supplied file is a NativeScript app.
-co                           Flag to indicate that the supplied file is a Cordova app.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
-pa <PATH>                    Path to the Digital.ai Apple Native Protection root folder (default: ENVIRONMENT).
```
#### Run information
Run `python protect-hybrid-ios.py -xc <XCARCHIVE>`. In addition to the default or provided protection configurations, Digital.ai Hybrid JavaScript Protection (iOS) will call Digital.ai Apple Native Protection protection for given archive.

Once the script finishes, initial archive folder will contain both unprotected and protected xcarchive files. "Protected" prefix is added to filename. Unprotected file is left unchanged.

---

### Protection without Digital.ai Apple Native Protection (Xcarchive)

#### Requirements for running protect-hybrid-ios.py
1. Install and setup license for Digital.ai Hybrid JavaScript Protection product. Refer to Installation Guide document for more information.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
4. Install Xcode 10 or later

#### Run options
```
-h                            Show help message and exit.
-xc <PATH>                    Path to *.xcarchive file (REQUIRED).
-dnp                          Flag to disable protection using Digital.ai Apple Native Protection (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js.
-rn                           Flag to indicate that the supplied file is a React Native app.
-ns                           Flag to indicate that the supplied file is a NativeScript app.
-co                           Flag to indicate that the supplied file is a Cordova app.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
```
#### Run information
Run `python protect-hybrid-ios.py -xc <XCARCHIVE> -dnp`. Default or provided protection configuration will be used for Digital.ai Hybrid JavaScript Protection (iOS) on a provided archive.

Once the script finishes, initial archive folder will contain both unprotected and protected xcarchive files. "Protected" prefix is added to filename. Unprotected file is left unchanged.

---

### Protection with Digital.ai Apple Native Protection (IPA)

IPA file protection with Digital.ai Apple Native Protection is not currently supported.

---

### Protection without Digital.ai Apple Native Protection (IPA)

#### Requirements for running protect-hybrid-ios.py
1. Install and setup license for Digital.ai Hybrid JavaScript Protection product. Refer to Installation Guide document for more information.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
4. Install Xcode 10 or later

#### Run options
```
-h                            Show help message and exit.
-i <PATH>                     Path to *.ipa file (REQUIRED).
-dnp                          Flag to disable protection using Digital.ai Apple Native Protection (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js.
-rn                           Flag to indicate that the supplied file is a React Native app.
-ns                           Flag to indicate that the supplied file is a NativeScript app.
-co                           Flag to indicate that the supplied file is a Cordova app.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
```
#### Run information
Run `python protect-hybrid-ios.py -i <IPA> -dnp`. Default or provided protection configuration will be used for Digital.ai Hybrid JavaScript Protection (iOS) on a provided IPA file.

Once the script finishes, a working directory will contain both unprotected and protected IPA files. "protected" postfix is added to the filename. It needs to be signed before use. Unprotected file is left unchanged.
