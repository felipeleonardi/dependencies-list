#Grunt

![Grunt logo](https://gruntjs.com/img/og.png)

When integrating SecureJS with Grunt, it is advised you run SecureJS at the last step otherwise you risk further transforming the Javascript. Further transformation of the Javascript after SecureJS has run will affect checksums.

### Integration

Here is an example of how you might integrate SecureJS with Grunt.

##### Plugin Load Code
```
grunt.loadNpmTasks('grunt-bg-shell');
grunt.loadNpmTasks('grunt-contrib-copy');
grunt.loadNpmTasks('grunt-contrib-clean');
```
##### Plugin Configuration
```
bgShell: {
  _defaults: {
    bg: false
  },
  buildOutDir: {
    cmd: `md out`,
  },
  runSjs: {
    cmd: `${secureJsPath} -if . -of ../out`,
    execOpts: {
      cwd: './input'
    }
  }
}
```
