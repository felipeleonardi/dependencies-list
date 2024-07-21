#!/usr/bin/env python3

import os
import argparse
import subprocess
import shutil
import tempfile
import fnmatch
import sys
import zipfile
import json
import tokenize


class TargetType:
    REACT_NATIVE = 1,
    NATIVESCRIPT = 2,
    CORDOVA = 3,
    IONIC = 4,
    DEFAULT = 5

# # # ARGUMENTS # # #


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Apply default protection to React Native, NativeScript, Cordova or Ionic iOS apps.')
    input_type_group = parser.add_mutually_exclusive_group(required=True)
    input_type_group.add_argument("-xc", "--xcarchive", metavar='<PATH>',
                        help="Path to *.xcarchive file.")
    input_type_group.add_argument("-i", "--ipa", metavar='<PATH>',
                        help="Path to *.ipa file.")
    parser.add_argument("-b4h", "--blueprint-for-hybrid", metavar='<PATH>',
                        help="Path to the blueprint file for protect-hybrid-js.")
    parser.add_argument("-b4a", "--blueprint-for-apple", metavar='<PATH>',
                        help="Path to the blueprint file for protect-apple.")
    target_type_group = parser.add_mutually_exclusive_group(required=False)
    target_type_group.add_argument("-rn", "--reactnative",
                        help="Indicate that the supplied iOS file is a React Native app.",
                        action='store_true')
    target_type_group.add_argument("-ns", "--nativescript",
                        help="Indicate that the supplied iOS file is a NativeScript app.",
                        action='store_true')
    target_type_group.add_argument("-co", "--cordova",
                        help="Indicate that the supplied iOS file is a Cordova app.",
                        action='store_true')
    target_type_group.add_argument("-io", "--ionic",
                                   help="Indicate that the supplied iOS file is an Ionic (Capacitor) app.",
                                   action='store_true')

    parser.add_argument("-ph", "--protect-hybrid-js", metavar='<PATH>',
                        help="Path to the protect-hybrid-js.")
    parser.add_argument("-pa", "--protect-apple", metavar='<PATH>',
                        help="Path to the Digital.ai Apple Native Protection root folder.")
    parser.add_argument("-dnp", "--disable-native-protection",
                        help="Flag to disable protection using Digital.ai Apple Native Protection.",
                        action='store_true')

    return parser.parse_args()


# # # HybridJavaScriptProtection # # #

class HybridJavaScriptProtection:
    def __init__(self, protect_hybrid_path):
        assert protect_hybrid_path
        self._protect_hybrid_exe = protect_hybrid_path
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

        if self.updated_config_file_path:
            protect_hybrid_args.extend(["-b", self.updated_config_file_path])
        elif self.config_file_path:
            protect_hybrid_args.extend(["-b", self.config_file_path])

        if self.input_folder:
            protect_hybrid_args.extend(["-i", self.input_folder])

        if self.output_folder:
            protect_hybrid_args.extend(["-o", self.output_folder])

        if self.target_type == TargetType.REACT_NATIVE:
            protect_hybrid_args.extend(["-t", "reactnative-ios"])
        elif self.target_type == TargetType.NATIVESCRIPT:
            protect_hybrid_args.extend(["-t", "nativescript-ios"])
        elif self.target_type == TargetType.CORDOVA:
            protect_hybrid_args.extend(["-t", "cordova-ios"])
        elif self.target_type == TargetType.IONIC:
            protect_hybrid_args.extend(["-t", "ionic-ios"])

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
                'Invalid pathname: ' + pathname + '. Unable to use this as the ' + executable_description +
                ' executable.')
        return pathname

    if not is_on_path(executable):
        raise ValueError('No argument for ' + executable_description + ' provided. Unable to locate the ' +
                         executable_description + ' executable on PATH.')
    return executable


def file_without_extension(file_name):
    return os.path.splitext(file_name)[0]


def get_files_in_folder(folder, file_patterns, skip_patterns, relative_to=None, recursive=True):
    search_folder = "".join([folder.strip().rstrip("/"), "/"])
    files = []
    if not os.path.isdir(search_folder):
        print("[X] Search dir (" + search_folder + ") does not exist in current path:" + os.getcwd())
    else:
        all_entries = os.listdir(search_folder)
        for item in all_entries:
            path_name = os.path.join(search_folder, item)
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


def create_folders(to_folder, relative_pathname):
    folders = relative_pathname.replace(os.path.basename(relative_pathname), "").rstrip("/").split("/")
    for folder in folders:
        if len(folder.strip()) > 0:
            to_folder = os.path.join(to_folder, folder.strip())
            if not os.path.isdir(to_folder):
                os.mkdir(to_folder)


