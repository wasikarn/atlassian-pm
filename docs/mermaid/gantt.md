# Gantt Diagrams

> A Gantt chart is a type of bar chart that illustrates a project schedule and the amount of time it would take for any one project to finish. Gantt charts illustrate number of days between the start and finish dates of the terminal elements and summary elements of a project.

## Note to Users

- When dates specific to a task are "excluded", the chart extends the task by an equal number of days to the right (no gap inside the task).
- If excluded dates are between two consecutive tasks, they are skipped graphically and left blank.

## Basic Example

```mermaid
gantt
    title A Gantt Diagram
    dateFormat YYYY-MM-DD
    section Section
        A task          :a1, 2014-01-01, 30d
        Another task    :after a1, 20d
    section Another
        Task in Another :2014-01-12, 12d
        another task    :24d
```

## Syntax

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title       Adding GANTT diagram functionality to mermaid
    excludes    weekends
    %% (`excludes` accepts specific dates in YYYY-MM-DD format, days of the week ("sunday") or "weekends", but not the word "weekdays".)

    section A section
    Completed task            :done,    des1, 2014-01-06,2014-01-08
    Active task               :active,  des2, 2014-01-09, 3d
    Future task               :         des3, after des2, 5d
    Future task2              :         des4, after des3, 5d

    section Critical tasks
    Completed task in the critical line :crit, done, 2014-01-06,24h
    Implement parser and jison          :crit, done, after des1, 2d
    Create tests for parser             :crit, active, 3d
    Future task in critical line        :crit, 5d
    Create tests for renderer           :2d
    Add to mermaid                      :until isadded
    Functionality added                 :milestone, isadded, 2014-01-25, 0d

    section Documentation
    Describe gantt syntax               :active, a1, after des1, 3d
    Add gantt diagram to demo page      :after a1  , 20h
    Add another diagram to demo page    :doc1, after a1  , 48h
```

Tasks are by default sequential. A task start date defaults to the end date of the preceding task.

A colon, `:`, separates the task title from its metadata. Metadata items are separated by a comma, `,`. Valid tags are `active`, `done`, `crit`, and `milestone`. Tags are optional, but if used, they must be specified first.

After processing the tags, the remaining metadata items are interpreted as follows:

1. If a single item is specified, it determines when the task ends. It can either be a specific date/time or a duration. If a duration is specified, it is added to the start date of the task.
2. If two items are specified, the last item is interpreted as above. The first item can either specify an explicit start date/time or reference another task using `after <otherTaskID>`.
3. If three items are specified, the last two will be interpreted as above. The first item will denote the ID of the task.

### Task Metadata Reference

> *All date values are interpreted using `dateformat`.*

| Metadata syntax                                      | Start date                                          | End date                                              | ID       |
| ---------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------- | -------- |
| `<taskID>, <startDate>, <endDate>`                   | *startdate*                                         | *endDate*                                             | `taskID` |
| `<taskID>, <startDate>, <length>`                    | *startdate*                                         | Start date + `length`                                 | `taskID` |
| `<taskID>, after <otherTaskId>, <endDate>`           | End date of previously specified task `otherTaskID` | *endDate*                                             | `taskID` |
| `<taskID>, after <otherTaskId>, <length>`            | End date of previously specified task `otherTaskID` | Start date + `length`                                 | `taskID` |
| `<taskID>, <startDate>, until <otherTaskId>`         | *startdate*                                         | Start date of previously specified task `otherTaskID` | `taskID` |
| `<taskID>, after <otherTaskId>, until <otherTaskId>` | End date of previously specified task `otherTaskID` | Start date of previously specified task `otherTaskID` | `taskID` |
| `<startDate>, <endDate>`                             | *startdate*                                         | *enddate*                                             | n/a      |
| `<startDate>, <length>`                              | *startdate*                                         | Start date + `length`                                 | n/a      |
| `after <otherTaskID>, <endDate>`                     | End date of previously specified task `otherTaskID` | *enddate*                                             | n/a      |
| `after <otherTaskID>, <length>`                      | End date of previously specified task `otherTaskID` | Start date + `length`                                 | n/a      |
| `<startDate>, until <otherTaskId>`                   | *startdate*                                         | Start date of previously specified task `otherTaskID` | n/a      |
| `after <otherTaskId>, until <otherTaskId>`           | End date of previously specified task `otherTaskID` | Start date of previously specified task `otherTaskID` | n/a      |
| `<endDate>`                                          | End date of preceding task                          | *enddate*                                             | n/a      |
| `<length>`                                           | End date of preceding task                          | Start date + `length`                                 | n/a      |
| `until <otherTaskId>`                                | End date of preceding task                          | Start date of previously specified task `otherTaskID` | n/a      |

> Support for keyword `until` was added in v10.9.0+

### Title

The `title` is an *optional* string to be displayed at the top of the Gantt chart.

### Excludes

The `excludes` is an *optional* attribute that accepts specific dates in YYYY-MM-DD format, days of the week ("sunday") or "weekends", but not the word "weekdays". These dates will be marked on the graph and excluded from duration calculation.

#### Weekend (v11.0.0+)

When excluding weekends, configure start day with the `weekend` attribute (`friday` or `saturday`). Default is Saturday and Sunday.

```mermaid
gantt
    title A Gantt Diagram Excluding Fri - Sat weekends
    dateFormat YYYY-MM-DD
    excludes weekends
    weekend friday
    section Section
        A task          :a1, 2024-01-01, 30d
        Another task    :after a1, 20d
