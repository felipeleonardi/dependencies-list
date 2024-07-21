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
    if blueprint_for_hybrid is None or blueprint_for_hybrid == "default":
        return None
    bp = Blueprint()
    ph_bp_json = bp.load_hybrid_blueprint(blueprint_for_hybrid)
    glob_section = bp.get_insensitive(ph_bp_json, "globalConfiguration")
    if glob_section is not None:
        return bp.get_insensitive(glob_section, "targetType")
    return None

# # # ARGUMENTS # # #
def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Setup React Native with CodePush application for Digital.ai Hybrid JavaScript Protection.')
    parser.add_argument("-p", "--project", metavar="<PATH>",
                        help="Path to React Native project (REQUIRED).",
                        required=True)
    parser.add_argument("-ac", "--appcenter", metavar="<PATH>",
                        help="Path to appcenter-cli (when not provided, path for global NPM packages used).")
    parser.add_argument("-b4a", "--blueprint-for-android", metavar="<PATH>",
                        help="Path to the blueprint file for protect-hybrid-js on Android.")
    parser.add_argument("-b4i", "--blueprint-for-ios", metavar="<PATH>",
                        help="Path to the blueprint file for protect-hybrid-js on iOS.")
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


def is_on_path(name):
    """Check whether `name` is on PATH."""
    return get_from_path(name) is not None


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

    if not is_on_path(executable):
        raise ValueError(
            create_error_message('Unable to locate ' + executable_description + ' binary in the PATH environment variable. ' +
                                 'Refer to help to learn how to specify path to it manually.'))
    return executable


def create_info_message(message):
    return '[INFO]: {}'.format(message)


def create_error_message(message):
    return '[ERROR]: {}'.format(message)


# # # GRADLE UPDATE # # #

def generate_codepush_protection_script(protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path, target_type_ios, target_type_android):
    script = """// Digital.ai Hybrid JavaScript Protection injected script - start
                try {
                    var DAI_fs = require('fs');
                    var DAI_path = require('path');
                    var DAI_target;
                    var protect = true;
                    if (this.os === "android") {
                        DAI_target = TARGET_ANDROID;
                        if (!PROTECT_ANDROID) {
                            protect = false;
                        }
                    } else {
                        DAI_target = TARGET_IOS;
                        if (!PROTECT_IOS) {
                            protect = false;
                        }
                    }
                    if (protect) {
                        var protect_hook = DAI_path.join(process.cwd(), "protect-hybrid-hook.js");
                        if (DAI_fs.existsSync(protect_hook)) {
                            var DAI_protect_hybrid_js = require(protect_hook);
                            yield DAI_protect_hybrid_js.runProtection(this.updateContentsPath, DAI_target, this.os);
                        }
                    }
                } catch (error) {
                    interaction_1.out.text(chalk.red("\\nFailed to apply Digital.ai Hybrid JavaScript Protection: \\n" + error));
                    throw error;
                }
                // Digital.ai Hybrid JavaScript Protection injected script - end
                """
    script = script.replace("TARGET_ANDROID", '"-t reactnative-android"' if target_type_android is None else '""')
    script = script.replace("TARGET_IOS", '"-t reactnative-ios"' if target_type_ios is None else '""')

    if protect_hybrid_android_blueprint_path is not None:
        script = script.replace("PROTECT_ANDROID", 'true')
    else:
        script = script.replace("PROTECT_ANDROID", 'false')

    if protect_hybrid_ios_blueprint_path is not None:
        script = script.replace("PROTECT_IOS", 'true')
    else:
        script = script.replace("PROTECT_IOS", 'false')

    return script


