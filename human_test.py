# student grades program
# just trying to make this work

students = []
grades = []
a = 0

while True:
    print("\n1 add student")
    print("2 show students")
    print("3 average")
    print("4 find student")
    print("5 exit")

    x = input("choice: ")

    if x == "1":
        n = input("name: ")
        g = input("grade: ")

        try:
            g = float(g)
            students.append(n)
            grades.append(g)
            print("added")
        except:
            print("wrong grade")

    elif x == "2":
        if len(students) == 0:
            print("no students yet")
        else:
            i = 0
            while i < len(students):
                print(students[i], " - ", grades[i])
                i = i + 1

    elif x == "3":
        total = 0
        for i in range(len(grades)):
            total = total + grades[i]

        if len(grades) > 0:
            avg = total / len(grades)
            print("average is", avg)
        else:
            print("nothing to average")

    elif x == "4":
        search = input("student name: ")
        found = 0

        for i in range(len(students)):
            if students[i].lower() == search.lower():
                print("found", students[i])
                print("grade =", grades[i])
                found = 1

        if found == 0:
            print("not found")

    elif x == "5":
        print("bye")
        break

    else:
        print("invalid choice")

    a = a + 1
