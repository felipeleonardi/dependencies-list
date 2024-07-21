#!/usr/bin/env python3

import os
import argparse
import subprocess
import shutil
import tempfile
import fnmatch
import json
import tokenize
import zipfile
import time
import sys
import struct
import platform


class TargetType:
    REACT_NATIVE = 1,
    NATIVESCRIPT = 2,
    CORDOVA = 3,
    IONIC = 4,
    DEFAULT = 5

# # # ARGUMENTS # # #


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Apply default protection to React Native, NativeScript, Cordova or Ionic Android apps.')
    parser.add_argument("-a", "--apk", "--aab", metavar="<PATH>",
                        help="Path to the input APK/AAB file (REQUIRED).",
                        required=True)
    parser.add_argument("-b4h", "--blueprint-for-hybrid", metavar="<PATH>",
                        help="Path to the blueprint file for protect-hybrid-js.")
    parser.add_argument("-b4a", "--blueprint-for-android", metavar="<PATH>",
                        help="Path to the blueprint file for protect-android.")
    target_type_group = parser.add_mutually_exclusive_group(required=False)
    target_type_group.add_argument("-rn", "--reactnative",
                        help="Flag to indicate that the supplied APK/AAB file is a React Native app.",
                        action='store_true')
    target_type_group.add_argument("-ns", "--nativescript",
                        help="Flag to Indicate that the supplied APK/AAB file is a NativeScript app.",
                        action='store_true')
    target_type_group.add_argument("-co", "--cordova",
                        help="Flag to Indicate that the supplied APK/AAB file is a Cordova app.",
                        action='store_true')
    target_type_group.add_argument("-io", "--ionic",
                                   help="Flag to Indicate that the supplied APK/AAB file is an Ionic (Capacitor) app.",
                                   action='store_true')

    parser.add_argument("-ph", "--protect-hybrid-js", metavar="<PATH>",
                        help="Path to the protect-hybrid-js binary (default: PATH).")
    parser.add_argument("-pa", "--protect-android", metavar="<PATH>",
                        help="Path to the protect-android binary (default: PATH).")

    parser.add_argument("-rvg", "--rvg-tamper-action", metavar="<ACTION>",
                        help='''Method invoked if RVG detects script tampering (default: 'doNothing').
                        Available values are 'doNothing', 'fail' and 'my.static.function'. 
                        Refer to Digital.ai Android App Protection Developer's Guide for more information.''')

    parser.add_argument("-dnp", "--disable-native-protection",
                        help="Flag to disable protection using Digital.ai Android App Protection.",
                        action='store_true')

    return parser.parse_args()


# # # HybridJavaScriptProtection # # #

class HybridJavaScriptProtection:
    def __init__(self, protect_hybrid_path, application_package_name):
        assert protect_hybrid_path
        self._protect_hybrid_exe = protect_hybrid_path
        self.application_package_name = application_package_name
        self.config_file_path = None
        self.updated_config_file_path = None
        self.input_folder = None
        self.output_folder = None
        self.target_type = TargetType.DEFAULT

    def protect(self):
        self.update_relative_ignorepaths()
        exe_args = [self._protect_hybrid_exe]
        exe_args.extend(self.create_protect_hybrid_arguments())

        return subprocess.call(exe_args)

    def update_relative_ignorepaths(self):
        if self.input_folder and self.config_file_path:
            protect_hybrid_json = load_json_from_file(self.config_file_path)

            targets = get_insensitive(protect_hybrid_json, "targets")
            paths_updated = False
            if targets:
                for target in targets:
                    old_paths = get_insensitive(targets[target], 'ignorePaths')
                    if old_paths:
                        updated_paths = []
                        for path in old_paths:
                            if os.path.exists(path):
                                updated_path = path
                            else:
                                realpath = os.path.realpath(self.input_folder)
                                updated_path = os.path.join(realpath, path.strip("/"))
                            updated_paths.append(updated_path)
                        set_insensitive(targets[target], 'ignorePaths',  updated_paths)
                        paths_updated = True
            if paths_updated:
                self.updated_config_file_path = self.config_file_path + ".updated"
                with open(self.updated_config_file_path, 'w') as output_json_file:
                    json.dump(protect_hybrid_json, output_json_file, indent=2)

    def create_protect_hybrid_arguments(self):
        protect_hybrid_args = []
        if self.config_file_path:
            protect_hybrid_json = load_json_from_file(self.config_file_path)
            if (get_insensitive(get_insensitive(protect_hybrid_json, "globalConfiguration"), "appid") == None and self.application_package_name != None):
                protect_hybrid_args.extend(["-id", self.application_package_name])
            if self.updated_config_file_path:
                protect_hybrid_args.extend(["-b", self.updated_config_file_path])
            else:
                protect_hybrid_args.extend(["-b", self.config_file_path])

        else:
            if self.application_package_name != None:
                protect_hybrid_args.extend(["-id", self.application_package_name])

        if self.input_folder:
            protect_hybrid_args.extend(["-i", self.input_folder])

        if self.output_folder:
            protect_hybrid_args.extend(["-o", self.output_folder])

        if self.target_type == TargetType.REACT_NATIVE:
            protect_hybrid_args.extend(["-t", "reactnative-android"])
        elif self.target_type == TargetType.NATIVESCRIPT:
            protect_hybrid_args.extend(["-t", "nativescript-android"])
        elif self.target_type == TargetType.CORDOVA:
            protect_hybrid_args.extend(["-t", "cordova-android"])
        elif self.target_type == TargetType.IONIC:
            protect_hybrid_args.extend(["-t", "ionic-android"])

        return protect_hybrid_args