def copy_with_path(from_folder, to_folder, relative_pathname):
    create_folders(to_folder, relative_pathname)
    print("Copying file: " + relative_pathname)
    shutil.copyfile(os.path.join(from_folder, relative_pathname), os.path.join(to_folder, relative_pathname))


# retrieve folders which appear prior to "app" or "*.app" (including):
#  get_path_to_folder("a/b.app/app/d/") should return "a/b.app/app"
#  get_path_to_folder("a/b/c.app/d/") should return "a/b/c.app"
def get_path_to_app_folder(full_path):
    folders = full_path.split("/")
    idx = -1
    for i in range(len(folders)-1, 0, -1):
        if "www" == folders[i] or "app" == folders[i] or folders[i].endswith(".app"):
            idx = i
            break
    result = None
    if idx >= 0:
        result = ""
        for i in range(0, idx+1):
            result = os.path.join(result, folders[i])
    return result


def extract_zip_file(source_file_name, target_file_name):
    zip_ref = zipfile.ZipFile(source_file_name, 'r')
    zip_ref.extractall(target_file_name)
    zip_ref.close()


def compress_zip_file(source_file_name, target_file_name):
    target_file_name_without_ext = file_without_extension(target_file_name)
    shutil.make_archive(target_file_name_without_ext, 'zip', source_file_name)
    os.rename(target_file_name_without_ext + ".zip", target_file_name)


def payload_inner_folder(folder):
    payload_folder = os.path.join(folder, "Payload")
    for directory in os.listdir(payload_folder):
        if directory.endswith(".app"):
            return directory
    return ""


def convert_plist(folder, conversion_format):
    plist_file = os.path.join(folder, "Info.plist")
    if os.path.exists(plist_file):
        args = ["plutil", "-convert", conversion_format, plist_file]
        if subprocess.call(args) != 0:
            print("Failed to convert plist file")

# # # VALIDATION # # #


def validate_file_exists(path):
    if not os.path.exists(path):
        raise ValueError('Unable to locate file: "{}".'.format(path))


# A bit paranoid function - to retrieve Digital.ai Apple Native Protection path from any possible (logical) combinations
def validate_protect_apple_path(pa_path):
    if 'ENSUREIT' not in os.environ:  # highest priority
        if pa_path is None:  # get from PATH
            relative_path = 'bin/ensureit'
            path_dirs = os.environ['PATH'].split(os.pathsep)
            for path_dir in path_dirs:
                full_path = os.path.join(path_dir, relative_path)
                if os.path.exists(full_path):
                    pa_path = full_path
                    break

            if pa_path is not None:  # found binary -> need to remove bin/ensureit from full path to get EnsureIT folder
                idx = pa_path.rindex(os.path.join("bin", "ensureit"))
                os.environ['ENSUREIT'] = os.path.join(".", pa_path[0:idx].rstrip("\\/"))
                return
        else:  # provided input validation
            if os.path.isfile(pa_path) and os.path.basename(pa_path) == "ensureit":  # path includes binary
                os.environ['ENSUREIT'] = pa_path.replace("/bin/ensureit", "")
                return
            if os.path.isfile(os.path.join(pa_path, "bin/ensureit")):  # install path (as asked)
                os.environ['ENSUREIT'] = pa_path
                return
            if os.path.isfile(os.path.join(pa_path, "ensureit")):  # path to binary folder
                os.environ['ENSUREIT'] = pa_path.replace("/bin", "")
                return
        raise ValueError("Could not find Digital.ai Apple Native Protection application. Please set Environment variables, " +
                         "or add PATH, or provide Digital.ai Apple Native Protection path via input parameter")


def get_input(input_string):
    if input_string is not None:
        validated_string = input_string.strip()
        if len(validated_string) > 0:
            return validated_string
    return None


def get_name_with_architecture(file_name):
    ret_value = os.path.basename(file_name)
    items = file_name.split("/")
    idx = -1
    for item in items:
        idx += 1
        if "xcarchive.temp" in item:
            break
    if 0 <= idx < len(items)-2:
        return items[idx+1] + "_" + ret_value
    return ret_value


# # # Stdout # # #

def print_section_start(message):
    print('---- ' + message + ' ----\n')


def print_section_end():
    print('')


