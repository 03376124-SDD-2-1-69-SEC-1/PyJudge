# GReader

A classroom system for programming courses at KMITL. Instructors publish
programming Assignments (drafted with AI from their lecture notes) to their
Classrooms; Students solve them and have their code judged.

## People

**Instructor**:
An account allowed to own Classrooms and author Assignments. Each Classroom has exactly one.
_Avoid_: Teacher, lecturer, owner

**Student**:
An account that joins Classrooms and submits code. Every new account starts as a Student.
_Avoid_: Learner, pupil

**Admin**:
An account that manages users, AI settings and system status; it belongs to no Classroom.
_Avoid_: Superuser, staff

**Member**:
A Student who has joined a given Classroom. The Instructor is not a Member of their own Classroom.
_Avoid_: Participant, enrollee

**Actor**:
The logged-in account on whose behalf a use case runs.
_Avoid_: Current user, principal

**Instructor request**:
A Student's application, filed at sign-up, to become an Instructor; an Admin approves or rejects it.
_Avoid_: Promotion, upgrade request

## Classrooms

**Classroom**:
One section of one course in one semester, owned by an Instructor.
_Avoid_: Class, course, room, team

**Join code**:
The six-character code a Student enters to become a Member of a Classroom.
_Avoid_: Invite code, class code, PIN

**Archived**:
A Classroom that is finished: readable, closed to joins and Submissions, and reversible.
_Avoid_: Deleted, inactive

## Assignments

**Assignment**:
A programming exercise: statement, Test Cases and judging settings. UI copy says "Problem" / "โจทย์"; code and API say Assignment.
_Avoid_: Challenge, task, question, exercise (in code)

**Posting**:
One Assignment published to one Classroom, carrying that Classroom's deadline, max score and late/resubmission policy.
_Avoid_: Classroom assignment, publication, share

**Version**:
An immutable snapshot of an Assignment's content, created at publish and at every later edit, with the reason for the change.
_Avoid_: Revision, edit, history entry

**Test Case**:
One input and its expected output, of kind sample, hidden or edge. Students see sample Test Cases in full and the rest as pass/fail only.
_Avoid_: Example, check, test (alone)

**Topic**:
The subject an Assignment practises, from one shared list.
_Avoid_: Tag, category, label

**Draft**:
An AI-generated Assignment an Instructor is still reviewing, not yet published to any Classroom.
_Avoid_: Artifact (in UI), proposal, pending assignment

**Document**:
A PDF of lecture notes in an Instructor's library, which generation may read and cite.
_Avoid_: File, upload, knowledge source (in core)

**Quota**:
The number of successful generations an Instructor may make per day.
_Avoid_: Credits, limit

## Solving

**Submission**:
A Student's code sent for grading against every Test Case of a Posting; always kept. Its ordinal number is the "attempt" shown in the UI.
_Avoid_: Attempt (as a noun for the record), answer, entry

**Run**:
An ungraded execution of a Student's code against the sample Test Cases only; never kept.
_Avoid_: Test run, trial, dry run

**Counted Submission**:
A Student's latest Submission on a Posting, on any Version; it is the grade.
_Avoid_: Final submission, best submission

**Late**:
A Submission made after the deadline on a Posting that allows late work; accepted and flagged, never penalised automatically.
_Avoid_: Overdue, tardy

**Closed**:
A Posting that accepts no more Submissions, because the Instructor closed it or its deadline passed without late work allowed.
_Avoid_: Ended, locked, expired

**Resubmit needed**:
The state of a Student whose Counted Submission is on an older Version than the current one.
_Avoid_: Outdated, stale