# # # Json load with comments removal # # #
SKIP_TOKEN_TYPES = [tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER]

def get_ignored_tokens_count(tokens, current_idx):
    max_idx = len(tokens)
    if current_idx >= max_idx:
        return 0
    token = tokens[current_idx]

    if token.type == tokenize.OP:
        # single line comment skip
        if token.string == '//':
            for idx in range(current_idx + 1, max_idx):
                token = tokens[idx]
                if token.type == tokenize.NL or token.type == tokenize.NEWLINE:
                    return idx - current_idx
            return 0

        # multiline comment skip
        if token.string == '/' and (current_idx < max_idx - 1) and tokens[current_idx + 1].string == '*':
            for idx in range(current_idx + 1, max_idx - 1):
                token = tokens[idx]
                if token.string == '*' and tokens[idx + 1].string == '/':
                    return 2 + idx - current_idx
            return 0
    elif token.type in SKIP_TOKEN_TYPES:
        return 1
    return 0

def is_trailing_comma(tokens, current_idx):
    token = tokens[current_idx]
    max_idx = len(tokens)
    return (token.type == tokenize.OP and
            token.string == ',' and
            ( current_idx + 1 == max_idx or tokens[current_idx + 1].string == "}" or tokens[current_idx + 1].string == "]"))

def remove_comments_and_newlines(tokens):
    output = []
    max_idx = len(tokens)
    idx = 0
    while idx < max_idx:
        count = get_ignored_tokens_count(tokens, idx)
        if (count):
            idx += count
        else:
            output.append(tokens[idx])
            idx += 1
    return output

def remove_trailing_commas(tokens):
    output = []
    for i in range(0, len(tokens)):
        if (not is_trailing_comma(tokens, i)):
            output.append(tokens[i])
    return output

def get_json_as_string(file_name):
    output_string = ""
    with open(file_name, 'rb') as json_file:
        try:
            tokens = list(tokenize.tokenize(json_file.read))
        except Exception as e:
            raise ValueError("Provided blueprint file '" + file_name + "' contains invalid JSON. " + str(e))
        tokens = remove_comments_and_newlines(tokens)
        tokens = remove_trailing_commas(tokens)
        for i in range(0, len(tokens)):
            output_string += tokens[i].string
    return output_string.strip()

def get_insensitive(json, key):
    if (json is None):
        return None
    keys = list(json.keys())
    for i in range(0, len(keys)):
        if (keys[i].lower() == key.lower()):
            return json[keys[i]]
    return None

def set_insensitive(json, key, value):
    if (json is None):
        return None
    keys = list(json.keys())
    for i in range(0, len(keys)):
        if (keys[i].lower() == key.lower()):
            json[keys[i]] = value;
            return;

def load_json_from_file(file_name):
    json_str = get_json_as_string(file_name)
    if len(json_str) == 0:
        raise ValueError("Provided blueprint file '" + file_name +
                         "' is empty. Make sure the file is a non-empty JSON.")
    try:
        return json.loads(json_str)
    except Exception as e:
        raise ValueError("Provided blueprint file '" + file_name + "' contains invalid JSON. " + str(e))

# # # Utils # # #


def remove_dir(dir_name):
    if os.path.isdir(dir_name):
        shutil.rmtree(dir_name)


def get_from_path(file_name):
    """Get `file_name` path searching by PATH environment variable."""
    from shutil import which
    return which(file_name)


def is_on_path(name):
    """Check whether `name` is on PATH."""
    return get_from_path(name) is not None


def validate_executable_path(pathname, executable, executable_description):
    if pathname is not None:
        if not os.path.isfile(pathname):
            raise ValueError(
                'Unable to locate ' + executable_description + ' binary at ' + pathname +
                '. Make sure the path is correct and the file exists.')
        return pathname

    if not is_on_path(executable):
        raise ValueError(
                'Unable to locate ' + executable_description + ' binary in the PATH environment variable. ' +
                'Refer to help to learn how to specify path to it manually.')
    return executable