```

### Section Statements

Divide the chart into sections with the `section` keyword followed by a name (required).

### Milestones

Milestones represent a single instant in time. Use the `milestone` tag. Location = *initial date* + *duration*/2.

```mermaid
gantt
    dateFormat HH:mm
    axisFormat %H:%M
    Initial milestone : milestone, m1, 17:49, 2m
    Task A : 10m
    Task B : 5m
    Final milestone : milestone, m2, 18:08, 4m
```

### Vertical Markers

The `vert` keyword adds vertical reference lines at specific dates (don't take up a row).

```mermaid
gantt
    dateFormat HH:mm
    axisFormat %H:%M
    Initial vert : vert, v1, 17:30, 2m
    Task A : 3m
    Task B : 8m
    Final vert : vert, v2, 17:58, 4m
```

## Setting Dates

### Input Date Format

The default input date format is `YYYY-MM-DD`. You can define your custom `dateFormat`.

Uses [day.js format tokens](https://day.js.org/docs/en/parse/string-format). Common tokens:

| Token | Example | Description |
| --- | --- | --- |
| `YYYY` | 2014 | 4-digit year |
| `MM` | 01-12 | Month |
| `DD` | 01-31 | Day |
| `HH:mm` | 23:59 | Hour:Minute |

Full reference: [day.js format docs](https://day.js.org/docs/en/parse/string-format)

### Output Date Format on the Axis

The default output date format is `YYYY-MM-DD`. You can define your custom `axisFormat`.

Uses [d3-time-format tokens](https://github.com/d3/d3-time-format). Common tokens:

| Token | Description |
| --- | --- |
| `%Y` | 4-digit year |
| `%m` | Month (01-12) |
| `%d` | Day (01-31) |
| `%H:%M` | Hour:Minute (24h) |

Full reference: [d3-time-format docs](https://github.com/d3/d3-time-format)

### Axis Ticks (v10.3.0+)

The default output ticks are auto. You can customize with `tickInterval`, like `1day` or `1week`.

Pattern: `/^([1-9][0-9]*)(millisecond|second|minute|hour|day|week|month)$/`

Week-based `tickInterval`s start on Sunday by default. Use the `weekday` option to change:

```mermaid
gantt
  tickInterval 1week
  weekday monday
```

> `millisecond` and `second` support was added in v10.3.0

## Compact Mode

Display multiple tasks in the same row by setting `displayMode: compact` via YAML frontmatter.

```mermaid
---
displayMode: compact
---
gantt
    title A Gantt Diagram
    dateFormat  YYYY-MM-DD

    section Section
    A task           :a1, 2014-01-01, 30d
    Another task     :a2, 2014-01-20, 25d
    Another one      :a3, 2014-02-10, 20d
```

## Comments

Comments need to be on their own line and must be prefaced with `%%` (double percent signs).

## Today Marker

Style it with:

```
todayMarker stroke-width:5px,stroke:#0f0,opacity:0.5
```

Hide it with:

```
todayMarker off
```

## Configuration

```javascript
mermaid.ganttConfig = {
  titleTopMargin: 25,
  barHeight: 20,
  barGap: 4,
  topPadding: 75,
  rightPadding: 75,
  leftPadding: 75,
  gridLineStartPadding: 10,
  fontSize: 12,
  sectionFontSize: 24,
  numberSectionStyles: 1,
  axisFormat: '%d/%m',
  tickInterval: '1week',
  topAxis: true,
  displayMode: 'compact',
  weekday: 'sunday',
};
```

## Interaction

Bind click events to tasks (requires `securityLevel='loose'`):

```
click taskId call callback(arguments)
click taskId href URL
```

## Bar Chart Example (using gantt)

```mermaid
gantt
    title Git Issues - days since last update
    dateFormat X
    axisFormat %s
    section Issue19062
    71   : 0, 71
    section Issue19401
    36   : 0, 36
    section Issue193
    34   : 0, 34
    section Issue7441
    9    : 0, 9
    section Issue1300
    5    : 0, 5
```
