#!/usr/bin/env python3

import os
import argparse
from random import randint, choice, seed
import time
import re
import string
import subprocess
import sys
from pathlib import Path
import shutil

import json
import tokenize


def ERROR(msg):
    print("\n[ERROR]: " + msg + "\n")
    sys.exit(-1)


class TargetType:
    REACT_NATIVE = 1,
    NATIVE_SCRIPT = 2,
    CORDOVA = 3,
    IONIC = 4


class PlatformType:
    ANDROID = 1,
    IOS = 2


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
                (current_idx + 1 == max_idx or tokens[current_idx + 1].string == "}" or tokens[current_idx + 1].string == "]"))

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
            if not self.is_trailing_comma(tokens, i):
                output.append(tokens[i])
        return output

    def get_json_as_string(self, file_name):
        output_string = ""
        if not os.path.isfile(file_name):
            ERROR("Unable to locate protect-hybrid-js blueprint at " + file_name +
                  ". Make sure the path is correct and the file exists.")
        with open(file_name, 'rb') as json_file:
            try:
                tokens = list(tokenize.tokenize(json_file.read))
            except Exception as e:
                ERROR("Provided blueprint file '" + file_name + "' contains invalid JSON. " + str(e))
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
            ERROR("Provided blueprint file '" + file_name + "' contains invalid JSON. " + str(e))

    def get_insensitive(self, json, key):
        if json is None:
            return None
        keys = list(json.keys())
        for i in range(0, len(keys)):
            if keys[i].lower() == key.lower():
                return json[keys[i]]
        return None


# Base for Plugin classes
class CodeLiftingPlugin:
    def __init__(self, project_path, app_id, script_path, plugin_path, platform_type):
        self.project_path = project_path
        self.app_id = app_id
        self.platform_type = platform_type
        self.input_path = os.path.join(script_path, plugin_path)
        self.script_path = script_path
        self.class_name_len = 3
        self.function_name_len = 7
        self.randomize()
        self.set_temp_dir()
        self.replace_dict = {
            'B_VALUE': str(self.b),
            'HASH_VALUE': str(self.hash_value),
            'CLASS_NAME': self.class_name,
            'FUNCTION_NAME': self.function_name,
            'PLUGIN_NAME': self.plugin_name
        }

    def set_temp_dir(self):
        tmp = os.path.join(self.script_path, 'tmp')
        unique_tmp = os.path.join(tmp, self.app_id + '-' + self.plugin_name)
        if not os.path.exists(tmp):
            os.mkdir(tmp)
        if not os.path.exists(unique_tmp):
            os.mkdir(unique_tmp)
        self.temp_path = unique_tmp

    def copy_with_replace(self, input_file, output_file, replace_dict={}):
        with open(os.path.join(self.input_path, input_file), 'r') as file:
            filedata = file.read()
        if len(replace_dict) > 0:
            for old_name in replace_dict:
                filedata = filedata.replace(old_name, replace_dict[old_name])
        output_file = os.path.join(self.temp_path, output_file)
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(os.path.join(self.temp_path, output_file), 'w') as file:
            file.write(filedata)

    def generate_secrets(self):
        self.s1 = randint(0, 10737418)
        self.s2 = randint(0, 10737418)
        self.s3 = randint(0, 10737418)
    
    def generate_values(self):
        self.a = self.s1 - self.s3
        self.b = 2*self.s2 + self.s3
        self.c = self.s3 - self.s2
    
    def generate_names(self):
        letters = string.ascii_letters
        self.class_name = ''.join(choice(letters) for i in range(self.class_name_len))
        self.function_name = ''.join(choice(letters) for i in range(self.function_name_len))
        self.plugin_name = ''.join(choice(letters) for i in range(2)) + str(abs(self.hash_code(self.app_id)))

    def hash_code(self, s):
        hash = 0
        for c in s:
            hash = (31 * hash + ord(c)) & 0xFFFFFFFF
        return ((hash + 0x80000000) & 0xFFFFFFFF) - 0x80000000

    def randomize(self):
        self.generate_secrets()
        self.generate_values()
        self.generate_names()
        self.hash_value = self.hash_code(str(self.s1 + self.s2 + self.s3))

    def set_environment_vars(self):
        # Set env variables
        envData = {
            'ARXAN_SECRET_1': str(self.s1),
            'ARXAN_SECRET_2': str(self.s2),
            'ARXAN_SECRET_3': str(self.s3),
            'ARXAN_CLASS': self.class_name,
            'ARXAN_FUNCTION': self.function_name,
            'ARXAN_PLUGIN': self.plugin_name
        }
        if sys.platform == "win32":
            if os.path.isdir(os.path.expandvars(R"C:\Users\$USERNAME\AppData\Local\Arxan\ArxanForHybrid")):
                with open(os.path.expandvars(R"C:\Users\$USERNAME\AppData\Local\Arxan\ArxanForHybrid\.{}".format(self.app_id)), 'w') as file:
                    file.write(json.dumps(envData))
            else:
                ERROR("Could not find the product license information. Make sure protect-hybrid-js is installed and licensed.")
        else:
            if os.path.isdir(os.path.expanduser('~/.arxan/ArxanForHybrid/')):
                with open(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(self.app_id)), 'w') as file:
                    file.write(json.dumps(envData))
            else:
                ERROR("Could not find the product license information. Make sure protect-hybrid-js is installed and licensed.")


# # # REACT NATIVE # # #