def file_without_extension(file_name):
    return os.path.splitext(file_name)[0]


def get_files_in_folder(folder, file_patterns, skip_patterns, relative_to=None, recursive=True):
    search_folder = "".join([folder.strip().rstrip("/"), "/"])
    files = []
    if not os.path.isdir(search_folder):
        print("Internal error: " + search_folder + " does not exist.")
    else:
        all_entries = os.listdir(search_folder)
        for item in all_entries:
            path_name = search_folder + item
            if not os.path.islink(path_name):
                if os.path.isdir(path_name) and recursive:
                    process = True
                    for pattern in skip_patterns:
                        if fnmatch.fnmatch(path_name, pattern.rstrip("*")):
                            process = False
                            break
                    if process:
                        files.extend(get_files_in_folder(path_name, file_patterns, skip_patterns,
                                                         relative_to, recursive))
                else:
                    include = True
                    for pattern in skip_patterns:
                        if fnmatch.fnmatch(path_name, pattern):
                            include = False
                            break
                    if include:
                        include = False
                        for pattern in file_patterns:
                            if fnmatch.fnmatch(path_name, pattern):
                                include = True
                                break
                    if include:
                        if relative_to is not None:
                            files.extend([path_name.replace(relative_to, '').lstrip("/")])
                        else:
                            files.extend([path_name])

    return files


def get_tamper_action(tamper_action_type, tamper_action_method=None):
    if tamper_action_type == "method" and tamper_action_method is None:
        raise ValueError("Internal error: RVG tamper action is a method, but method name is not set.")
    tamper_action = {
        "type": tamper_action_type
    }
    if tamper_action_type == "method":
        tamper_action.update({"name": tamper_action_method})
    return tamper_action


def get_verification_guard_idx(resource_verification_guards, rvg_name):
    rvg = None
    index = -1
    for item in resource_verification_guards:
        index += 1
        if "name" in item and rvg_name == item["name"]:
            rvg = item
            break
    if rvg is None:
        index += 1
        rvg = {
            "name": rvg_name,
            "invocationLocations": [{"type": "auto"}],
            "tamperAction": {
                "type": "doNothing"  # "method" or "fail". If "method" then "name" points to method in APK
            },
            "nonTamperAction": {
                "type": "doNothing"
            },
            "files": []
        }
        resource_verification_guards.append(rvg)
    return index


