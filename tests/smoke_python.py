# Synthetic, AI-authored sample for checking that real Python inference runs.
def summarize_grades(records):
    totals = {}
    for student, mark in records:
        if student not in totals:
            totals[student] = []
        totals[student].append(float(mark))
    result = []
    for student, values in sorted(totals.items()):
        total = sum(values)
        average = total / len(values)
        result.append((student, round(average, 2), average >= 75))
    return result

sample = [("Amy", 93), ("Sam", 67), ("Amy", 88), ("Sam", 74)]
for name, score, passed in summarize_grades(sample):
    print(name, score, "pass" if passed else "review")
