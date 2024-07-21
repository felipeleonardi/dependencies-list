#!/usr/bin/env node
//--------------------------------------------------------------------------------------------------------
//
// Digital.ai Hybrid JavaScript Protection
// ===============================
//
// 'after_prepare' hook for Digital.ai Hybrid JavaScript Protection.
//
//--------------------------------------------------------------------------------------------------------
//
// To setup, make sure that protect-hybrid-js is in PATH and copy this script to the scripts directory at the root of your project.
//
//   mkdir -p ${project_root}/scripts
//   cp scripts/protect-hybrid-js.js ${project_root}/scripts
//
// Add the below to ${project_root}/config.xml file.
//   <hook src="scripts/protect-hybrid-js.js" type="after_prepare" />
//
//--------------------------------------------------------------------------------------------------------
//
// This hook invokes protect-hybrid-js before the assets are packaged for deployment. By default, this will
// obfuscate everything in your project's 'www' folder at the deployment location.
//
//--------------------------------------------------------------------------------------------------------

// Modules
var fs    = require('fs');
var path  = require('path');
var spawn = require('child_process').spawnSync;

//--------------------------------------------------------------------------------------------------------

module.exports = function(context)
{
	// Process
	var rootDir        = context.opts.projectRoot;
	var platformPath   = path.join(rootDir, 'platforms');
	var platforms      = context.opts.platforms;

	// Hook configuration
	var configFilePath = path.join(rootDir, 'protect-hybrid-js.blueprint');
	var altConfigFilePath = path.join(rootDir, 'a4hybrid.blueprint');

	platforms.forEach(function(platform)
	{
		var wwwPath;
		var targetType;
		var execType;

		switch (platform)
		{
			case 'android':
				targetType = 'cordova-android';
				execType = 'protect-hybrid-js';
				wwwPath = path.join(platformPath, platform, 'app', 'src', 'main', 'assets');
				if (!fs.existsSync(wwwPath)) // older versions used a different folder
					wwwPath = path.join(platformPath, platform, 'assets');
				break;

			case 'ios':
				targetType = 'cordova-ios';
				execType = 'protect-hybrid-js';
				wwwPath = path.join(platformPath, platform);
				break;

			case 'browser':
				targetType = 'browser';
				execType = 'protect-web';
				wwwPath = path.join(platformPath, platform);
				break;

			default:
				throw new Error('The Digital.ai Hybrid JavaScript Protection hook only supports \'android\', \'ios\' and \'browser\' currently.');
		}

		processFolders(wwwPath, targetType, execType, configFilePath, altConfigFilePath);
	});
};

//--------------------------------------------------------------------------------------------------------

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

//--------------------------------------------------------------------------------------------------------

function processFolders(base, targetType, execType, configFilePath, altConfigFilePath)
{
	var wwwPath = base + "/www";
	var wwwObfuscated = wwwPath + "_obfuscated";
	var executable = process.platform === 'win32' ? (execType + '.exe') : execType;

	// Create dir if it doesn't exist
	if (!fs.existsSync(wwwObfuscated))
		fs.mkdirSync(wwwObfuscated);

	// Build commandline
	var config = fs.existsSync(configFilePath) ? (" -b \"" + configFilePath + "\"") : (fs.existsSync(altConfigFilePath) ? (" -b \"" + altConfigFilePath + "\"") : "");
	var cmd = `"${executable}" -i "${wwwPath}" -o "${wwwObfuscated}"${config} -t ${targetType}`;

	// Execute Digital.ai Hybrid JavaScript Protection on this path
	console.log('Running Digital.ai Hybrid JavaScript Protection: \n  ' + cmd);
	var execProcess = spawn(cmd, { shell: true, stdio: "inherit"});

	if (execProcess.status !== 0)
		process.exit(execProcess.status);

	// delete original content path
	recursiveDelete(wwwPath);

	// Move obfuscated dir to real path
	fs.renameSync(wwwObfuscated, wwwPath);
}
