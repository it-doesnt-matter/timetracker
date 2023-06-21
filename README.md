# TimeTracker
A simple terminal app to keep track of what you spend your time on.  
Before you start using this tool, you should set your timezone with the [settings](#settings) command.

## Table of Contents
- [Installation](#installation)
- [Commands](#commands)
- [Settings](#settings)

## Installation
It's recommended to use [pipx](https://github.com/pypa/pipx) instead of pip to install this application, as pipx makes the app available globally without polluting the global environment and causing conflicts with other packages.
```
pipx install git+https://github.com/it-doesnt-matter/timetracker.git
```

## Commands
The commands in this section are documented using the [docopt](http://docopt.org/) language.

### create
Use this to create a new project. Projects allow us to group related tasks together.
```
timet create <project>
```

### delete
With this command you can delete tasks that are no longer needed. This will also delete all associated tasks.
```
timet delete <project>
```

### start
To start tracking your time, you can use this command. <task> doesn't need to be unique, while <project> must have been created previously with the [create](#create) command.
```
timet start <task> <project>
```

### stop
This command will stop tracking time.
```
timet stop
```

### status
If there's currently a task running, you can use this command to display information about it.  
The display option allows you to choose between two kinds of displays. The basic display is kept as simple as possible, while the fullscreen version is a bit more sophisticated and built using [Textual](https://github.com/textualize/textual/). If this is not specified, it will fall back to the settings.
```
timet status [--display basic | fullscreen]
```

### recap
This command will display an overview of finished tasks.  
<start> and <end> represent dates in the form of dd/mm/yy or dd/mm/yyyy. The recap will only include tasks that occurred during the date range described by <start> and <end>. Each of those two arguments might also be substituted with "today" or "yesterday", which will be parsed to the current date or the date of yesterday respectively. If <end> is not specified, only tasks that occurred during <start> are included. If neither <start> nor <end> are used, the tasks are not filtered by time. Lastly you can also use any combination of "last"|"this" and "week"|"month"|"year". What those combinations do should be self-explanatory.  
If you want only tasks of a certain project to be included, you can use "--project" followed by the name of the respective project.  
The recap table can be split into different sections based on the sections option. If this is not specified, it will fall back to the settings.  
When using the id flag, the table will also included the task IDs.
```
timet recap [<start>] [<end>] [--project <project>] [--sections none | days | weeks | months] [--id]
```

### export
With this command, you can export all your data to a JSON or CSV file.
```
timet export (json | csv)
```

### settings
To use this command you need to use at least one of the two following flags.  
"--set" allows you to change your current settings.  
"--list" will show a list of all settings and what they are currently set to.  
Have a look at the [settings](#settings) section, if you want to read more about what you can configure.
```
timet settings [--set <setting> <value>] [--list]
```

### edit
In case that you want to change an existing task or project, you can use this command.  
First you need to specify with the first argument whether you want to edit a task or a project.  
Then <specifier> will indicate, which task/project you want to edit. In the case of a task it should be its ID and for a project it should its name.  
<attribute> should be the attribute you want to change.--
<value> should be the new value that <attribute> should be set to.
```
timet edit [task | project] <specifier> <attribute> <value>
```

## Settings
### tz
Your timezone, which should be specified using an identifier form the [tzdata](https://tzdata.readthedocs.io/en/latest/) package, e.g. "America/New_York" or "CET".

### status
The type of status display, i.e. basic or fullscreen, that should be used by default.

### sections
This specifies the default for the type of sections into which the recap table should be split. Valid values are: "none", "days", "weeks", "years".
