#import <Cordova/CDV.h>

@interface CLASS_NAME : CDVPlugin {
}

- (void)FUNCTION_NAME:(CDVInvokedUrlCommand*)command;

@end

void tamperAction () {}

@implementation CLASS_NAME

int hash_value = HASH_VALUE;
int b_value = B_VALUE;
int tamper_value = 0;

- (void)FUNCTION_NAME:(CDVInvokedUrlCommand*)command
{
    NSString* salt = [self genRandString:5];
    int a = (int)[[command.arguments objectAtIndex:0] integerValue];
    int c = (int)[[command.arguments objectAtIndex:1] integerValue];
    int hashSecret = [self javaHashCode:[NSString stringWithFormat:@"%d", (a + b_value + c)]] + [self javaHashCode:[NSString stringWithFormat:@"%@", salt]];
    CDVPluginResult* pluginResult = nil;
    
    if ((tamper_value + hash_value + [self javaHashCode:[NSString stringWithFormat:@"%@", salt]]) == hashSecret) {
        pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_OK messageAsString:[NSString stringWithFormat:@"%@,%@,%@", [@(hashSecret) stringValue], salt, [@((a + b_value)) stringValue]]];
    } else {
        pluginResult = [CDVPluginResult resultWithStatus:CDVCommandStatus_ERROR];
    }

    [self.commandDelegate sendPluginResult:pluginResult callbackId:command.callbackId];
}

- (int)javaHashCode:(NSString*)str
{
    int h = 0;

    for (int i = 0; i < (int)str.length; i++) {
        h = (31 * h) + [str characterAtIndex:i];
    }

    return h;
}

- (NSString*)genRandString:(int)len {
    static NSString *letters = @"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    NSMutableString *randomString = [NSMutableString stringWithCapacity: len];
    for (int i=0; i<len; i++) {
        [randomString appendFormat: @"%C", [letters characterAtIndex: arc4random() % [letters length]]];
    }
    return randomString;
}

@end
