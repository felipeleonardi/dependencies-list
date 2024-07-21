## Digital.ai Hybrid JavaScript Protection - Integrated Hybrid App Protection for Android

### Protection with Digital.ai Android App Protection

#### Requirements for running protect-hybrid-android.py
1. Install and setup licenses for Digital.ai Hybrid JavaScript Protection and Digital.ai Android App Protection products. Refer to relevant Installation Guide documents for more information.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).
3. Set the location of the Android SDK installation as an `ANDROID_HOME` environment variable.

#### Run options
```
-h                            Show help message and exit.
-a <PATH>                     Path to the input APK/AAB file (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js.
-b4a <PATH>                   Path to the blueprint file for protect-android.
-rn                           Flag to indicate that the supplied APK/AAB file is a React Native app.
-ns                           Flag to indicate that the supplied APK/AAB file is a NativeScript app.
-co                           Flag to indicate that the supplied APK/AAB file is a Cordova app.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
-pa <PATH>                    Path to the protect-android binary (default: PATH).
-rvg <ACTION>                 Method invoked if RVG detects script tampering (default: 'doNothing').
                              Available values are 'doNothing', 'fail' and 'my.static.function'.
                              Refer to Digital.ai Android App Protection Developer's Guide for more information.
```
#### Run information
Run `python protect-hybrid-android.py -a <APK/AAB>`. In addition to the default or provided protection configurations, Digital.ai Hybrid JavaScript Protection (Android) will apply a Resource Verification Guard on all JavaScript files found inside the APK.

Once the script finishes, an output directory `APK/AAB.protected.unsigned_protection_output` is created.
Output directory contains the protected `APK/AAB.protected.unsigned-unaligned-unsigned-protected.apk/aab` file. It needs to be aligned and signed before use.

---

### Protection without Digital.ai Android App Protection

#### Requirements for running protect-hybrid-android.py
1. Install and setup license for Digital.ai Hybrid JavaScript Protection product. Refer to Installation Guide document for more information.
2. Install Python 3.4 or later and add `python` to the `PATH` environment variable ([https://www.python.org/downloads](https://www.python.org/downloads)).

#### Run options
```
-h                            Show help message and exit.
-a <PATH>                     Path to the input APK/AAB file (REQUIRED).
-dnp                          Flag to disable protection using Digital.ai Android App Protection (REQUIRED).
-b4h <PATH>                   Path to the blueprint file for protect-hybrid-js.
-rn                           Flag to indicate that the supplied APK/AAB file is a React Native app.
-ns                           Flag to indicate that the supplied APK/AAB file is a NativeScript app.
-co                           Flag to indicate that the supplied APK/AAB file is a Cordova app.
-ph <PATH>                    Path to the protect-hybrid-js binary (default: PATH).
```
#### Run information
Run `python protect-hybrid-android.py -a <APK/AAB> -dnp`. Default or provided protection configuration will be used for Digital.ai Hybrid JavaScript Protection (Android) on a provided APK/AAB file.

Once the script finishes, a working directory will contain both unprotected and protected APK/AAB files. "protected" postfix is added to the filename. It needs to be aligned and signed before use. Unprotected file is left unchanged.