class ReactNative(CodeLiftingPlugin):
    def __init__(self, project_path, app_id, script_path, platform_type):
        super().__init__(project_path, app_id, script_path, "ReactNativePlugin", platform_type)

    def set(self):

        self.set_environment_vars()

        # Set common files
        self.copy_with_replace('index.js', 'index.js', self.replace_dict)
        self.copy_with_replace('package.json', 'package.json', self.replace_dict)

        print("Adding ReactNative plugin")
        # Set iOS plugin
        if self.platform_type == PlatformType.IOS:
            xc_prj_path = get_xcode_proj_dir(self.project_path, "ios")
            pbxfile = os.path.join(xc_prj_path, u'project.pbxproj')
            if not os.path.exists(pbxfile):
                ERROR("Could not locate project.pbxproj file. Make sure the iOS Xcode project is prepared.")

            self.copy_with_replace('ios/Unnamed.m', 'ios/{}.m'.format(self.class_name), self.replace_dict)
            self.copy_with_replace('ios/Unnamed.h', 'ios/{}.h'.format(self.class_name), self.replace_dict)

            import pbxproj
            self.xc_prj = pbxproj.XcodeProject.load(pbxfile)
            self.xc_prj.add_file(os.path.join(self.temp_path, 'ios/{}.m'.format(self.class_name)), force=False)
            self.xc_prj.add_file(os.path.join(self.temp_path, 'ios/{}.h'.format(self.class_name)), force=False)
            self.xc_prj.save()

        # Set Android plugin
        if self.platform_type == PlatformType.ANDROID:
            self.copy_with_replace('android/build.gradle', 'android/build.gradle', self.replace_dict)
            self.copy_with_replace('android/src/main/AndroidManifest.xml', 'android/src/main/AndroidManifest.xml', self.replace_dict)
            if not os.path.exists(os.path.join(self.temp_path, 'android/src/main/java/com/{}'.format(self.plugin_name))):
                os.makedirs(os.path.join(self.temp_path, 'android/src/main/java/com/{}'.format(self.plugin_name)))
            self.copy_with_replace('android/src/main/java/com/unnamed/UnnamedModule.java'.format(self.plugin_name), 'android/src/main/java/com/{}/{}Module.java'.format(self.plugin_name, self.class_name), self.replace_dict)
            self.copy_with_replace('android/src/main/java/com/unnamed/UnnamedPackage.java'.format(self.plugin_name), 'android/src/main/java/com/{}/{}Package.java'.format(self.plugin_name, self.class_name), self.replace_dict)

    def get_old_plugin_name(self):
        old_plugin_name = None
        for dir in os.listdir('node_modules'):
            if re.match("[\w\W]{2}" + str(abs(self.hash_code(self.app_id))), dir):
                old_plugin_name = dir
        return old_plugin_name

    def uninstall(self):
        old_plugin = self.get_old_plugin_name()
        if self.platform_type == PlatformType.ANDROID and old_plugin is not None:
            os.system('npm uninstall ' + old_plugin)
            if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', self.app_id + '-' + old_plugin)) and old_plugin != self.plugin_name:
                shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', self.app_id + '-' + old_plugin))

        if self.platform_type == PlatformType.IOS and os.path.isfile(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(self.app_id))):
            with open(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(self.app_id)), 'r') as file:
                vars = json.loads(file.read())
            try:
                self.xc_prj.remove_files_by_path('{}.m'.format(vars['ARXAN_CLASS']))
                self.xc_prj.remove_files_by_path('{}.h'.format(vars['ARXAN_CLASS']))
                self.xc_prj.save()
            except:
                pass

    def install(self):

        try:
            self.set()
        except SystemExit as e:
            raise e
        except:
            ERROR("Could not find the plugin directory. Make sure to preserve the script directory structure as it exists in the protect-hybrid-js installation archive.")

        os.chdir(self.project_path)
        self.uninstall()

        os.system('npm install "' + self.temp_path + '"')
        if (self.platform_type == PlatformType.IOS):
            os.chdir('ios')
            os.system('pod install')


# # # NATIVESCRIPT # # #