def protect_xcarchive(args, protect_hybrid_path, protect_hybrid_blueprint, protect_apple_blueprint, xcarchive_path, native_protection):

    temporary_folder = tempfile.mkdtemp()
    input_folder = os.path.join(temporary_folder, "input")
    os.mkdir(input_folder)
    output_folder = os.path.join(temporary_folder, "output")
    os.mkdir(output_folder)
    
    try:
        print_section_start('Copying protectable files')

        include_patterns = ["*.jsbundle", "*.js", "*.html"]
        files = get_files_in_folder(xcarchive_path, include_patterns, [], xcarchive_path, True)
        path_to_app = None
        for file in files:
            if path_to_app is None:  # Get path to "app", "www" or "*.app" folder (NativeScript/Cordova/ReactNative)
                path_to_app = get_path_to_app_folder(file.replace(os.path.basename(file), ""))  # supply only folders
            copy_with_path(xcarchive_path, input_folder, file)
            create_folders(output_folder, file)  # create relative path to app
        if path_to_app is not None:
            print("Offset path to detected app folder: " + path_to_app)
        print_section_end()

        print_section_start('Protecting with protect-hybrid-js')

        sjs = HybridJavaScriptProtection(protect_hybrid_path=protect_hybrid_path)
        if path_to_app is not None:
            sjs.input_folder = os.path.join(input_folder, path_to_app)
            sjs.output_folder = os.path.join(output_folder, path_to_app)
        else:
            sjs.input_folder = input_folder
            sjs.output_folder = output_folder

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

        print_section_start('Creating protected archive')
        base_name = os.path.basename(xcarchive_path)
        protected_protect_hybrid_xcarchive_path = os.path.join(temporary_folder, "Protected_" + base_name)
        remove_dir(protected_protect_hybrid_xcarchive_path)  # remove output from previous run
        shutil.copytree(xcarchive_path, protected_protect_hybrid_xcarchive_path)

        files = get_files_in_folder(output_folder, ["*"], [], output_folder, True)
        for file in files:
            shutil.copyfile(os.path.join(output_folder, file), os.path.join(protected_protect_hybrid_xcarchive_path, file))

        print_section_end()

        protected_protect_apple_xcarchive_path = None
        if native_protection:
            print_section_start('Protecting with protect-apple')
            protected_protect_apple_xcarchive_path = os.path.join(temporary_folder, "EIT_protected_" + base_name)
            sys.path.append(os.path.join(os.environ['ENSUREIT'], "lib"))
            try:
                from ArxanForIOS import protectIOS
                protect_apple_args = ["ensure_it_script"]  # dummy name to align argument parser
                protect_apple_args.extend(["-i", protected_protect_hybrid_xcarchive_path])
                # remove temporary files - do not remove temps until you copy guard mapping files
                # protect_apple_args.extend(["--remove-temps"])
                protect_apple_args.extend(["-o", protected_protect_apple_xcarchive_path])
                # protect_apple_args.extend(["-tv"])  # verbose output
                if protect_apple_blueprint is not None:
                    protect_apple_args.extend(["-b", protect_apple_blueprint])
                result = protectIOS.protect_IOS(protect_apple_args)
                if result != 0:
                    raise ValueError("Please check output for error description (Digital.ai Apple Native Protection execution code = " +
                                     str(result) + ")")
            except Exception as exc:
                raise ValueError("Exception during Digital.ai Apple Native Protection execution: " + str(exc))

            print_section_end()

        if native_protection:
            # Digital.ai Apple Native Protection App Aware files
            app_aware_files = get_files_in_folder(protected_protect_apple_xcarchive_path, ["*guard*.json"], [], None, True)
            for file in app_aware_files:
                output_name = get_name_with_architecture(file)
                print("Moving '" + file + "' to '" + "./" + output_name + "'")
                shutil.move(file, os.path.join("./", output_name))
        print_section_end()

        print_section_start('Copying protected xcarchive to initial folder')
        found_xcarchive = None
        if native_protection:
            folders = os.listdir(protected_protect_apple_xcarchive_path)
            for folder in folders:
                if not os.path.basename(folder).endswith(".xcarchive"):
                    continue
                found_xcarchive = os.path.join(protected_protect_apple_xcarchive_path, folder)
        else:
            found_xcarchive = protected_protect_hybrid_xcarchive_path

        if found_xcarchive is not None:
            final_output = xcarchive_path.replace(os.path.basename(xcarchive_path), "Protected " + base_name)
            remove_dir(final_output)
            shutil.copytree(found_xcarchive, final_output)
            print("Protected archive:" + final_output)

        print_section_end()

    except ValueError as inst:
        print_section_end()
        print_section_start('Exception')
        print(inst)
        print_section_end()
    finally:
        print_section_start('Cleaning')
        if sjs.updated_config_file_path is not None and os.path.exists(sjs.updated_config_file_path):
            os.remove(sjs.updated_config_file_path)
        print('Removed the temporary directory "{}".'.format(temporary_folder))
        remove_dir(temporary_folder)
        print_section_end()