def generate_protection_hook_script(protect_hybrid_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path):
    script = """#!/usr/bin/env node

var fs    = require('fs');
var path  = require('path');
var spawn = require('child_process').spawnSync;

function recursiveDelete(path)
{
    if (fs.existsSync(path))
    {
        fs.readdirSync(path).forEach(function(file, index)
        {
            var curPath = path + "/" + file;
            if (fs.lstatSync(curPath).isDirectory())
            { // recurse
                recursiveDelete(curPath);
            }
            else
            { // delete file
                fs.unlinkSync(curPath);
            }
        });

        fs.rmdirSync(path);
    }
}

function runProtection(pathToBundle, targetType, osType)
{
    var tempBundlePath = pathToBundle + "_obfuscated";

    // Build commandline
    var blueprint = "";
    if (osType === "android") {
        blueprint = BLUEPRINT_ANDROID;
    } else {
        blueprint = BLUEPRINT_IOS;
    }
    var cmd = `"PROTECT_HYBRID" -i "${pathToBundle}" -o "${tempBundlePath}" ${targetType} ${blueprint}`;

    // Execute Digital.ai Hybrid JavaScript Protection on this path
    console.log('Running Digital.ai Hybrid JavaScript Protection');
    var execProcess = spawn(cmd, { shell: true, stdio: "inherit"});

    if (execProcess.status !== 0)
        process.exit(execProcess.status);

    // delete original content path
    recursiveDelete(pathToBundle);

    // Move obfuscated dir to real path
    fs.renameSync(tempBundlePath, pathToBundle);
}

module.exports.runProtection = runProtection;
    """
    adjusted_hybrid_path = protect_hybrid_path.replace("\\", "\\\\")
    script = script.replace("PROTECT_HYBRID", adjusted_hybrid_path)

    if protect_hybrid_android_blueprint_path is not None and protect_hybrid_android_blueprint_path != "default":
        adjusted_blueprint_path = protect_hybrid_android_blueprint_path.replace("\\", "\\\\")
        script = script.replace("BLUEPRINT_ANDROID", '\'-b "{}"\''.format(adjusted_blueprint_path))
    else:
        script = script.replace("BLUEPRINT_ANDROID", '""')

    if protect_hybrid_ios_blueprint_path is not None and protect_hybrid_ios_blueprint_path != "default":
        adjusted_blueprint_path = protect_hybrid_ios_blueprint_path.replace("\\", "\\\\")
        script = script.replace("BLUEPRINT_IOS", '\'-b "{}"\''.format(adjusted_blueprint_path))
    else:
        script = script.replace("BLUEPRINT_IOS", '""')
    return script


def update_codepush(react_codepush_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path, target_type_ios, target_type_android):
    with open(react_codepush_path, 'r+') as react_file:
        file_data = react_file.read()

    script = generate_codepush_protection_script(protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path, target_type_ios, target_type_android)
    if file_data.find("Digital.ai Hybrid JavaScript Protection") < 0:
        with open(react_codepush_path, 'r') as react_file:
            file_data = react_file.readlines()
            for i in range(len(file_data)):
                if file_data[i].find("runReactNativeBundleCommand") > 0:
                    insert_index = i + 1
                    break

        if insert_index < 0:
            print(create_error_message('Unable to locate position for script injection. Please contact support@digital.ai for help resolving this error.'))
            sys.exit()
        file_data.insert(insert_index, script)
        with open(react_codepush_path, 'w+') as react_file:
            react_file.writelines(file_data)
        print(create_info_message('Injected protection script to CodePush.'))
    else:
        if file_data.find(script) < 0:
            script_start_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - start")
            script_end_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - end")
            if script_start_index < 0 or script_end_index < 0:
                print(create_error_message('Injected script was not found. Please contact support@digital.ai for help resolving this error.'))
                sys.exit()
            with open(react_codepush_path, 'w+') as react_file:
                file_data = file_data[:script_start_index] + script + file_data[script_end_index + len("// Digital.ai Hybrid JavaScript Protection injected script - finish"):]
                react_file.write(file_data)
            print(create_info_message('Protection script was updated with new configurations.'))
        else:
            print(create_info_message('Protection script with the same configurations was found, no updates were made.'))


def remove_codepush_scripts(codepush_react_path, project_path):
    if os.path.exists(os.path.join(project_path, "protect-hybrid-hook.js")):
        os.remove(os.path.join(project_path, "protect-hybrid-hook.js"))
        print(create_info_message('Protection hook was removed from project directory.'))
    else:
        print(create_info_message('No protection hook was found in project directory.'))

    with open(codepush_react_path, 'r+') as react_file:
        file_data = react_file.read()

    script_start_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - start")
    script_end_index = file_data.find("// Digital.ai Hybrid JavaScript Protection injected script - end")
    if script_start_index < 0 or script_end_index < 0:
        print(create_error_message('Injected script was not found. Please contact support@digital.ai for help resolving this error.'))
        sys.exit()

    with open(codepush_react_path, 'w+') as react_file:
        file_data = file_data[:script_start_index] + file_data[script_end_index + len("// Digital.ai Hybrid JavaScript Protection injected script - finish"):]
        react_file.write(file_data)
    print(create_info_message('Protection script was removed from CodePush.'))


