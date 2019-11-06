import pandas as pd
import zipfile
import numpy as np
import math
import json
import functools
import sys
import pdfkit

SID_COLUMN = 3
NAME_COLUMN = 2
RUBRIC_PREVIOUS_COLUMN_NAME = "Submission Time"
POINT_VALUES_FIRST_COLUMN = 6
OUTPUT_DIR = "outputs"

class Student:
    def __init__(self, sid = None, name = ""):
        self.sid = sid
        self.name = name
        self.totalScore = 0
        self.parts = {}
        self.qscores = {}
        self.logs = []
        self.tutorial = "XXX"

class QScore:
    def __init__(self):
        self.question = None
        self.score = None
        self.applied_rubrics = []
        self.adjustment = None
        self.comment = None

class Question:
    def __init__(self):
        self.name = ""
        self.max_pts = 0
        self.rubrics = []
        self.students = []
    def show(self):
        print("Question:", self.name)
        print("  - max points:", self.max_pts)
        for r in self.rubrics:
            print("  - ", r.name, " / ", r.deduction)

class LogEntry:
    def __init__(self, qname="", type=""):
        self.question = qname
        self.type = type
        self.comments = []
    def __repr__(self):
        return f"(Entry {self.question}, {self.type}, {self.comments})"

def split_question_name(qname):
    p = qname.split(" ")
    print("p =", p)

class Rubric:
    def __init__(self, name = "", deduction = 0):
        self.name = name
        self.deduction = deduction

def get_question_name( fname):
    assert fname.endswith(".csv")
    qname = fname[:-4]
    ind = qname.rfind("/")
    if ind != -1:
        qname = qname[ind+1:]
    ind = qname.rfind("_")
    if ind != -1:
        qname = qname[ind+1:]
    else:
        qname = f"[{qname}]"
    return qname

def process_question( fname, df):
    print("Processing question in ", fname)
    assert df.columns[0] == "Assignment Submission ID"
    assert df.columns[NAME_COLUMN] == "Name"
    assert df.columns[SID_COLUMN] == "SID"
    q = Question()
    question_name = get_question_name(fname)
    q.name = question_name
    # print( fname, " => ", q.name)
    ptVals = find_row( df, "Point Values")[1:] # get point values
    ptVals = filter( lambda v: v == v, ptVals) # get rid of nans
    ptVals = list(ptVals)

    assert len(ptVals) > 0
    max_pts = float(ptVals[0])
    q.points = max_pts
    rubric_type = find_row( df, "Rubric Type")[1]
    assert rubric_type == "negative"
    n_rubrics = len(ptVals) - 1

    rubric_values = list(map(float, ptVals[1:]))
    # print("rubric_values=", rubric_values)
    assert max(rubric_values) <= max_pts
    cols = list(df.columns)

    # figure out which column is for first rubric name
    rubric_col1 = cols.index( "Submission Time") + 1

    rubric_names = cols[rubric_col1:rubric_col1+n_rubrics]
    # print("rubric_names=", rubric_names)

    score_col = cols.index("Score")
    comments_col = cols.index("Comments")
    adjustment_col = cols.index("Adjustment")
    for rn in range( 0, len(ptVals) - 1):
        rubric = Rubric( cols[rubric_col1 + rn], ptVals[1 + rn])
        q.rubrics.append( rubric)

    questions.append(q)
    q.show()

    split_question_name(q.name)

    # process every student for this question
    for row in df.values:
        if not row[0].isdigit():
            continue
        sid = row[SID_COLUMN] # student ID
        name = row[NAME_COLUMN] # student name
        print("Processing student", name)
        student = students.get( sid, Student(sid, name))
        students[sid] = student

        log = LogEntry(question_name, "total")
        log.comments.append(f"{row[score_col]} / {max_pts}")
        student.logs.append(log)

        deduction_total = 0

        for r in range(0,n_rubrics):
            assert row[rubric_col1 + r] in ["true","false"]
            if row[rubric_col1 + r] == "true":
                deduction_total += rubric_values[r]
                if(rubric_values[r] == 0 and rubric_names[r].lower() == "correct"):
                    continue
                log = LogEntry(question_name, "deduction")
                # comment = f"{-rubric_values[r]}: {rubric_names[r]}"
                # log.comments.append(comment)
                log.comments.append(f"{-rubric_values[r]}")
                log.comments.append(f"{rubric_names[r]}")

                # print("Comment=", comment)
                # print("log:", log)

                student.logs.append(log)

        adjustment = 0
        if( row[adjustment_col] == row[adjustment_col]):
            adjustment = float(row[adjustment_col])
        # print("adjustement=", adjustment, type(adjustment))
        comment = row[comments_col]
        if comment != comment:
            comment = ""
        if adjustment or comment:
            if adjustment == 0:
                log = LogEntry( question_name, "warning")
            elif adjustment < 0:
                log = LogEntry( question_name, "deductionn")
            else:
                log = LogEntry( question_name, "bonus")
            log.comments.append(f"{adjustment}")
            log.comments.append(f"{comment}")
            student.logs.append(log)

        # print("student log=", student.logs)

        # print("deuction_total before adjustment=", deduction_total)
        deduction_total -= adjustment
        calculated_score = max_pts - deduction_total
        suggested_score = float(row[score_col])
        # print("calc vs suggested", calculated_score, suggested_score, type(calculated_score), type(suggested_score))
        assert calculated_score == suggested_score

        #     print("+adjustment=", adjustment, comment, type(comment))
        # else:
        #     print("-adjustment=", adjustment, comment, type(comment))

        score = QScore()
        score.question = q
        score.score = row[score_col]
        score.adjustment = row[adjustment_col]
        score.comment = row[comments_col]

        assert(q.name not in student.qscores)
        student.qscores[q.name] = score


