#Gulp

![Gulp logo](https://raw.githubusercontent.com/gulpjs/artwork/master/gulp.png)

When integrating SecureJS with Gulp, it is advised you run SecureJS at the last step otherwise you risk further transforming the Javascript. Further transformation of the Javascript after SecureJS has run will affect checksums.

### Integration

Here is an example of how you might integrate SecureJS with Gulp.

```
var exec = require('gulp-exec');
 
var options = {
    continueOnError: false,
    pipeStdout: false,
};
exec('securejs -if input -of output', options);
```
