#!/usr/bin/env python3

import os
import argparse
import sys

import json
import tokenize

def ERROR(msg):
    print("\n[ERROR]: " + msg + "\n")
    sys.exit(-1)

class Blueprint:
    def __init__(self):
        self.SKIP_TOKEN_TYPES = [tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER]

    def get_ignored_tokens_count(self, tokens, current_idx):
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

        elif token.type in self.SKIP_TOKEN_TYPES:
            return 1

        return 0


    def is_trailing_comma(self, tokens, current_idx):
        token = tokens[current_idx]
        max_idx = len(tokens)
        return (token.type == tokenize.OP and
                token.string == ',' and
                ( current_idx + 1 == max_idx or tokens[current_idx + 1].string == "}" or tokens[current_idx + 1].string == "]"))


    def remove_comments_and_newlines(self, tokens):
        output = []
        max_idx = len(tokens)
        idx = 0
        while idx < max_idx:
            count = self.get_ignored_tokens_count(tokens, idx)
            if (count):
                idx += count
            else:
                output.append(tokens[idx])
                idx += 1
        return output


    def remove_trailing_commas(self, tokens):
        output = []
        for i in range(0, len(tokens)):
            if (not self.is_trailing_comma(tokens, i)):
                output.append(tokens[i])
        return output


    def get_json_as_string(self, file_name):
        output_string = ""
        if (not os.path.isfile(file_name)):
            ERROR("Unable to locate protect-hybrid-js blueprint at " + file_name + ". Make sure the path is correct and the file exists.")
        with open(file_name, 'rb') as json_file:
            try:
                tokens = list(tokenize.tokenize(json_file.read))
            except Exception as e:
                ERROR("Provided blueprint file '" + file_name + "' contains invalid JSON: " + str(e))
            tokens = self.remove_comments_and_newlines(tokens)
            tokens = self.remove_trailing_commas(tokens)
            for i in range(0, len(tokens)):
                output_string += tokens[i].string
        return output_string.strip()

    def load_hybrid_blueprint(self, file_name):
        json_str = self.get_json_as_string(file_name)
        if len(json_str) == 0:
            ERROR("Provided blueprint file '" + file_name +
                  "' is empty. Make sure the file is a non-empty JSON.")
        try:
            return json.loads(json_str)
        except Exception as e:
            ERROR("Provided blueprint file '" + file_name + "' contains invalid JSON: " + str(e))

    def get_insensitive(self, json, key):
        if (json is None):
            return None
        keys = list(json.keys())
        for i in range(0, len(keys)):
            if (keys[i].lower() == key.lower()):
                return json[keys[i]]
        return None


def get_target_type(blueprint_for_hybrid):
    bp = Blueprint()
    ph_bp_json = bp.load_hybrid_blueprint(blueprint_for_hybrid)
    glob_section = bp.get_insensitive(ph_bp_json, "globalConfiguration")
    if glob_section is not None:
        return bp.get_insensitive(glob_section, "targetType")
    return None


# # # ARGUMENTS # # #

def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Setup React Native with Hermes application for Digital.ai Hybrid JavaScript Protection.')
    parser.add_argument("-p", "--project", metavar="<PATH>",
                        help="Path to React Native directory (REQUIRED).",
                        required=True)
    parser.add_argument("--blueprint-for-hybrid-android", metavar="<PATH>",
                        help="Path to the blueprint file for protect-hybrid-js Android target.")
    parser.add_argument("--blueprint-for-hybrid-ios", metavar="<PATH>",
                        help="Path to the blueprint file for protect-hybrid-js iOS target.")
    parser.add_argument("-ph", "--protect-hybrid-js", metavar="<PATH>",
                        help="Path to the protect-hybrid-js binary (default: PATH).")
    parser.add_argument("-r", "--remove",
                        help="Flag to remove protection script from React Gradle.",
                        action='store_true')
    return parser.parse_args()

# # # UTILS # # #


def get_input(input_string):
    if input_string is not None:
        validated_string = input_string.strip()
        if len(validated_string) > 0:
            return validated_string
    return None


def get_from_path(file_name):
    """Get `file_name` path searching by PATH environment variable."""
    from shutil import which
    return which(file_name)


