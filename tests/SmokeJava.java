// Synthetic, AI-authored sample for checking that real Java inference runs.
import java.util.ArrayList;
import java.util.List;

public class SmokeJava {
    public static void main(String[] args) {
        int[] marks = {82, 91, 73, 84, 96, 77};
        List<Integer> passing = new ArrayList<>();
        int sum = 0;
        for (int value : marks) {
            sum += value;
            if (value >= 75) {
                passing.add(value);
            }
        }
        double average = (double) sum / marks.length;
        System.out.println("Average: " + average);
        System.out.println("Passing count: " + passing.size());
    }
}
