package PLUGIN_NAME;

import java.util.Random;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;

public class CLASS_NAME {

    private String pFUNCTION_NAME(int a, int c) {
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
                return "" + (sumHash + rsHash) + "," + rs + "," + apb;
            } else {
                return "0,0,0";
            }
        } catch(IllegalArgumentException | IllegalAccessException | InvocationTargetException | NoSuchMethodException e) { return "0,0,0"; }
    }

    public String FUNCTION_NAME(int a, int c) {
        return pFUNCTION_NAME(a, c);
    }
}