def validate_file_exists(path):
    if not os.path.exists(path):
        raise ValueError(create_error_message('Unable to locate file: "{}".'.format(path)))


def validate_executable_path(pathname, executable, executable_description):
    if pathname is not None:
        if not os.path.isfile(pathname):
            raise ValueError(
                create_error_message('Unable to locate ' + executable_description + ' binary at ' + pathname +
                                     '. Make sure the path is correct and the file exists.'))
        return pathname

    if not get_from_path(executable):
        raise ValueError(
            create_error_message('Unable to locate ' + executable_description + ' binary in the PATH environment variable. ' +
                                 'Refer to help to learn how to specify path to it manually.'))
    return get_from_path(executable)


def create_info_message(message):
    return '[INFO]: {}'.format(message)


def create_error_message(message):
    return '[ERROR]: {}'.format(message)


# # # GRADLE UPDATE # # #


def generate_android_hermes_protection_script(protect_hybrid_path, protect_hybrid_android_blueprint):
    script = """
    // Digital.ai Hybrid JavaScript Protection injected script - start
    val rootFile = root.get().asFile
    val protectedFile = File("${bundleFile}.ph")
    val protectCommand = windowsAwareCommandLine(
        "PROTECT_HYBRID", 
        TARGET_TYPE BLUEPRINT 
        "-i", bundleFile.cliPath(rootFile),
        "-o", protectedFile.cliPath(rootFile))
    runCommand(protectCommand)
    protectedFile.moveTo(bundleFile)
    // Digital.ai Hybrid JavaScript Protection injected script - end
    """
    adjusted_hybrid_path = protect_hybrid_path.replace("\\", "\\\\")
    script = script.replace("PROTECT_HYBRID", adjusted_hybrid_path)
    adjusted_blueprint_path = protect_hybrid_android_blueprint.replace("\\", "\\\\")
    script = script.replace("BLUEPRINT", '"-b", "{}",'.format(adjusted_blueprint_path))
    blueprint_target = get_target_type(protect_hybrid_android_blueprint)
    target_type = '"-t", "reactnative-android",'
    if blueprint_target is not None:
        if blueprint_target.lower() != "reactnative-android":
            print(create_error_message('Wrong target type used in provided Android blueprint. Set the target type to "reactnative-android".'))
            sys.exit(1)
        target_type = ""
    return script.replace("TARGET_TYPE", target_type)


def update_gradle(react_gradle_path, protect_hybrid_path, protect_hybrid_android_blueprint_path):
    with open(react_gradle_path, 'r+') as react_file:
        file_data = react_file.read()

    script = generate_android_hermes_protection_script(protect_hybrid_path, protect_hybrid_android_blueprint_path)
    if file_data.find("Digital.ai Hybrid JavaScript Protection") < 0:
        with open(react_gradle_path, 'w+') as react_file:
            insert_index = file_data.find("runCommand(bundleCommand)")
            if insert_index < 0:
                print(create_error_message('Unable to locate position in React Gradle for script injection. Please contact support@digital.ai for help resolving this error.'))
                sys.exit(1)
            file_data = file_data[:insert_index + len("runCommand(bundleCommand)")] + script + file_data[insert_index + len("runCommand(bundleCommand)"):]
            react_file.write(file_data)
        print(create_info_message('Injected protection script to React Gradle.'))
    else:
        if file_data.find(script) < 0:
            script_start_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - start")
            script_end_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - end")
            if script_start_index < 0 or script_end_index < 0:
                print(create_error_message('Injected script in React Gradle was not found. Please contact support@digital.ai for help resolving this error.'))
                sys.exit(1)
            with open(react_gradle_path, 'w+') as react_file:
                file_data = file_data[:script_start_index] + script + file_data[script_end_index + len("// Digital.ai Hybrid JavaScript Protection injected script - finish"):]
                react_file.write(file_data)
            print(create_info_message('Protection script in React Gradle was updated with new configurations.'))
        else:
            print(create_info_message('Protection script with the same configurations was found, no updates were made to React Gradle.'))