def get_default_protect_android_blueprint_json(isAAB):
    if isAAB:
        return {
            "globalConfiguration": {
                "verbosityLevel": {"global": 1},
                "appAware": {"endpointURL": "auto", "applicationToken": "auto"}
            },
            "guardConfiguration": {
                "controlFlowFlattening": {"safeMode": True},
                "stringEncryption": {},
                "operatorRemoval": {"disable": True},
                "literalHiding": {"disable": True},
                "debugInfoStrip": {
                    "exclude": [
                        {"type": "class", "name": "android.*"},
                        {"type": "class", "name": "androidx.*"}
                    ]
                },
                "logStrip": {"safeMode": True},
                "debuggerDetection": [{
                    "name": "Debugger Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 15,
                        "initialDelay": 0,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "fail"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "rootDetection": [{
                    "name": "Root Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 90,
                        "initialDelay": 1,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "hookDetection": [{
                    "name": "Hook Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 80,
                        "initialDelay": 2,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": { "type": "doNothing"},
                    "detectHookInstalled": False,
                    "detectHookTarget": True,
                    "detectMagiskHiddenModules": True
                }],
                "emulatorDetection": [{
                    "name": "Emulator Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 90,
                        "initialDelay": 5,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"},
                    "detectKoPlayer": False,
                    "detectMEmuPlay": False
                }],
                "dynamicInstrumentationDetection": [{
                    "name": "Dynamic Instrumentation Detection Guard",
                    "frida": {},
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 80,  
                        "initialDelay": 0,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "checksum": [{
                    "name": "Checksum Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 60,
                        "initialDelay": 3,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "fail"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "virtualizationDetection": [{
                    "name": "Virtualization Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 60,
                        "initialDelay": 2,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "virtualControlDetection": [{
                    "name": "Virtual Control Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 10,
                        "initialDelay": 5,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }]
            }}
    else: # APK
        return {
            "globalConfiguration": {
                "verbosityLevel": {"global": 1},
                "appAware": {"endpointURL": "auto", "applicationToken": "auto"}
            },
            "guardConfiguration": {
                "controlFlowFlattening": {"safeMode": True},
                "stringEncryption": {},
                "operatorRemoval": {"disable": True},
                "literalHiding": {"disable": True},
                "debugInfoStrip": {
                    "exclude": [
                        {"type": "class", "name": "android.*"},
                        {"type": "class", "name": "androidx.*"}
                    ]
                },
                "logStrip": {"safeMode": True},
                "debuggerDetection": [{
                    "name": "Debugger Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 15,
                        "initialDelay": 0,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "fail"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "rootDetection": [{
                    "name": "Root Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 90,
                        "initialDelay": 1,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "hookDetection": [{
                    "name": "Hook Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 80,
                        "initialDelay": 2,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": { "type": "doNothing"},
                    "detectHookInstalled": False,
                    "detectHookTarget": True,
                    "detectMagiskHiddenModules": True
                }],
                "emulatorDetection": [{
                    "name": "Emulator Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 90,
                        "initialDelay": 5,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"},
                    "detectKoPlayer": False,
                    "detectMEmuPlay": False
                }],
                "resourceVerification": [{
                    "name": "Resource Verification Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 90,
                        "initialDelay": 0,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "fail"},
                    "nonTamperAction": {"type": "doNothing"},
                    "files": ["resources.arsc", "AndroidManifest.xml"]
                }],
                "checksum": [{
                    "name": "Checksum Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 60,
                        "initialDelay": 3,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "fail"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "dynamicInstrumentationDetection": [{
                    "name": "Dynamic Instrumentation Detection Guard",
                    "frida": {},
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 80,  
                        "initialDelay": 0,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "virtualizationDetection": [{
                    "name": "Virtualization Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 60,
                        "initialDelay": 2,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }],
                "virtualControlDetection": [{
                    "name": "Virtual Control Detection Guard",
                    "invocationLocations": [{
                        "type": "periodic",
                        "interval": 10,
                        "initialDelay": 5,
                        "probability": 100
                    }],
                    "tamperAction": {"type": "doNothing"},
                    "nonTamperAction": {"type": "doNothing"}
                }]
            }}

def add_code_lifting_class_to_android_blueprint(protect_android_blueprint_copy, protect_android_json, target_type, protect_hybrid_blueprint):

    if protect_hybrid_blueprint is None:
        return

    hybrid_blueprint = load_json_from_file(protect_hybrid_blueprint)
    global_config = get_insensitive(hybrid_blueprint, "globalConfiguration")
    guard_configs = get_insensitive(hybrid_blueprint, "guardConfigurations")

    code_lifting_enabled = False
    for config in guard_configs:
        guard_config = get_insensitive(guard_configs, config)
        code_lifting_config = get_insensitive(guard_config, "codeLiftingDetection")
        if code_lifting_config is None:
            continue
        elif type(code_lifting_config) is dict:
            if get_insensitive(code_lifting_config, "enable") is True:
                code_lifting_enabled = True
        elif type(code_lifting_config) is list:
            for cl_config in code_lifting_config:
                if get_insensitive(cl_config, "enable") is True:
                    code_lifting_enabled = True
                    break
        else:
            raise ValueError("Invalid Code Lifting Detection configuration found. Configuration only accepts an object or an array, but a literal has been found.")

    if not code_lifting_enabled:
        return

    app_id = get_insensitive(global_config, "appid")
    target = get_insensitive(global_config, "targettype")

    if sys.platform == "win32":
        with open(os.path.expandvars(R"C:\Users\$USERNAME\AppData\Local\Arxan\ArxanForHybrid\.{}".format(app_id)), 'r') as file:
            vars = json.loads(file.read())
    else:
        with open(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(app_id)), 'r') as file:
            vars = json.loads(file.read())

    if (target_type == TargetType.CORDOVA or target.lower() == 'cordova-android'):
        excludes = [
            {'type': 'method', 'name': 'cordova.plugin.' + vars["ARXAN_PLUGIN"] + '.' + vars["ARXAN_CLASS"] + '.' + vars["ARXAN_FUNCTION"]}
        ]
        includes = []
        targets = [
            'cordova.plugin.' + vars["ARXAN_PLUGIN"] + '.' + vars["ARXAN_CLASS"]
        ]
    elif(target_type == TargetType.IONIC or target.lower() == 'ionic-android'):
        raise ValueError('Code Lifting Detection guard is not implemented for "{}" target.'.format(target))
    elif(target_type == TargetType.NATIVESCRIPT or target.lower() == 'nativescript-android'):
        excludes = [
            {'type': 'class', 'name': vars["ARXAN_PLUGIN"] + '.' + vars["ARXAN_CLASS"]}
        ]
        includes = [
            {'type': 'method', 'name': vars["ARXAN_PLUGIN"] + '.' + vars["ARXAN_CLASS"] + '.p' + vars["ARXAN_FUNCTION"]}
        ]
        targets = [
            vars["ARXAN_PLUGIN"] + '.' + vars["ARXAN_CLASS"]
        ]
    elif(target_type == TargetType.REACT_NATIVE or target.lower() == 'reactnative-android'):
        excludes = [
            {'type': 'class', 'name': 'com.' + vars["ARXAN_PLUGIN"] + '.'  + vars["ARXAN_CLASS"] + 'Module'},
        ]
        includes = [
            {'type': 'method', 'name': 'com.' + vars["ARXAN_PLUGIN"] + '.'  + vars["ARXAN_CLASS"] + 'Module.p' + vars["ARXAN_FUNCTION"]},
        ]
        targets = [
            'com.' + vars["ARXAN_PLUGIN"] + '.'  + vars["ARXAN_CLASS"] + 'Module',
            'com.' + vars["ARXAN_PLUGIN"] + '.'  + vars["ARXAN_CLASS"] + 'Package'
        ]
    else:
        raise ValueError('Unable to find configuration for target: "{}".'.format(target))

    guard_dict = protect_android_json["guardConfiguration"]

    if "classEncryption" in guard_dict:
        classEncryption_guard = guard_dict["classEncryption"]
        if "targets" in classEncryption_guard:
            for target in classEncryption_guard["targets"]:
                if target not in targets:
                    targets.append(target)
        classEncryption_guard["targets"] = targets
        if "disable" in classEncryption_guard:
            classEncryption_guard["disable"] = False
    else:
        guard_dict["classEncryption"] = {
            "disable": False,
            "targets": targets
        }

    if "renaming" in guard_dict:
        renaming_guard = guard_dict["renaming"]
        if "disable" in renaming_guard and renaming_guard["disable"] == False:
            if "exclude" in renaming_guard:
                for exclude in renaming_guard["exclude"]:
                    if exclude not in excludes:
                        excludes.append(exclude)
            renaming_guard["exclude"] = excludes
            if "include" in renaming_guard:
                for include in renaming_guard["include"]:
                    if include not in includes:
                        includes.append(include)
            renaming_guard["include"] = includes

    with open(protect_android_blueprint_copy, 'w') as output_json_file:
        json.dump(protect_android_json, output_json_file, indent=2)

def add_protected_files_to_android_blueprint(tmp_folder, protect_android_blueprint_copy, protect_android_json, isAAB, tamper_action_type=None, tamper_action_method=None):
    # could achieve same result using regex and re.search(pattern, path_name) instead of fnmatch.fnmatch function
    #    include_patterns = [".+(assets).+(index.android.bundle)", ".+(assets).+(.js)"]

    include_patterns = ["*assets*index.android.bundle", "*assets*.js", "*app*.js", ]
    exclude_patterns = []

    print("\tInclude patterns:" + str(include_patterns))
    print("\tExclude patterns:" + str(exclude_patterns))

    if isAAB:
        tmp_folder = tmp_folder[:-5]

    files = get_files_in_folder(tmp_folder,
                                file_patterns=include_patterns,
                                skip_patterns=exclude_patterns,
                                relative_to=tmp_folder,
                                recursive=True)

    print("\tFollowing files will be protected using Resource Verification Guard: ")

    for file in files:
        print("\t   + " + file)

    if len(files) > 0:
        guard_dict = protect_android_json["guardConfiguration"]
        if "resourceVerification" in guard_dict:
            resource_verification_guards = guard_dict["resourceVerification"]
        else:
            resource_verification_guards = []
            guard_dict["resourceVerification"] = resource_verification_guards
        index = get_verification_guard_idx(resource_verification_guards, "Hybrid JavaScript Resource Verification Guard")
        rvg = resource_verification_guards[index]
        for file in rvg["files"]:
            if file not in files:
                files.extend(files)
        rvg["files"] = files
        if tamper_action_type is not None:
            print("\tUsing tamper action: " + tamper_action_type)
            rvg["tamperAction"] = get_tamper_action(tamper_action_type, tamper_action_method)
        with open(protect_android_blueprint_copy, 'w') as output_json_file:
            json.dump(protect_android_json, output_json_file, indent=2)


def get_input(input_string):
    if input_string is not None:
        validated_string = input_string.strip()
        if len(validated_string) > 0:
            return validated_string
    return None

# # # VALIDATION # # #


def validate_file_exists(path):
    if not os.path.exists(path):
        raise ValueError('Unable to locate file: "{}".'.format(path))


def validate_android_home_variable():
    if not os.environ.get('ANDROID_HOME'):
        raise ValueError("ANDROID_HOME variable not set.")

# # # Stdout # # #


def print_section_start(message):
    print('---- ' + message + ' ----\n')


def print_section_end():
    print('')

# # # Zip/APK handling


def decompress_with_report(zip_file: str, extracting_path: str):
    compression_level = {}
    file_list_in_zip_file = []
    renamed_files = {}
    zip_to_scan = zipfile.ZipFile(zip_file)
    file_info = zip_to_scan.NameToInfo
    is_extracting = len(extracting_path) > 0
    for fileName, info in file_info.items():
        if not info.filename.lower() in file_list_in_zip_file:
            file_list_in_zip_file.append(info.filename.lower())
        else:
            name = info.filename[info.filename.rfind('/') + 1:info.filename.rfind('.')]
            new_path = info.filename.replace(name, str(hash(info.filename) % 10 ** 8))
            renamed_files[new_path] = info.filename
            info.filename = new_path

        compression_level[fileName] = info.compress_type
        if is_extracting:
            zip_to_scan.extract(info, extracting_path)

    return compression_level, renamed_files


def compress_dir(out_dir: str, out_zip_file: str, compress_level_table, renamed_files):
    is_windows = platform.system() == "Windows"
    with zipfile.ZipFile(out_zip_file, mode='w') as zf:
        # Iterate over all the files in directory
        for folderName, subfolders, filenames in os.walk(out_dir):
            for filename in filenames:
                # create complete filepath of file in directory
                target_file = os.path.join(folderName, filename)
                file_in_zip = os.path.relpath(target_file, out_dir)
                key = file_in_zip.replace('\\', '/') if is_windows else file_in_zip
                if key in renamed_files:
                    file_in_zip = renamed_files.get(key)
                    if is_windows:
                        file_in_zip = file_in_zip.replace('/', '\\')

                # Add file to zip
                info = zipfile.ZipInfo(file_in_zip, date_time=time.localtime(time.time()))

                in_file = open(target_file, "rb")
                file_content_data = in_file.read()
                in_file.close()

                key = file_in_zip.replace('\\', '/') if is_windows else file_in_zip
                compression_type = compress_level_table.get(key, zipfile.ZIP_DEFLATED)

                info.compress_type = compression_type
                info.create_system = 0
                zf.writestr(info, file_content_data)

    zf.close()


def protect_apk(args, protect_hybrid_path, protect_hybrid_blueprint, apk, protect_android_blueprint, protect_android_path, native_protection,
                tamper_action_type=None, tamper_action_method=None):

    temporary_protect_hybrid_directory = tempfile.mkdtemp()
    temporary_decoded_apk_directory = tempfile.mkdtemp()
    temporary_apk_out_directory = os.path.join(temporary_protect_hybrid_directory, "out")  # Prevent copying exception later

    apk_fullpath = os.path.realpath(apk)
    apk_filename = file_without_extension(apk_fullpath)
    isAAB = apk_fullpath.endswith('.aab')

    try:
        updated_protect_android_blueprint = None
        protect_android_json = None

        if native_protection:
            # Blueprint for Digital.ai Android App Protection creation
            print_section_start('Loading & validating Digital.ai Android App Protection blueprint')
            if protect_android_blueprint is None:
                updated_protect_android_blueprint = "protect-android.blueprint.default.updated"
                protect_android_json = get_default_protect_android_blueprint_json(isAAB)
                print("\tUsing default Digital.ai Android App Protection blueprint ('" + updated_protect_android_blueprint + "')")
            else:
                updated_protect_android_blueprint = protect_android_blueprint + ".updated"
                protect_android_json = load_json_from_file(protect_android_blueprint)
                if "guardConfiguration" not in protect_android_json:
                    raise ValueError("Provided Digital.ai Android App Protection blueprint does not contain " +
                                     "'guardConfiguration' section.")
                print("\tDigital.ai Android App Protection blueprint (" + protect_android_blueprint + ") was loaded successfully.")
            print_section_end()

        # Expand APK
        print_section_start('Extracting')
        compression_report, hash_map = decompress_with_report(apk_fullpath, temporary_decoded_apk_directory)

        if isAAB:
            print('\nDecoded AAB "{}" in the temporary directory "{}".'.format(apk_fullpath, temporary_decoded_apk_directory))
        else:
            print('\nDecoded APK "{}" in the temporary directory "{}".'.format(apk_fullpath, temporary_decoded_apk_directory))

        application_package_name = None

        if isAAB:
            manifest_path = os.path.join(temporary_decoded_apk_directory, 'base/manifest/AndroidManifest.xml')
            application_package_name = AndroidManifestParser(open(manifest_path, 'rb').read()).get_aab_package()
        else:
            manifest_path = os.path.join(temporary_decoded_apk_directory, 'AndroidManifest.xml')
            application_package_name = AndroidManifestParser(open(manifest_path, 'rb').read()).get_apk_package()

        if application_package_name == None:
            print('\nCould not retrieve the package name from extracted AndroidManifest.xml file.')
        print_section_end()

        # Protect with protect-hybrid-js
        print_section_start('Protecting')

        sjs = HybridJavaScriptProtection(protect_hybrid_path=protect_hybrid_path, application_package_name=application_package_name)

        if isAAB:
            shutil.copytree(temporary_decoded_apk_directory, temporary_apk_out_directory)
            sjs.input_folder = os.path.join(temporary_decoded_apk_directory, 'base')
            sjs.output_folder = os.path.join(temporary_apk_out_directory, 'base')
        else:
            sjs.input_folder = temporary_decoded_apk_directory
            sjs.output_folder = temporary_apk_out_directory

        sjs.config_file_path = protect_hybrid_blueprint

        if args.reactnative:
            sjs.target_type = TargetType.REACT_NATIVE
        if args.nativescript:
            sjs.target_type = TargetType.NATIVESCRIPT
        if args.cordova:
            sjs.target_type = TargetType.CORDOVA
        if args.ionic:
            sjs.target_type = TargetType.IONIC

        if sjs.protect() != 0:
            raise ValueError("Failed to apply protect-hybrid-js.")

        print_section_end()

        if native_protection:
            # include protected files to protect-android resource verification guard
            print_section_start('Adding protected files to protect-android blueprint')
            add_code_lifting_class_to_android_blueprint(
                updated_protect_android_blueprint, protect_android_json, sjs.target_type, protect_hybrid_blueprint)
            add_protected_files_to_android_blueprint(
                sjs.output_folder, updated_protect_android_blueprint, protect_android_json, isAAB, tamper_action_type, tamper_action_method)
            print_section_end()

        # Create APK package
        print_section_start("Repacking")
        if isAAB:
            repacked_apk_filename = apk_filename + '.protected.unsigned.aab'
        else:
            repacked_apk_filename = apk_filename + '.protected.unsigned.apk'
        compress_dir(temporary_apk_out_directory, repacked_apk_filename, compression_report, hash_map)
        repacked_apk_path = os.path.realpath(repacked_apk_filename)
        print('\nRepacked the temporary directory "{}" as "{}".'
              .format(temporary_apk_out_directory, repacked_apk_path))
        print_section_end()

        if native_protection:
            # protect-android
            print_section_start("Protecting with protect-android")
            out_dir = os.path.splitext(repacked_apk_filename)[0] + '_protection_output'
            print("Output directory:" + out_dir)
            protect_android_args = [protect_android_path, '--input', repacked_apk_filename, '--output', out_dir]
            if updated_protect_android_blueprint is not None:
                protect_android_args.extend(['--blueprint', updated_protect_android_blueprint])
            subprocess.Popen(protect_android_args).communicate()
            print_section_end()

            # move "AppAware*" to output directory
            print_section_start("Move guard mappings / delete temporary files & folders")
            current_directory = os.getcwd()
            ta_files = get_files_in_folder(current_directory, ["*AppAware*.json"], [], None, False)
            for file in ta_files:
                print("Moving " + file + " to " + out_dir)
                shutil.move(file, out_dir)

            # delete temporary files:
            if os.path.exists(updated_protect_android_blueprint):
                os.remove(updated_protect_android_blueprint)
            if os.path.exists(repacked_apk_filename):
                os.remove(repacked_apk_filename)
            print_section_end()

    except ValueError as inst:
        print_section_end()
        print_section_start('Exception')
        print(inst)
        print_section_end()

    finally:
        if sjs.updated_config_file_path is not None and os.path.exists(sjs.updated_config_file_path):
            os.remove(sjs.updated_config_file_path)

        remove_dir(temporary_decoded_apk_directory)
        remove_dir(temporary_protect_hybrid_directory)
        print_section_start('Cleaning')
        print('Removed the temporary directory "{}".'.format(temporary_protect_hybrid_directory))
        print('Removed the temporary directory "{}".'.format(temporary_decoded_apk_directory))
        print_section_end()

class AndroidManifestParser:

    def __init__(self, raw_buffer):
        self.buffer = raw_buffer
        self.index = 0
        self.read(8)

    def read(self, size):
        buffer = self.buffer[self.index: self.index + size]
        self.index += size
        return buffer

    def process(self):
        event = -1
        self.attributes = []
        while True:
            type = struct.unpack('<L', self.read(4))[0]
            if type == 0x00080180: # Resource type
                self.read(4 * int(struct.unpack('<L', self.read(4))[0]/4-2))
                continue
            self.read(12)
            if type == 0x00100100 or type == 0x00100101: # Namespace types
                self.read(8)
            if type == 0x00100102: # Start tag type
                self.read(12)
                attribute_count = struct.unpack('<L', self.read(4))[0]
                self.read(4)
                for i in range(0, (attribute_count & 0xFFFF) * 5):
                    self.attributes.append(struct.unpack('<L', self.read(4))[0])
                for i in range(3, len(self.attributes), 5):
                    self.attributes[i] = (self.attributes[i]>>24)
                event = type
                break
        return event

    def get_apk_package(self):
        self.process_strings()
        while True:
            if self.process() == 0x00100102: # Start tag type
                for i in range(0, int(len(self.attributes) / 5)):
                    if self.get_raw(self.attributes[i * 5 + 1]) == "package":
                        return self.get_raw(self.attributes[i * 5 + 2])
        return None


    # Online protobuf decoder: https://protogen.marcgravell.com/decode
    # Encoding and other protobuf docs: https://developers.google.com/protocol-buffers/docs/encoding
    def get_aab_package(self):
        package_attribute_index = self.buffer.find(bytearray("package", 'ascii'))
        package_attribute_len = self.buffer[package_attribute_index - 1]
        package_attribute_id = self.buffer[package_attribute_index - 2]

        package_attribute_wire_type = package_attribute_id & 0x3

        # We assume 'package' attribute will go before the package name
        if package_attribute_len == 7 and package_attribute_wire_type == 0x2:

            package_name_index = package_attribute_index + package_attribute_len + 2
            package_name_id = self.buffer[package_name_index - 2]
            package_name_len = self.buffer[package_name_index - 1]

            package_name_wire_type = package_name_id & 0x3

            if package_name_wire_type == 0x2:
                application_package_name = self.buffer[package_name_index: package_name_index + package_name_len]
                return application_package_name.decode()
        return None

    def process_strings(self):
        self.string_offsets = []
        self.strings = []
        self.read(4)
        chunk_size = struct.unpack('<L', self.read(4))
        string_count = struct.unpack('<L', self.read(4))
        style_offset_count = struct.unpack('<L', self.read(4))
        self.read(4)
        strings_offset = struct.unpack('<L', self.read(4))
        styles_offset = struct.unpack('<L', self.read(4))

        for i in range(0, string_count[0]):
            self.string_offsets.append(struct.unpack('<L', self.read(4)))
        self.read(4 * style_offset_count[0])

        size = chunk_size[0] - strings_offset[0]
        if styles_offset[0] != 0:
            size = styles_offset[0] - strings_offset[0]
        if (size % 4) != 0:
            pass

        for i in range(0, int(size / 4)):
            self.strings.append(struct.unpack('<L', self.read(4)))

        if styles_offset[0] != 0:
            size = chunk_size[0] - strings_offset[0]
            if (size % 4) != 0:
                pass
            self.read(4 * (size / 4))

    def get_raw(self, index):
        offset = self.string_offsets[ index ][0]
        length = self.get_short(self.strings, offset)
        data = ""

        while length > 0:
            offset += 2
            data += chr(self.get_short(self.strings, offset))
            if data[-1] == "&":
                data = data[:-1]
            length -= 1
        return data

    def get_short(self, array, offset):
        value = array[int(offset / 4)][0]
        if (int((offset % 4)) / 2) == 0:
            return value & 0xFFFF
        else:
            return value >> 16
        
# # # MAIN # # #


def execute():
    print('Digital.ai Hybrid JavaScript Protection (Android) - start')

    args = parse_cli_args()

    protect_android_path = get_input(args.protect_android)
    protect_hybrid_path = get_input(args.protect_hybrid_js)
    protect_hybrid_config_path = get_input(args.blueprint_for_hybrid)
    protect_android_config = get_input(args.blueprint_for_android)

    tamper_action_type = get_input(args.rvg_tamper_action)
    tamper_action_method = None
    if tamper_action_type is None:
        tamper_action_type = "doNothing"
    else:
        if tamper_action_type != "fail" and tamper_action_type != "doNothing":
            tamper_action_method = tamper_action_type
            tamper_action_type = "method"

    native_protection = not args.disable_native_protection

    # initial validation

    try:
        if native_protection:
            validate_android_home_variable()
            protect_android_path = validate_executable_path(protect_android_path, "secure-dex", "Digital.ai Android App Protection")
        else:
            protect_android_path = None

        validate_file_exists(args.apk)
        if protect_hybrid_config_path is not None:
            validate_file_exists(protect_hybrid_config_path)
        if protect_android_config is not None:
            validate_file_exists(protect_android_config)
        protect_hybrid_path = validate_executable_path(protect_hybrid_path, "protect-hybrid-js", "Digital.ai Hybrid JavaScript Protection")
    except Exception as e:
        raise SystemExit(e)

    # Extract / protect-hybrid-js / Archive / protect-android / Clean
    protect_apk(args,
                protect_hybrid_path,
                protect_hybrid_config_path,
                args.apk,
                protect_android_config,
                protect_android_path,
                native_protection,
                tamper_action_type,
                tamper_action_method)

    print('Digital.ai Hybrid JavaScript Protection (Android) - finish')


if __name__ == "__main__":
    execute()