def protect_ipa(args, protect_hybrid_path, protect_hybrid_blueprint, ipa_path):
    temporary_folder = tempfile.mkdtemp()
    input_folder = os.path.join(temporary_folder, "input")
    os.mkdir(input_folder)
    output_folder = os.path.join(temporary_folder, "output")
    os.mkdir(output_folder)

    try:
        sjs = HybridJavaScriptProtection(protect_hybrid_path=protect_hybrid_path)

        print_section_start('Extracting files')
        ipa_fullpath = os.path.realpath(ipa_path)
        ipa_filename_no_extension = file_without_extension(ipa_fullpath)

        extract_zip_file(source_file_name=ipa_fullpath, target_file_name=input_folder)

        inner_folder = payload_inner_folder(input_folder)
        if inner_folder != "":
            sjs.input_folder = os.path.join(input_folder, "Payload", inner_folder)
            sjs.output_folder = os.path.join(output_folder, "Payload", inner_folder)
            convert_plist(sjs.input_folder, "xml1")
        else:
            sjs.input_folder = input_folder
            sjs.output_folder = output_folder

        print('Extracted "{}" to the temporary directory "{}".'.format(ipa_fullpath, input_folder))
        print_section_end()

        print_section_start('Protecting with protect-hybrid-js')

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

        print_section_start('Compressing')

        protected_ipa = ipa_filename_no_extension + '-protected.ipa'

        if inner_folder != "":
            convert_plist(sjs.output_folder, "binary1")
        compress_zip_file(source_file_name=output_folder, target_file_name=protected_ipa)

        print('Compressed the temporary directory "{}" as "{}".'.format(output_folder, protected_ipa))
        print_section_end()

    except ValueError as inst:
        print_section_end()
        print_section_start('Exception')
        print(inst)
        print_section_end()
    finally:
        print_section_start('Cleaning')
        if sjs.updated_config_file_path is not None and os.path.exists(sjs.updated_config_file_path):
            os.remove(sjs.updated_config_file_path)
        print('Removed the temporary directory "{}".'.format(temporary_folder))
        remove_dir(temporary_folder)
        print_section_end()

# # # MAIN # # #


def execute():
    print('Digital.ai Hybrid JavaScript Protection (iOS) - start')

    args = parse_cli_args()

    protect_hybrid_path = get_input(args.protect_hybrid_js)
    protect_apple_path = get_input(args.protect_apple)
    protect_hybrid_config = get_input(args.blueprint_for_hybrid)
    protect_apple_config = get_input(args.blueprint_for_apple)

    native_protection = not args.disable_native_protection

    # initial validation

    try:
        if native_protection:
            if args.xcarchive is None:
                raise ValueError('Xcarchive file was not specified. Specify it by using the --xcarchive switch.')
            validate_file_exists(args.xcarchive)
            validate_protect_apple_path(protect_apple_path)
        else:
            if args.ipa is None and args.xcarchive is None:
                raise ValueError('Neither IPA nor Xcarchive file was specified. Specify it by using the --ipa or ' +
                                 '--xcarchive switches.')
            if args.ipa is not None and args.xcarchive is not None:
                raise ValueError('Both IPA and Xcarchive files were specified. You must specify only one or the other.')
            if args.ipa is not None:
                validate_file_exists(args.ipa)
            else:
                validate_file_exists(args.xcarchive)

        if protect_apple_config is not None:
            validate_file_exists(protect_apple_config)
        if protect_hybrid_config is not None:
            validate_file_exists(protect_hybrid_config)
        protect_hybrid_path = validate_executable_path(protect_hybrid_path, "protect-hybrid-js", "Digital.ai Hybrid JavaScript Protection")

    except Exception as e:
        raise SystemExit(e)

    if native_protection:
        protect_xcarchive(args, protect_hybrid_path, protect_hybrid_config, protect_apple_config, args.xcarchive, native_protection)
    else:
        if args.ipa is not None:
            protect_ipa(args, protect_hybrid_path, protect_hybrid_config, args.ipa)
        else:
            protect_xcarchive(args, protect_hybrid_path, protect_hybrid_config, None, args.xcarchive, native_protection)

    print('Digital.ai Hybrid JavaScript Protection (iOS) - finish')


if __name__ == "__main__":
    execute()