def find_row( df, col1):
    for r in df.values:
        if r[0] == col1:
            return r
    assert False


def mycmp(log1, log2):
    q1,q2 = log1.question, log2.question
    q1 = q1.split(".")
    q2 = q2.split(".")
    for p1,p2 in zip(q1,q2):
        try:
            if float(p1) < float(p2):
                return -1
            if float(p1) > float(p2):
                return 1
            if p1 < p2:
                return -1
            if p1 > p2:
                return 1
        except:
            pass
    return 0


questions = []
students = {}

def usage():
    print("Usage: main evals.zip roster.[csv|xls]")
    sys.exit(-1)

def main(argv):

    if len(argv) != 3:
        usage()

    try:
        zf = zipfile.ZipFile( argv[1])
    except:
        print(f"Could not open {argv[1]}")
        sys.exit(-1)

    try:
        rosterf = pd.read_csv( argv[2])
    except:
        print(f"Could not open roster {argv[2]} as CSV")
        sys.exit(-1)

    assert zf
    for info in zf.infolist():
        if not info.filename.endswith(".csv"):
            continue
        df = pd.read_csv(zf.open(info.filename), dtype=str)
        q = process_question( info.filename, df)

    # for every student try to find their tutorial in roster
    for index, row in rosterf.iterrows():
        sid = row["ID"]
        student = students.get( sid, None)
        if student is None:
            print("roster: no student", sid)
            continue
        tutorial = row["TUT"]
        student.tutorial = tutorial
        student.name2 = row["Name"]


    for id,s in students.items():
        s.logs.sort( key=functools.cmp_to_key(mycmp))

    print("==== summary ========")
    print("len(students) = ", len(students))
    for id,s in students.items():
        print( f"{s.name} ({s.sid}) {id} {s.tutorial}")
        for l in s.logs:
            if l.type == "total":
                continue
            print("  ", l)
        
        student_name = s.name2
        student_name = student_name.replace(',', ', ')
        student_name = student_name.replace('  ', ' ')
        base_name = f"{OUTPUT_DIR}/{s.tutorial}-{student_name}-{s.sid}"
        base_name = base_name.replace(' ', '_')
        base_name = base_name.lower()
        html_fname = base_name + ".html"
        f = open( html_fname, "w")
        f.write('''<link rel="stylesheet" href="../style.css">''' + "\n")
        f.write('''<div style="height: 3em"></div>''' + "\n")
        f.write('''<div id="sinfoc">''' + "\n")
        f.write('''<div id="sinfo">''' + "\n")
        f.write(student_name + " (" + s.sid + ")")
        f.write('''<br>''' + "\n")
        f.write(s.tutorial + "\n")
        f.write('''</div>''' + "\n")
        f.write('''</div>''' + "\n")
        f.write('''<div style="height: 3em"></div>''' + "\n")
        f.write('''<table class="detailsTable">''' + "\n")
        f.write('''<thead><tr>''' + "\n")
        f.write('''<th width="10%">Question</th>''' + "\n")
        f.write('''<th width="10%">Deduction</th>''' + "\n")
        f.write('''<th>Reason</th>''' + "\n")
        f.write('''</tr></thead>''' + "\n")
        f.write('''<tbody>''' + "\n")

        for log in s.logs:
            if log.type == "total":
                continue
            if log.type == "deduction":
                f.write(f"<tr><td>{log.question}</td><td>{log.comments[0]}</td><td>{log.comments[1]}</td></tr>")
            else:
                f.write(f"<tr><td>{log.question}</td><td>{log.type}</td><td>{','.join(log.comments)}</td></tr>")
        f.write('''</tbody></table>''' + "\n")
        f.close()

        pdf_fname = base_name + ".pdf"
        # pdfkit.from_file( html_fname, pdf_fname)


if __name__ == "__main__":
    main(sys.argv)
