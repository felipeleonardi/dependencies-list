#Angular

![Angular logo](https://angular.io/assets/images/logos/angular/logo-nav@2x.png)

This document discusses how to get the best protection for an Angular JS project when using SecureJS.

Due to the dependency injection mechanism used by Angular JS it's global objects like `$scope`, `$http` and others cannot be renamed because they are being looked up by their original names. There are two solutions for this:

### Option 1

Add names of controllers and dependencies being injected to IdentifierRenaming's ignore list:

```"identifierRenaming" :
{
	"ignore" : [ "myController1",
                 "myController2",
                 "$scope",
                 "$http" ]
}
```

This solves the issue but leaves some code unprotected therefore the next option is recommended.


### Option 2

Instead of defining controllers this way:

##### HTML:
```
<body ng-app ng-controller="myController">
```

##### JS:
```
function myController($scope)
{
	...
}
```

They can be defined like this:

##### HTML:
```
<body ng-app="myApp" ng-controller="myController">
```
##### JS:
```
var app = angular.module("myApp", []);

app.controller("myController", ["$scope", function (anyNameForScope) { ... }
```
The latter notation allows SecureJS to safely rename controller parameters and does not require controller exclusion from ControlFlowFlattening.