def remove_gradle_script(react_gradle_path):
    with open(react_gradle_path, 'r+') as react_file:
        file_data = react_file.read()

    script_start_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - start")
    script_end_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - end")
    if script_start_index < 0 or script_end_index < 0:
        return

    with open(react_gradle_path, 'w+') as react_file:
        file_data = file_data[:script_start_index] + file_data[script_end_index + len("// Digital.ai Hybrid JavaScript Protection injected script - finish"):]
        react_file.write(file_data)
    print(create_info_message('Protection script was removed from React Gradle.'))


# # # XCODE UPDATE # # #


def generate_xcode_hermes_protection_script(protect_hybrid_path, protect_hybrid_ios_blueprint):
    script = """# Digital.ai Hybrid JavaScript Protection injected script - start
if [ -f "PROTECT_HYBRID" ]; then
    PROTECT_HYBRID TARGET_TYPE -i "$BUNDLE_FILE" -o "$BUNDLE_FILE".ph BLUEPRINT
    [ $? -eq 0 ] || exit 2
    mv "$BUNDLE_FILE".ph "$BUNDLE_FILE"
    [ $? -eq 0 ] || exit 2
else 
    echo "Unable to locate Digital.ai Hybrid JavaScript Protection binary at PROTECT_HYBRID. Make sure the path is correct and the file exists."
    exit 2
fi
# Digital.ai Hybrid JavaScript Protection injected script - end
"""
    adjusted_hybrid_path = protect_hybrid_path.replace("\\", "\\\\")
    script = script.replace("PROTECT_HYBRID", adjusted_hybrid_path)
    target_type = "-t reactnative-ios"

    adjusted_blueprint_path = protect_hybrid_ios_blueprint.replace("\\", "\\\\")
    script = script.replace("BLUEPRINT", '-b {}'.format(adjusted_blueprint_path))
    blueprint_target = get_target_type(protect_hybrid_ios_blueprint)
    if blueprint_target is not None:
        if blueprint_target.lower() != "reactnative-ios":
            print(create_error_message('Wrong target type used in provided iOS blueprint. Set the target type to "reactnative-ios".'))
            sys.exit(1)
        target_type = ""
    return script.replace("TARGET_TYPE", target_type)


def update_xcode(react_xcode_path, protect_hybrid_path, protect_hybrid_ios_blueprint):
    with open(react_xcode_path, 'r+') as react_file:
        file_data = react_file.read()

    script = generate_xcode_hermes_protection_script(protect_hybrid_path, protect_hybrid_ios_blueprint)
    if file_data.find("Digital.ai Hybrid JavaScript Protection") < 0:
        with open(react_xcode_path, 'w+') as react_file:
            insert_index = file_data.find('"$HERMES_CLI_PATH" -emit-binary')
            if insert_index < 0:
                print(create_error_message('Unable to locate position in React Xcode Script for script injection. Please contact support@digital.ai for help resolving this error.'))
                sys.exit(1)
            file_data = file_data[:insert_index] + script + file_data[insert_index:]
            react_file.write(file_data)
        print(create_info_message('Injected protection script to React Xcode Script.'))
    else:
        if file_data.find(script) < 0:
            script_start_index = file_data.find("# Digital.ai Hybrid JavaScript Protection injected script - start")
            script_end_index = file_data.find("# Digital.ai Hybrid JavaScript Protection injected script - end")
            if script_start_index < 0 or script_end_index < 0:
                print(create_error_message('Injected script in React Xcode Script was not found. Please contact support@digital.ai for help resolving this error.'))
                sys.exit(1)
            with open(react_xcode_path, 'w+') as react_file:
                file_data = file_data[:script_start_index] + script + file_data[script_end_index + len("// Digital.ai Hybrid JavaScript Protection injected script - finish"):]
                react_file.write(file_data)
            print(create_info_message('Protection script in React Xcode Script was updated with new configurations.'))
        else:
            print(create_info_message('Protection script with the same configurations was found, no updates were made to React Xcode Script.'))


