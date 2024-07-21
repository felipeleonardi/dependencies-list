package cordova.plugin.PLUGIN_NAME;

import org.apache.cordova.CordovaPlugin;
import org.apache.cordova.CallbackContext;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.Random;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;

public class CLASS_NAME extends CordovaPlugin {

    @Override
    public boolean execute(String action, JSONArray args, CallbackContext callbackContext) throws JSONException {
        if (action.equals("FUNCTION_NAME")) {
            int a = args.getInt(0);
            int c = args.getInt(1);
            this.FUNCTION_NAME(a, c, callbackContext);
            return true;
        }
        return false;
    }

    private void FUNCTION_NAME(int a, int c, CallbackContext callbackContext) {
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
              int apb = a + B_VALUE;
              callbackContext.success("" + (sumHash + rsHash) + "," + rs + "," + apb);
            } else {
              callbackContext.error("");
            }
        } catch(IllegalArgumentException | IllegalAccessException | InvocationTargetException | NoSuchMethodException e) { callbackContext.error(""); }
    }
}

