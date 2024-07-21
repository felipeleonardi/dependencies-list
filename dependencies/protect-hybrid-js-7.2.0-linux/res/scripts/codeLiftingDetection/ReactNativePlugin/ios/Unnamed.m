#import "CLASS_NAME.h"


void tamperAction () {}

@implementation CLASS_NAME: NSObject

int hash_value = HASH_VALUE;
int b_value = B_VALUE;
int tamper_value = 0;

RCT_EXPORT_MODULE();

RCT_EXPORT_METHOD(FUNCTION_NAME:(int) a :(int) c :(RCTResponseSenderBlock)callback){
    NSString* salt = [self genRandString:5];
    int hashSecret = [self javaHashCode:[NSString stringWithFormat:@"%d", (a + b_value + c)]] + [self javaHashCode:[NSString stringWithFormat:@"%@", salt]];
    if ((tamper_value + hash_value + [self javaHashCode:[NSString stringWithFormat:@"%@", salt]]) == hashSecret) {
        callback(@[[@(hashSecret) stringValue], salt, [@((a + b_value)) stringValue]]);
    } else {
        callback(@[[@(0) stringValue], @"0", [@(0) stringValue]]);
    }
}

- (int)javaHashCode:(NSString*)str {
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