class NativeScript(CodeLiftingPlugin):
    def __init__(self, project_path, app_id, script_path, platform_type):
        super().__init__(project_path, app_id, script_path,"NativeScriptPlugin", platform_type)

    def set(self):

        self.set_environment_vars()

        resources = ''
        if not os.path.exists(os.path.join(self.project_path, 'App_Resources')):
            resources = 'app'

        # Set Android plugin
        if self.platform_type == PlatformType.ANDROID:
            self.copy_with_replace('android/Unnamed.java', 'android/{}.java'.format(self.class_name), self.replace_dict)
        
            if not os.path.exists(os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java')):
                os.mkdir(os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java/'))
            if not os.path.exists(os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java/{}'.format(self.plugin_name))):
                os.mkdir(os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java/{}'.format(self.plugin_name)))
            os.rename(os.path.join(self.temp_path, 'android/{}.java'.format(self.class_name)), os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java/{}/{}.java'.format(self.plugin_name, self.class_name)))

        # Set iOS plugin
        if self.platform_type == PlatformType.IOS:
            self.copy_with_replace('ios/Unnamed.m', 'ios/{}.m'.format(self.class_name), self.replace_dict)
            self.copy_with_replace('ios/Unnamed.h', 'ios/{}.h'.format(self.class_name), self.replace_dict)
            self.copy_with_replace('ios/Unnamed.modulemap', 'ios/module.modulemap', self.replace_dict)
            if not os.path.exists(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/')):
                os.mkdir(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/'))
            os.rename(os.path.join(self.temp_path, 'ios/{}.m'.format(self.class_name)), os.path.join(self.project_path, resources, 'App_Resources/iOS/src/{}.m'.format(self.class_name)))
            os.rename(os.path.join(self.temp_path, 'ios/{}.h'.format(self.class_name)), os.path.join(self.project_path, resources, 'App_Resources/iOS/src/{}.h'.format(self.class_name)))

            if not os.path.exists(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/module.modulemap')):
                os.rename(os.path.join(self.temp_path, 'ios/module.modulemap'), os.path.join(self.project_path, resources, 'App_Resources/iOS/src/module.modulemap'))
            else:
                with open(os.path.join(self.temp_path, 'ios/module.modulemap'), 'r') as file :
                    filedata = file.read()
                with open(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/module.modulemap'), 'a') as file:
                    file.write(filedata)

    def uninstall(self):
        resources = ''
        if not os.path.exists(os.path.join(self.project_path, 'App_Resources')):
            resources = 'app'

        if sys.platform == "win32":
            if os.path.isfile(os.path.expandvars(R"C:\Users\$USERNAME\AppData\Local\Arxan\ArxanForHybrid\.{}".format(self.app_id))):
                with open(os.path.expandvars(R"C:\Users\$USERNAME\AppData\Local\Arxan\ArxanForHybrid\.{}".format(self.app_id)), 'r') as file:
                    vars = json.loads(file.read())
        else:
            if os.path.isfile(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(self.app_id))):
                with open(os.path.expanduser('~/.arxan/ArxanForHybrid/.{}'.format(self.app_id)), 'r') as file:
                    vars = json.loads(file.read())

        if self.platform_type == PlatformType.IOS:
            try:
                os.remove(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/{}.m'.format(vars['ARXAN_CLASS'])))
                os.remove(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/{}.h'.format(vars['ARXAN_CLASS'])))
            except:
                pass
            try:
                with open(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/module.modulemap'), 'r') as file:
                    filedata = file.read().replace('module ' + vars['ARXAN_CLASS'] + ' {\n    header "' + vars['ARXAN_CLASS'] + '.h"\n    export *\n}\n', '')
                with open(os.path.join(self.project_path, resources, 'App_Resources/iOS/src/module.modulemap'), 'w') as file:
                    file.write(filedata)
            except:
                pass

        if self.platform_type == PlatformType.ANDROID:
            try:
                shutil.rmtree(os.path.join(self.project_path, resources, 'App_Resources/Android/src/main/java/{}'.format(vars['ARXAN_PLUGIN'])))
                shutil.rmtree(os.path.join(self.project_path, 'platforms/android/app/src/main/java/{}'.format(vars['ARXAN_PLUGIN'])))
            except:
                pass

    def install(self):
        try:
            self.uninstall()
            self.set()
        except SystemExit as e:
            raise e
        except:
            ERROR("Could not find the plugin directory. Make sure to preserve the script directory structure as it exists in the protect-hybrid-js installation archive.")
        finally:
            if os.path.isdir(self.temp_path):
                shutil.rmtree(self.temp_path)

        os.chdir(self.project_path)
        if (self.platform_type == PlatformType.IOS):
            os.system('tns prepare ios')
        if (self.platform_type == PlatformType.ANDROID):
            os.system('tns prepare android')


# # # CORDOVA # # #

class CordovaPlugin(CodeLiftingPlugin):
    def __init__(self, project_path, app_id, script_path, platform_type):
        super().__init__(project_path, app_id, script_path, "CordovaPlugin", platform_type)

    def set(self):

        self.set_environment_vars()

        # Set common files
        self.copy_with_replace('www/Unnamed.js', 
                               'www/{}.js'.format(self.class_name),
                               self.replace_dict)
        self.copy_with_replace('plugin.xml',
                               'plugin.xml',
                               self.replace_dict)
        self.copy_with_replace('package.json',
                               'package.json',
                               self.replace_dict)
        if (self.platform_type == PlatformType.IOS):
            self.copy_with_replace('src/ios/Unnamed.m',
                                'src/ios/{}.m'.format(self.class_name),
                                self.replace_dict)
        if (self.platform_type == PlatformType.ANDROID):
            self.copy_with_replace('src/android/Unnamed.java',
                                'src/android/{}.java'.format(self.class_name),
                                self.replace_dict)

    def get_old_plugin_name(self):
        output = subprocess.check_output("cordova plugin list", shell=True)
        old_plugin_name = re.search("[\w\W]{2}" + str(abs(self.hash_code(self.app_id))), output.decode('utf-8'))
        if old_plugin_name is None:
            return None
        return old_plugin_name.group()

    def install(self):
        try:
            self.set()
        except SystemExit as e:
            raise e
        except:
            ERROR("Could not find the plugin directory. Make sure to preserve the script directory structure as it exists in the protect-hybrid-js installation archive.")

        os.chdir(self.project_path)
        old_plugin = self.get_old_plugin_name()
        if (old_plugin is not None):
            os.system('cordova plugin remove ' + old_plugin)
            if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', self.app_id + '-' + old_plugin)) and old_plugin != self.plugin_name:
                shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', self.app_id + '-' + old_plugin))

        os.system('cordova plugin add ' + '"' + self.temp_path + '"')


# # # Xcode integration functions # # #

def get_script_content(targetType, ph_path, b4h_path):
    if targetType == TargetType.CORDOVA:
        scriptContent = """
PH_DEST_DIR="$BUILT_PRODUCTS_DIR/$FULL_PRODUCT_NAME/www"
PH_TEMP_DIR=$(mktemp -d)
mv "$PH_DEST_DIR" "$PH_TEMP_DIR"
__PH_PATH__ -b __B4H_PATH__ -i "$PH_TEMP_DIR"/www -o "$PH_DEST_DIR"
if [[ $? != 0 ]]; then
    exit -1
fi
rm -rf "$PH_TEMP_DIR"/www
"""
    if (targetType == TargetType.NATIVE_SCRIPT):
        scriptContent = """
PH_DEST_DIR="$BUILT_PRODUCTS_DIR/$FULL_PRODUCT_NAME/app"
PH_TEMP_DIR=$(mktemp -d)
mv "$PH_DEST_DIR" "$PH_TEMP_DIR"
__PH_PATH__ -b __B4H_PATH__ -i "$PH_TEMP_DIR"/app -o "$PH_DEST_DIR" 
if [[ $? != 0 ]]; then
    exit -1
fi
pushd "$PH_TEMP_DIR/app"
du -a > $PROJECT_DIR/bundle_files.info
popd
rm -rf "$PH_TEMP_DIR"/app
"""
    if (targetType == TargetType.REACT_NATIVE):
        scriptContent = """
PH_DEST_DIR="$CONFIGURATION_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
BUNDLE_NAME="main.jsbundle"
PH_TEMP_DIR=$(mktemp -d)
mv "$PH_DEST_DIR/$BUNDLE_NAME" "$PH_TEMP_DIR/$BUNDLE_NAME"
__PH_PATH__ -b __B4H_PATH__ -i "$PH_TEMP_DIR/$BUNDLE_NAME" -o "$PH_DEST_DIR"
if [[ $? != 0 ]]; then
    exit -1
fi
rm -f "$PH_TEMP_DIR/$BUNDLE_NAME"
"""
    
    scriptContent = scriptContent.replace("__PH_PATH__", ph_path)
    scriptContent = scriptContent.replace("__B4H_PATH__", b4h_path)
    return scriptContent


def get_config_by_framework(targetType, ph_path, b4h_path):

    if (targetType == TargetType.CORDOVA):
        scriptContent = get_script_content(targetType, ph_path, b4h_path)
        movePhases = {}
        bundlingPhase = "Copy Staging Resources"
        platformPath = "platforms/ios"

    if (targetType == TargetType.NATIVE_SCRIPT):
        scriptContent = get_script_content(targetType, ph_path, b4h_path)
        movePhases = {"PBXResourcesBuildPhase" : "NativeScript PreBuild"}
        bundlingPhase = "PBXResourcesBuildPhase"
        platformPath = "platforms/ios"

    if (targetType == TargetType.REACT_NATIVE):
        scriptContent = get_script_content(targetType, ph_path, b4h_path)
        movePhases = { "Bundle React Native code and images" : "[CP] Check Pods Manifest.lock"}
        bundlingPhase = "Bundle React Native code and images"
        platformPath = "ios"
    
    return scriptContent, movePhases, bundlingPhase, platformPath


def get_from_path(file_name):
    """Get `file_name` path searching by PATH environment variable."""
    from shutil import which
    return which(file_name)


# check that we are using the right version of pbxproj.
# Shameless copy from add-arxan.py
def check_pbxproj_version(pbxproj):
    oldest_version = "2.7.0"
    actual_version = pbxproj.__version__
    
    oldest_int = int(oldest_version.replace('.',''))
    actual_int = int(actual_version.replace('.', ''))
    
    if actual_int < oldest_int:
        ERROR(u'Using pbxproj ' +  actual_version + u'\nPlease install pbxproj ' +  oldest_version + u', or newer')


def get_xcode_proj_dir(app_path, platformPath):
    xc_prj_path = os.path.join(app_path, platformPath)
    if not os.path.isdir(xc_prj_path):
        ERROR("Project " + app_path + " is not prepared for Xcode build.")
    prjs = [e for e in os.listdir(xc_prj_path) if e.endswith('.xcodeproj')]
    if len(prjs) != 1:
        ERROR("Project directory should only contain one Xcode project. Please contact support@digital.ai for help resolving this error.")
    return os.path.join(xc_prj_path, prjs[0])


def get_phase_pos(xc_prj, target, phaseName):
    for i in range(0, len(target.buildPhases)):
        phaseKey = target.buildPhases[i]
        name = None
        isa = None
        try: # not all of them have names :(
            isa = xc_prj.get_object(phaseKey).isa
            name = xc_prj.get_object(phaseKey).name

            # Older Cordova versions have different phase name
            if(name == "Copy www directory"):
                name = "Copy Staging Resources"
        except:
            pass # do nothing generally :)
        if (name is not None and name.lower() == phaseName.lower()): # React native could have different case even in same project
            return i
        if (isa is not None and isa == phaseName):
            return i    
    return None


# Move "phaseName" build phase execution right after "phaseAfter"
def move_phase(xc_prj, target, phaseName, phaseAfter):
    currentPos = get_phase_pos(xc_prj, target, phaseName)
    if (currentPos is None):
        return False

    targetPos = get_phase_pos(xc_prj, target, phaseAfter)
    if (targetPos is None):
        return False
    targetPos = targetPos if phaseAfter == "NativeScript PreBuild" else targetPos + 1

    if (currentPos != targetPos):
        target.buildPhases.insert(targetPos, target.buildPhases[currentPos])
        if (currentPos > targetPos):
            del target.buildPhases[currentPos + 1]
        else:
            del target.buildPhases[currentPos]

    return True

def get_additional_code(target_type):
    if (target_type == TargetType.CORDOVA or target_type == TargetType.NATIVE_SCRIPT):
        return """
bool endsWith(const std::string& text, const std::string& suffix)
{
    if (suffix.length() > text.length()) {
        return false;
    }
    return (text.substr(text.length() - suffix.length()) == suffix);
}

bool isJsFile(const std::string& fn) {
    const char* ext[] = { ".js", ".html", ".htm" };
    for (size_t i = 0; i < sizeof(ext) / sizeof(ext[0]); ++i) {
        if (endsWith(fn, std::string(ext[i])))
            return true;
    }
    return false;
}

void getFilesInFolder(const std::string& path, std::vector<std::string>& files) {
    struct dirent* dir = nullptr;
    DIR* d = opendir(path.c_str());
    if (d)
    {
        while ((dir = readdir(d)))
        {
            if (dir->d_type == DT_REG && isJsFile(std::string(dir->d_name)))
            {
                files.push_back(path + "/" + dir->d_name);
            }
            else if (dir->d_type == DT_DIR && strcmp(dir->d_name, ".") && strcmp(dir->d_name, ".."))
            {
                getFilesInFolder(path + "/" + dir->d_name, files);
            }
        }
        closedir(d);
    }
}   

void getFileList(const std::string& folder, std::vector<std::string>& files) {
    char buffer[1024];
    FILE* fd = fopen("bundle_files.info", "r");
    if (fd) {
        while(!feof(fd)) {
            buffer[0] = 0;
            if (fgets(buffer, sizeof(buffer), fd)) {
                size_t len = strlen(buffer);
                while(len && (buffer[len - 1] == '\\r' || buffer[len - 1] == '\\n')) {
                    --len;
                    buffer[len] = 0;
                }
                if (len) {
                    std::string fileName(buffer);
                    size_t pos = fileName.find_first_of("/");
                    if (std::string::npos != pos) {
                        fileName = fileName.substr(pos + 1);
                        if (isJsFile(fileName)) {
                            files.push_back(folder + "/" + fileName);
                        }
                    }
                }
            }
        }
        fclose(fd);
    }
}   

FileExpr& getFileExpr(GuardSpec& gs, std::vector<std::string>& fileNames) {
    std::string fn = fileNames.back();
    fileNames.pop_back();
    if (fileNames.size()) 
        return gs.file(fn) + getFileExpr(gs, fileNames);
    return gs.file(fn);
}

FileExpr& getFiles(GuardSpec& gs, const std::string& folder, const std::string& defaultFile) {

    std::vector<std::string> fileNames;
    getFilesInFolder(folder, fileNames);
    if (!fileNames.size()) {
        getFileList(folder, fileNames); // Try from bundle_files.info - list created durin invocation of protect-hybrid-js
    }

    if (!fileNames.size()) {
        printf("[WARNING]: Could not find JavaScript files for automatic Resource Verification. You can specify them manually in your GuardSpec.");
        return gs.file(defaultFile);
    }
    return getFileExpr(gs, fileNames);
}
"""
    return ""


def get_files_collection_code(target_type):
    if (target_type == TargetType.CORDOVA):
        return 'FileExpr& files = getFiles(gs, "www", "www/js/index.js");'
    if (target_type == TargetType.NATIVE_SCRIPT):
        return 'FileExpr& files = getFiles(gs, "app", "app/bundle.js");'
    if (target_type == TargetType.REACT_NATIVE):
        return 'FileExpr& files = gs.file("main.jsbundle");'
    ERROR("Internal Error. Unknown target type.")

def create_default_guardspec(cfg_path, hybrid_guardspec_path, seed):
    default_guardspec_cpp = os.path.join(cfg_path, "GuardSpec.cpp")
    cpp_content = """
//
//  GuardSpec.cpp
//
//  Created by hybrid-install-plugin.py script on __DATE__.
//

#include <stdio.h>
#include "EnsureIT.h"
#include <unistd.h>
#include <cstdlib>

using namespace eit;

#include "_HYBRID_GUARDSPEC_"

int main(int argc, char** argv)
{
    GuardSpec gs;

    setHybridProtection(gs);
    gs.obfuscate(gs.sourceBitcode(), 100);
    gs.seed(__SEED__);
    gs.execute(argc, argv);
    
    return 0;
}
"""

    cpp_content = cpp_content.replace("__DATE__", time.strftime("%Y-%m-%d", time.localtime()))
    cpp_content = cpp_content.replace("__SEED__", str(seed))
    cpp_content = cpp_content.replace("_HYBRID_GUARDSPEC_", hybrid_guardspec_path)

    with open(default_guardspec_cpp, "w") as file:
        file.write(cpp_content)

    return default_guardspec_cpp

def create_hybrid_guardspec(cfg_path, module_name, function_name, target_type):
    hybrid_guardspec_hpp = os.path.join(cfg_path, "HybridGuardSpec.hpp")
    hpp_content = """
//
//  HybridGuardSpec.hpp
//
//  Created by hybrid-install-plugin.py script on __DATE__.
//

#include <vector>
#include <string>
#include <dirent.h>

__ADDITIONAL_CODE__

void setHybridProtection(GuardSpec& gs) {
    gs.repair("plugin_repair", gs.function("__FUNCTION_NAME__", SUBSTRING).entry(), gs.data("hash_value") + gs.data("b_value")).protectWritableRanges().protectDataOnly().preDamage();
    gs.damage("plugin_damage", gs.function("__FUNCTION_NAME__", SUBSTRING).returns(), gs.data("hash_value") + gs.data("b_value")).protectWritableRanges().protectDataOnly();
    gs.damage("plugin_damage_on_tamper", gs.function("tamperAction").entry(), gs.data("tamper_value") + gs.data("b_value") + gs.data("hash_value")).protectWritableRanges().protectDataOnly();
    
    std::set<eit::DIDAlgorithm> algorithms;
    algorithms.insert(eit::FridaPresenceDetectionQuickScan);
    gs.detectDynamicInstrumentation("plugin_dynamic_instrumentation_detection",
    gs.function("__FUNCTION_NAME__", SUBSTRING).entry(), algorithms).setTamperAction(gs.function("tamperAction"));
    
    gs.detectDebugger("plugin_debugger_detection", gs.function("__FUNCTION_NAME__", SUBSTRING).entry()).setTamperAction(gs.function("tamperAction"));
    
    gs.checksum("plugin_cs", gs.function("main").entry(), gs.module("__MODULE_NAME__.o"));
    
    __BUNDLE_FILES__
    gs.resourceVerification("plugin_rv", gs.function("main").entry(), files);
    gs.encryptStrings();
    gs.obfuscate(gs.allGuards(), 300);
    gs.obfuscate(gs.module("__MODULE_NAME__.o"), 100);
}
"""
    hpp_content = hpp_content.replace("__DATE__", time.strftime("%Y-%m-%d", time.localtime()))
    hpp_content = hpp_content.replace("__ADDITIONAL_CODE__", get_additional_code(target_type))
    hpp_content = hpp_content.replace("__MODULE_NAME__", module_name)
    hpp_content = hpp_content.replace("__FUNCTION_NAME__", function_name)
    hpp_content = hpp_content.replace("__BUNDLE_FILES__", get_files_collection_code(target_type))
    with open(hybrid_guardspec_hpp, "w") as file:
        file.write(hpp_content)

    return hybrid_guardspec_hpp


def get_extra_flags(target_type):
    all_flags = '"-v"'
    if (target_type == TargetType.CORDOVA):
        return all_flags
    if (target_type == TargetType.NATIVE_SCRIPT):
        return all_flags + ', "-original-tool $SRCROOT/internal/nsld.sh"'
    if (target_type == TargetType.REACT_NATIVE):
        return all_flags


def get_target_name(target_type):
    if (target_type == TargetType.CORDOVA):
        return "Cordova"
    if (target_type == TargetType.NATIVE_SCRIPT):
        return "NativeScript"
    if (target_type == TargetType.REACT_NATIVE):
        return "ReactNative"
    return None


def create_default_pa_configuration(cfg_path, pa_path, xcode_prj, xc_targets, guard_spec, target_type):
    cfg_file_name = os.path.join(cfg_path, "add_arxan.json")

    target_content = """                {
                    "bundleName": "__TARGET_NAME__",
                    "guardSpec" : "__GUARDSPEC__",
                    "extraFlags" : [ __EXTRA_FLAGS__ ]
                }"""    

    content = """{
    "arxanPath": "__PA_PATH__",
    "target" : "__TARGET__",
    "configurations": [ "Release", "Debug" ],
    "projects": [
        {
            "xcodeproj": "__XCODE_PRJ__",
            "targets": [ 
                __TARGETS__
            ]
        }
    ]
}"""
    if pa_path is None:
        relative_path = 'bin/ensureit'
        path_dirs = os.environ['PATH'].split(os.pathsep)
        for path_dir in path_dirs:
            full_path = os.path.join(path_dir, relative_path)
            if os.path.exists(full_path):
                pa_path = full_path
                break

        if pa_path is not None:  # found binary -> need to remove bin/ensureit from full path to get EnsureIT folder
            idx = pa_path.rindex(os.path.join("bin", "ensureit"))
            pa_path = pa_path[0:idx]
            pa_path = os.path.join(".", pa_path.rstrip("\\/"))
    if pa_path is None:
        ERROR("Unable to locate Digital.ai Apple Native Protection binary.")
    if not os.path.isfile(os.path.join(pa_path, "bin", "ensureit")):  # we expect EnsureIT install folder here
        ERROR("Unable to locate Digital.ai Apple Native Protection binary at " + pa_path + ". Make sure the path is correct and the file exists.")

    content = content.replace("__PA_PATH__", pa_path)
    content = content.replace("__TARGET__", get_target_name(target_type))
    content = content.replace("__XCODE_PRJ__", xcode_prj)

    targets = []
    for t in xc_targets:
        target_item = target_content
        target_item = target_item.replace("__TARGET_NAME__", t)
        target_item = target_item.replace("__GUARDSPEC__", guard_spec)
        target_item = target_item.replace("__EXTRA_FLAGS__", get_extra_flags(target_type))
        targets.append(target_item)

    content = content.replace("__TARGETS__", ",".join(targets))

    with open(cfg_file_name, "w") as file:
        file.write(content)

    return cfg_file_name


def update_xcode(args, target_type, module_name, function_name, seed):
    import pbxproj
    from pbxproj.pbxsections.XCBuildConfiguration import XCBuildConfigurationFlags

    print("Start of Xcode integration for Hybrid app")

    check_pbxproj_version(pbxproj)

    ph_path = get_from_path("protect-hybrid-js")
    if args.protect_hybrid_js is not None:
        ph_path = args.protect_hybrid_js
    if ph_path is None:
        ERROR("Unable to locate protect-hybrid-js binary.")
    elif not os.path.isfile(ph_path):
        ERROR("Unable to locate protect-hybrid-js binary at " + ph_path + ". Make sure the path is correct and the file exists.")

    scriptContent, movePhases, bundlingPhase, platformPath = get_config_by_framework(target_type, ph_path, args.blueprint_for_hybrid)

    xc_prj_path = get_xcode_proj_dir(args.project, platformPath)
    pbxfile = os.path.join(xc_prj_path, u'project.pbxproj')
    if (not os.path.exists(pbxfile)):
        ERROR("Could not locate project.pbxproj file. Make sure the iOS Xcode project is prepared.")

    print(" - Loading project:" + pbxfile)
    xc_prj = pbxproj.XcodeProject.load(pbxfile)

    print(" - Creating protect-hybrid-js execution script")
    scriptName = "Run protect-hybrid-js"
    newphase = pbxproj.pbxsections.PBXShellScriptBuildPhase.create(
        scriptContent,
        name = scriptName)

    xc_targets = []
    for t in xc_prj.get_object(xc_prj.rootObject).targets:
        target = xc_prj.get_object(t)
        # if targets provided, make changes only for those targets. 
        # all targets are affected otherwise

        # we add files manually, so we need to correct LIBRARY_SEARH_PATH for targets. 
        # for some reason it is missin $(inherited)
        # execute that for all BuildConfigurations for all targets
        if (target_type == TargetType.REACT_NATIVE):
            bc_list = xc_prj.objects[target.buildConfigurationList]
            target_bc = bc_list['buildConfigurations']
    
            for bc in target_bc:
                bc_obj = xc_prj.get_object(bc)
                if bc_obj is not None:
                    bc_obj.remove_search_paths(XCBuildConfigurationFlags.LIBRARY_SEARCH_PATHS, ["$(inherited)"])
                    bc_obj.add_search_paths(XCBuildConfigurationFlags.LIBRARY_SEARCH_PATHS, ['$(inherited)'])

        if (args.targets is not None and len(args.targets) > 0 and not target.name in args.targets):
            continue
        if (get_phase_pos(xc_prj, target, scriptName) is None): # is it first run ???
            phase_moved = True
            for item in movePhases:
                if not move_phase(xc_prj, target, item, movePhases[item]):
                    phase_moved = False
            if not phase_moved:
                continue
            print(" - Adding protect-hybrid-js execution to \"" + target.name + "\" target")
            target.add_build_phase(newphase)
            target.get_parent()[newphase.get_id()] = newphase
            move_phase(xc_prj, target, scriptName, bundlingPhase)
        xc_targets.append(target.name)
    if len(xc_targets) == 0:
        ERROR("No valid targets among " + str(target.buildPhases) + " found. Please contact support@digital.ai for help resolving this error.")


    xc_prj.save()

    arxan_dir = os.path.join(args.project, "Arxan")
    if (args.add_arxan_configuration is None):
        # create default configuration and guardspec for add-arxan.py script
        if (not os.path.isdir(arxan_dir)):
            os.makedirs(arxan_dir)
        hybrid_guardspec_path = create_hybrid_guardspec(arxan_dir, module_name, function_name, target_type)
        default_guard_spec_path = create_default_guardspec(arxan_dir, hybrid_guardspec_path, seed)
        aa_cfg = create_default_pa_configuration(arxan_dir, args.protect_apple, xc_prj_path, xc_targets, default_guard_spec_path, target_type)
    else:
        aa_cfg = args.add_arxan_configuration
        if (not os.path.exists(aa_cfg)):
            ERROR("Provided configuration file does not exist: " + aa_cfg)
        bp = Blueprint()
        config = bp.get_json_as_string(aa_cfg)
        config = json.loads(config)
        guard_spec_path = config["projects"][0]["targets"][0]["guardSpec"]
        hybrid_guardspec_path = create_hybrid_guardspec(os.path.split(guard_spec_path)[0], module_name, function_name, target_type)
        with open(guard_spec_path, 'r+') as user_guard_spec:
            lines = user_guard_spec.readlines()
            if not [line for line in lines if "setHybridProtection" in line]:
                main_index = [i for i, line in enumerate(lines) if "int main(" in line]
                lines.insert(main_index[0] - 1, '\n#include "{}"\n'.format(hybrid_guardspec_path))
                for i, line in enumerate(lines):
                    if bool(re.search('GuardSpec \w[a-zA-Z0-9_-]+;', line.strip())):
                        gs_identifier = line.split()[1].strip(";")
                        lines.insert(i + 1, '\n\tsetHybridProtection({});\n'.format(gs_identifier))
                user_guard_spec.seek(0)
                user_guard_spec.writelines(lines)

    add_arxan_path = args.add_arxan_path
    if (add_arxan_path is None):
        add_arxan_path = get_from_path("add-arxan.py")
    if (add_arxan_path is None or not os.path.isfile(add_arxan_path)):
        ERROR("Unable to locate 'add-arxan.py' script required to install Digital.ai Apple Native Protection on provided project. Please contact support@digital.ai for help resolving this error.")

    cmd_line = ["python3", add_arxan_path, aa_cfg]
    if (0 != os.system(" ".join(cmd_line))):
        sys.exit(-1)

    _, extension = os.path.splitext(xc_prj_path)
    protected_xc_prj_path = xc_prj_path[0:-len(extension)] + "_ensureit.xcodeproj"
    if os.path.exists(xc_prj_path) and os.path.exists(protected_xc_prj_path):
        shutil.rmtree(xc_prj_path)
        os.rename(protected_xc_prj_path, xc_prj_path)

    print("Xcode integration for Hybrid app completed")


# # # ARGUMENTS # # #

def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='Install Code Lifting Detection Android/iOS plugin.')
    parser.add_argument("-p", "--project", metavar="<PATH>",
                        help="Path to the project directory (REQUIRED).",
                        required=True)
    parser.add_argument("-b4h", "--blueprint-for-hybrid", metavar='<PATH>',
                        help="Path to the blueprint file for protect-hybrid-js (REQUIRED).",
                        required=True)
    parser.add_argument("-ph", "--protect-hybrid-js", metavar='<PATH>',
                        help="Path to the protect-hybrid-js binary.")
    parser.add_argument("-t", "--targets", nargs='*',
                        help="Xcode targets to be updated.")
    parser.add_argument("-aap", "--add-arxan-path", metavar='<PATH>',
                        help="Path to add-arxan.py script.")
    parser.add_argument("-acfg", "--add-arxan-configuration", metavar='<PATH>',
                        help="Path to configuration json file used by add-arxan.py script. Default would be created if not provided.")
    parser.add_argument("-pa", "--protect-apple", metavar='<PATH>',
                        help="Path to Digital.ai Apple Native Protection root folder.")
    args = parser.parse_args()
    args.project = os.path.abspath(args.project)
    args.blueprint_for_hybrid = os.path.abspath(args.blueprint_for_hybrid)
    return args


def execute(script_path):
    print('Digital.ai Hybrid JavaScript Protection Code Lifting Detection Plugin Installation - start')

    args = parse_cli_args()

    # we need APP_ID and Target from blueprint
    bp = Blueprint()
    ph_bp_json = bp.load_hybrid_blueprint(args.blueprint_for_hybrid)
    glob_section = bp.get_insensitive(ph_bp_json, "globalConfiguration")
    app_id = bp.get_insensitive(glob_section, "appid")
    if app_id is None or len(app_id) == 0:
        ERROR("Provided protect-hybrid-js blueprint does not contain valid 'appid' setting: " + args.blueprint_for_hybrid)

    bp_seed = bp.get_insensitive(glob_section, "seed")
    if isinstance(bp_seed, str) and bp_seed.lower() == "random":
        bp_seed = None

    target_type = None
    platform_type = None
    tt = bp.get_insensitive(glob_section, "targetType")
    if tt is not None:
        tt = tt.lower()
        if tt == "cordova-ios":
            target_type = TargetType.CORDOVA
            platform_type = PlatformType.IOS
        if tt == "cordova-android":
            target_type = TargetType.CORDOVA
            platform_type = PlatformType.ANDROID
        if tt == "ionic-ios":
            raise 'Code Lifting Detection is not supported by "Ionic-iOS" target.'
        if tt == "ionic-android":
            raise 'Code Lifting Detection is not supported by "Ionic-Android" target.'
        if tt == "nativescript-ios":
            target_type = TargetType.NATIVE_SCRIPT
            platform_type = PlatformType.IOS
        if tt == "nativescript-android":
            target_type = TargetType.NATIVE_SCRIPT
            platform_type = PlatformType.ANDROID
        if tt == "reactnative-ios":
            target_type = TargetType.REACT_NATIVE
            platform_type = PlatformType.IOS
        if tt == "reactnative-android":
            target_type = TargetType.REACT_NATIVE
            platform_type = PlatformType.ANDROID
    if target_type is None:
        ERROR("Provided protect-hybrid-js blueprint does not contain valid 'targetType' setting: "
              + args.blueprint_for_hybrid)

    if bp_seed is None :
        bp_seed = int(time.time())
        print("Seed generated:", bp_seed)
    else:
        print("Seed extracted from blueprint:", bp_seed)
    seed(bp_seed)

    project_path = args.project
    if not os.path.exists(project_path):
        ERROR("Could not find the specified project directory: {} .".format(project_path))

    if target_type == TargetType.CORDOVA:
        plugin_obj = CordovaPlugin(project_path, app_id, script_path, platform_type)
    if target_type == TargetType.NATIVE_SCRIPT:
        plugin_obj = NativeScript(project_path, app_id, script_path, platform_type)
    if target_type == TargetType.REACT_NATIVE:
        plugin_obj = ReactNative(project_path, app_id, script_path, platform_type)
    plugin_obj.install()

    if platform_type == PlatformType.IOS:
        update_xcode(args, target_type, plugin_obj.class_name, plugin_obj.function_name, bp_seed)

    print('Digital.ai Hybrid JavaScript Protection Code Lifting Detection Plugin Installation - finish')


if __name__ == "__main__":
    script_path = Path(sys.path[0])
    execute(script_path)
    exit(0)
