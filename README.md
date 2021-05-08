# Logs Monitor 2000
Monitor your HTTP logs for interesting statistics, or keep an eye on unusual traffic levels.


## Usage
No additional libraries are needed to run the log monitor. Tested with Python 3.8.1.

Simply pass a log file:

`python LogsMonitor2000.py tests/small_sample_csv.txt`

For more options see help:

```python LogsMonitor2000.py --help```


## Development

Testing
--------

To run unit-tests:

`python -m unittest`


We use the following packages during development:
*  'black' for standardizing and auto-formatting any code changes you make in your IDE of choice, 
*  'coverage' for unit-test coverage reports,
*  'mypy' for static type checking based on type-annotations.

`pip install black coverage mypy`

Alternatively, just create a virtual environment:
```
virtualenv venv
source venv/Scripts/activate
pip install -r requirements-dev.txt
```

Run code coverage:

`coverage run --omit '*/venv3/*,*/tests/*' -m unittest`

Generate test-coverage report (html optional):

`coverage report`

```
$ coverage report
Name         Stmts   Miss  Cover
--------------------------------
action.py       14      0   100%
analyze.py      42      0   100%
event.py        26      1    96%
--------------------------------
TOTAL           82      1    99%
```

Mypy:

`mypy LogMonitor2000.py`

Profilng:

`python -m profile -s 'tottime' LogsMonitor2000.py tests/sample_csv.txt`

Then `deactivate` when done.


Architecture
------------

This is made of a parser, analyzer and action modules.
Each part tries to do one thing and passes data to the next stage thanks to forward dependency and dependency injection.

This way, an Action to display to terminal doesn't do any data analysis, the processor doesn't care whether events were HTTP logs or information brought by piegeon, the parser does just the input reading and sanitation. 

The modules are split into the three stages below, in addition to an Event class used for simple message passing.

**Parse**

The HTTPLogParser class parses a HTTP log file (*gasp!*) while skipping any invalid lines as best-effort, and generates events to analyse.

Additional protocols or sources can just implement the Parser interface.

**Analyze**

StatsProcessor class collects sourced log events and uses statistics to determine e.g. if there's a high level of traffic within the past x minutes. If so, it generates a traffic events that need to be actioned somehow.

Other 'Processor' classes can be implemented, such as persisting the data into a time-series database.

**Action**

The TerminalNotifier action class displays the calculated statistics and important information like high-traffic alerts in the screen.

Other 'Action' classes can be implemented such as sending an email notification, or calling an external API.


We can easily add e.g. multiple processors/actions instances to notify in a publish-subscribe form as the project grows.
