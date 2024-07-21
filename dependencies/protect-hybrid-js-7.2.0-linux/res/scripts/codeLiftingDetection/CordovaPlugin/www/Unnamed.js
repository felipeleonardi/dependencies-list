var exec = require('cordova/exec');

exports.FUNCTION_NAME = function (arg0, arg1, success, error) {
    exec(success, error, 'CLASS_NAME', 'FUNCTION_NAME', [arg0, arg1]);
};
