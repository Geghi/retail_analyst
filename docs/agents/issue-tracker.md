# Task tracking

Tasks are plain markdown files in `.scratch/`, one file per task.
The folder is the status: `todo/`, `in-progress/`, `done/`.
Move a task with `git mv` (or `mv`) when its status changes.
File name: `<slug>.md`; first line is the title, then a short description and acceptance criteria.
No external tracker, no ticket keys, no triage labels.
`/ship` runs are not tied to a task file.
