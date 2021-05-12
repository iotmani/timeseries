# Logs Monitor 2000
Monitor your HTTP logs for interesting statistics, or keep an eye on unusual traffic levels.


## Usage
No additional libraries are needed to run the log monitor. Tested with Python 3.8.1.

Simply pass a log file:

`python -m LogsMonitor2000 tests/small_sample_csv.txt`

For more options see help:

```python -m LogsMonitor2000 --help```


## Development

Testing
--------

To run unit-tests:

`python -m unittest`


We use the following packages during development:
*  'black' for standardizing and auto-formatting any code changes you make in your IDE of choice, 
*  'coverage' for unit-test coverage reports,
*  'mypy' for static type checking based on type-annotations.

Create a virtual environment:
```
virtualenv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
```

Code coverage:

`coverage run --omit '*/.venv/*,*/tests/*' -m unittest`

Generate test-coverage report (html optional):

`coverage report`

```
$ coverage report
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
LogsMonitor2000\__init__.py                 0      0   100%
LogsMonitor2000\action.py                  20      0   100%
LogsMonitor2000\analyze\__init__.py         1      0   100%
LogsMonitor2000\analyze\calculator.py      88      0   100%
LogsMonitor2000\analyze\processor.py       37      0   100%
LogsMonitor2000\event.py                   26      0   100%
LogsMonitor2000\parse.py                   68     19    72%
-----------------------------------------------------------
TOTAL                                     240     19    92%
```

Mypy:

`mypy LogMonitor2000`

Profilng:

`python -m profile -s 'tottime' -m LogsMonitor2000 tests/sample_csv.txt`

Then `deactivate` when done.


Architecture
------------

This is made of a parser, analyzer and action modules.
Each part tries to do one thing and passes data to the next stage thanks to forward-dependency and dependency-injection (Inversion of Control).

This way, an Action to display to terminal doesn't do any data analysis, the processor doesn't care whether events were HTTP logs or information brought by piegeon, the parser does just the input reading and sanitation. 

The modules are split into the three stages below, in addition to an Event class used for simple message passing.

**Parse**

The HTTPLogParser class parses a HTTP log file (*gasp!*) while skipping any invalid lines as best-effort, and generates events to analyse.

Additional protocols or sources can just implement the Parser interface.

**Analyze**

AnalyticsProcessor class collects sourced log events and uses statistics to determine e.g. if there's a high level of traffic within the past x minutes. If so, it generates a traffic events that need to be actioned somehow.

Other 'Processor' classes can be implemented, such as persisting the data into a time-series database.

**Action**

The TerminalNotifier action class displays the calculated statistics and important information like high-traffic alerts in the screen.

Other 'Action' classes can be implemented such as sending an email notification, or calling an external API.


**Scaling**
Turn each of the parser/processor/action into a separate microservice, kafka-connected. 
Parse and process sets of logs ingested from multiple server machines, sent possibly using the syslog protocol.
Persist outputs from each step in a timeseries-db potentially for dynamic querying or further processing.

We can add the support of multiple processors/actions instances to notify in a publish-subscribe form as the project grows.