def remove_xcode_script(react_gradle_path):
    with open(react_gradle_path, 'r+') as react_file:
        file_data = react_file.read()

    script_start_index = file_data.find("# Digital.ai Hybrid JavaScript Protection injected script - start")
    script_end_index = file_data.find("# Digital.ai Hybrid JavaScript Protection injected script - end")
    if script_start_index < 0 or script_end_index < 0:
        return

    with open(react_gradle_path, 'w+') as react_file:
        file_data = file_data[:script_start_index] + file_data[script_end_index + len("# Digital.ai Hybrid JavaScript Protection injected script - finish"):]
        react_file.write(file_data)
    print(create_info_message('Protection script was removed from React Xcode Script.'))


# # # MAIN # # #


def execute():
    print('Digital.ai Hybrid JavaScript Protection React Native Hermes Set-up - start\n')

    args = parse_cli_args()

    if os.path.exists(gradle_plugin := os.path.join(get_input(args.project), "node_modules/@react-native/gradle-plugin")):
        react_gradle_path = os.path.realpath(os.path.join(gradle_plugin, "src/main/kotlin/com/facebook/react/tasks/BundleHermesCTask.kt"))
    else:
        react_gradle_path = os.path.realpath(os.path.join(get_input(args.project), "node_modules/react-native-gradle-plugin/src/main/kotlin/com/facebook/react/tasks/BundleHermesCTask.kt"))

    react_xcode_path = os.path.realpath(os.path.join(get_input(args.project), "node_modules/react-native/scripts/react-native-xcode.sh"))
    protect_hybrid_path = get_input(args.protect_hybrid_js)

    if not args.blueprint_for_hybrid_android and not args.blueprint_for_hybrid_ios:
        print(create_error_message('No protection blueprints were provided. Please specify "--blueprint-for-hybrid-android" and/or "--blueprint-for-hybrid-ios".'))
        sys.exit(1)

    protect_hybrid_android_blueprint_path = None
    protect_hybrid_ios_blueprint_path = None

    if args.blueprint_for_hybrid_android:
        protect_hybrid_android_blueprint_path = get_input(args.blueprint_for_hybrid_android)
    if args.blueprint_for_hybrid_ios:
        protect_hybrid_ios_blueprint_path = get_input(args.blueprint_for_hybrid_ios)

    if protect_hybrid_path is not None:
        protect_hybrid_path = os.path.realpath(protect_hybrid_path)
    if protect_hybrid_android_blueprint_path is not None:
        protect_hybrid_android_blueprint_path = os.path.realpath(protect_hybrid_android_blueprint_path)
    if protect_hybrid_ios_blueprint_path is not None:
        protect_hybrid_ios_blueprint_path = os.path.realpath(protect_hybrid_ios_blueprint_path)

    try:
        if protect_hybrid_android_blueprint_path is not None and not args.remove:
            validate_file_exists(react_gradle_path)
            validate_file_exists(protect_hybrid_android_blueprint_path)
        if protect_hybrid_ios_blueprint_path is not None and not args.remove:
            validate_file_exists(react_xcode_path)
            validate_file_exists(protect_hybrid_ios_blueprint_path)
        protect_hybrid_path = validate_executable_path(protect_hybrid_path, "protect-hybrid-js", "Digital.ai Hybrid JavaScript Protection")
    except Exception as e:
        raise SystemExit(e)

    if args.remove:
        remove_gradle_script(react_gradle_path)
        remove_xcode_script(react_xcode_path)
    else:
        if protect_hybrid_android_blueprint_path is not None:
            update_gradle(react_gradle_path, protect_hybrid_path, protect_hybrid_android_blueprint_path)
            print(create_info_message("Hermes protection on Android does not support the following guards: Checksum, Hook Detection and Minification. Please make sure to disable them for the protected app to function as expected."))
        if protect_hybrid_ios_blueprint_path is not None:
            update_xcode(react_xcode_path, protect_hybrid_path, protect_hybrid_ios_blueprint_path)
            print(create_info_message("Hermes protection on iOS does not support the following guards and features: Checksum, Script Verification, Hook Detection, Minification and infiniteDebuggerLoop options of Debug Detection. Please make sure to disable them for the protected app to function as expected."))

    print('\nDigital.ai Hybrid JavaScript Protection React Native Hermes Set-up - finish')


if __name__ == "__main__":
    execute()