def add_protection_hook(project_path, protect_hybrid_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path):
    script = generate_protection_hook_script(protect_hybrid_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path)
    protection_hook_path = os.path.join(project_path, "protect-hybrid-hook.js")
    if not os.path.exists(protection_hook_path):
        print(create_info_message('Protection hook was added to project directory.'))
    else:
        with open(protection_hook_path, 'r+') as hook_file:
            file_data = hook_file.read()
        if file_data.find(script) >= 0:
            print(create_info_message('Protection hook with the same configurations was found, no updates were made.'))
        else:
            print(create_info_message('Protection hook in project directory was updated.'))
    with open(protection_hook_path, 'w+') as hook_file:
        hook_file.write(script)

# # # MAIN # # #
def execute():
    print('Digital.ai Hybrid JavaScript Protection React Native CodePush Set-Up - start\n')

    args = parse_cli_args()

    project_path = os.path.realpath(get_input(args.project))
    if args.appcenter is not None:
        appcenter_path = args.appcenter
    else:
        found_ac = False
        try:
            temp = os.popen("npm root -g").readlines()
            if os.path.exists(os.path.join(temp[0][:-1], "appcenter-cli")):
                appcenter_path = os.path.join(temp[0][:-1], "appcenter-cli")
                found_ac = True
        except:
            pass
        if not found_ac:
            raise SystemExit(create_error_message("Unable to locate appcenter-cli installation path. Either provide a "
                                                  "custom path to the installation folder with an '--appcenter' command "
                                                  "line argument, or install appcenter-cli as an NPM package."))

    codepush_react_path = os.path.realpath(os.path.join(get_input(appcenter_path), "dist/commands/codepush/release-react.js"))
    protect_hybrid_path = get_input(args.protect_hybrid_js)
    protect_hybrid_android_blueprint_path = get_input(args.blueprint_for_android)
    protect_hybrid_ios_blueprint_path = get_input(args.blueprint_for_ios)

    if protect_hybrid_path is not None:
        protect_hybrid_path = os.path.realpath(protect_hybrid_path)
    if protect_hybrid_android_blueprint_path is not None and protect_hybrid_android_blueprint_path != "default":
        protect_hybrid_android_blueprint_path = os.path.realpath(protect_hybrid_android_blueprint_path)
    if protect_hybrid_ios_blueprint_path is not None and protect_hybrid_ios_blueprint_path != "default":
        protect_hybrid_ios_blueprint_path = os.path.realpath(protect_hybrid_ios_blueprint_path)

    target_android = get_target_type(protect_hybrid_android_blueprint_path)
    target_ios = get_target_type(protect_hybrid_ios_blueprint_path)

    if target_android is not None and target_android != "reactnative-android":
        raise ValueError(create_error_message('Wrong target type used in provided Android blueprint. Set the target type to "reactnative-android".'))
    if target_ios is not None and target_ios != "reactnative-ios":
        raise ValueError(create_error_message('Wrong target type used in provided iOS blueprint. Set the target type to "reactnative-ios".'))

    try:
        validate_file_exists(project_path)
        validate_file_exists(codepush_react_path)
        if protect_hybrid_android_blueprint_path is not None and protect_hybrid_android_blueprint_path != "default" and not args.remove:
            validate_file_exists(protect_hybrid_android_blueprint_path)
        if protect_hybrid_ios_blueprint_path is not None and protect_hybrid_ios_blueprint_path != "default" and not args.remove:
            validate_file_exists(protect_hybrid_ios_blueprint_path)
        protect_hybrid_path = validate_executable_path(protect_hybrid_path, "protect-hybrid-js", "Digital.ai Hybrid JavaScript Protection")
        if protect_hybrid_android_blueprint_path is None and protect_hybrid_ios_blueprint_path is None and not args.remove:
            raise ValueError(
                create_error_message('At least one of the "--blueprint-for-android" or "--blueprint-for-ios" is required. Provide the blueprints for the platforms that should be protected.'))
    except Exception as e:
        raise SystemExit(e)

    if args.remove:
        remove_codepush_scripts(codepush_react_path, project_path)
    else:
        add_protection_hook(project_path, protect_hybrid_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path)
        update_codepush(codepush_react_path, protect_hybrid_android_blueprint_path, protect_hybrid_ios_blueprint_path, target_ios, target_android)

    print('\nDigital.ai Hybrid JavaScript Protection React Native CodePush Set-Up - finish')


if __name__ == "__main__":
    execute()
