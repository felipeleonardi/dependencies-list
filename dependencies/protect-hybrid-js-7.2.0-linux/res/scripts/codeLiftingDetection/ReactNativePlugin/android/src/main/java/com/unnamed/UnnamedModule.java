package com.PLUGIN_NAME;

import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.Callback;
import java.util.Random;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;

public class CLASS_NAMEModule extends ReactContextBaseJavaModule {

    private final ReactApplicationContext reactContext;

    public CLASS_NAMEModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }

    @Override
    public String getName() {
        return "CLASS_NAME";
    }
    
    @ReactMethod
    public void FUNCTION_NAME(int a, int c, Callback cb) {
        pFUNCTION_NAME(a, c, cb);
    }

    private void pFUNCTION_NAME(int a, int c, Callback cb) {
        Random random = new Random();
        char[] r = new char[10];
        char[] letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".toCharArray();
        for (int i=0; i<10; i++) {
            r[i] = letters[random.nextInt(letters.length)];
        }
        String rs = new String(r);
        String sum = Integer.toString((a + B_VALUE + c));
        try {
            Method method = rs.getClass().getMethod("hashCode");
            long rsHash = Long.parseLong(method.invoke(rs).toString());
            long sumHash = Long.parseLong(method.invoke(sum).toString());
            if ((HASH_VALUE + rsHash) == sumHash + rsHash) {
                cb.invoke(Long.toString(sumHash + rsHash), rs, Integer.toString(a + B_VALUE));
            } else {
              cb.invoke("0","0","0");
            }
        } catch(IllegalArgumentException | IllegalAccessException | InvocationTargetException | NoSuchMethodException e) { cb.invoke("0","0","0"); }
    }
}
