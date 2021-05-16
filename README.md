# Logs Monitor 2000
Monitor your HTTP logs for interesting statistics, and get alerted on unusual traffic levels.

## Usage
No additional libraries are needed to run the log monitor. Tested with Python 3.8.1 and 3.9.4.

Simply pass a log file:

`python -m LogsMonitor2000 tests/small_sample_csv.txt`

For more options see help:

```
python -m LogsMonitor2000 --help

usage: __main__.py [-h] [--verbose] [--stats_interval STATS_INTERVAL]
                   [--high_traffic_interval HIGH_TRAFFIC_INTERVAL]
                   [--high_traffic_threshold HIGH_TRAFFIC_THRESHOLD]
                   [--follow]
                   file

Parse HTTP logs and monitor traffic

positional arguments:
  file                  HTTP log path, e.g. tests/sample_csv.txt

optional arguments:
  -h, --help            show this help message and exit
  --verbose             Print DEBUG lines
  --stats_interval STATS_INTERVAL
                        Print general requests statistics every x seconds
  --high_traffic_interval HIGH_TRAFFIC_INTERVAL
                        Monitor high traffic over window size of x seconds
  --high_traffic_threshold HIGH_TRAFFIC_THRESHOLD
                        Number of requests to exceed within that interval in
                        order to trigger an alert
  --follow              Continuously watch file for updates, similar to `tail
                        --follow`

```

**Troubleshooting**

* "No module named LogsMonitor2000/" -> Remove "/" when running the application.
* "Relative module names not supported" -> Remove any "./" preceeding the module name, like so: `python -m LogsMonitor2000 -h`


## Development

**Testing**

To run unit-tests:

`python -m unittest`


We use the following packages during development:
*  'black' for standardizing and auto-formatting any code changes you make in your IDE of choice, 
*  'coverage' for unit-test coverage reports,
*  'mypy' for static type checking based on type-annotations.

Create a virtual environment:
```
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
```

**Code coverage**

`coverage run --omit '*/.venv/*,*/tests/*' -m unittest`

Generate test-coverage `report` (or `html`):

`coverage report`

```
$ coverage report
Name                                               Stmts   Miss  Cover
----------------------------------------------------------------------
LogsMonitor2000\__init__.py                            0      0   100%
LogsMonitor2000\action.py                             21      0   100%
LogsMonitor2000\analyze\__init__.py                    1      0   100%
LogsMonitor2000\analyze\calculator.py                 26      0   100%
LogsMonitor2000\analyze\highTrafficCalculator.py      34      0   100%
LogsMonitor2000\analyze\mostCommonCalculator.py       38      0   100%
LogsMonitor2000\analyze\processor.py                  63      0   100%
LogsMonitor2000\event.py                              26      0   100%
LogsMonitor2000\parse.py                              66      7    89%
----------------------------------------------------------------------
TOTAL                                                275      7    97%
```

**Mypy for type-checking**

`mypy LogsMonitor2000`

`Success: no issues found in 10 source files`

**Profilng**

`python -m profile -s 'tottime' -m LogsMonitor2000 tests/sample_csv.txt`


Then `deactivate` when done.


Architecture
------------

This is made of a parse, analyze and action modules.
Each part does one thing and sends a message to the next step thanks to forward-dependency and dependency-injection (Inversion of Control), each part communicates via an high-level interface and it's the responsibility of the main class to link them together more concretely.

This way, an Action to display to terminal doesn't do any data analysis, the processor doesn't care whether events were HTTP logs or information brought by piegeons, the parser does just the file reading and sanitation. 

The analyze module instantiates is the core of this project, and uses instances of 'stream calculators', each of which defines a sliding-window length and consumes web log events as they come in as a stream and generates alerts for the Action as appropriate.

The modules are split into the three stages below, in addition to an Event class used for simple message passing.

**Parse**

The HTTPLogParser class parses a HTTP log file (*gasp!*) while skipping any invalid lines for best-effort, and generates events to analyse.

Additional protocols or sources can just implement the Parser interface.

**Analyze**

AnalyticsProcessor class collects sourced log events and uses statistics to determine e.g. if there's a high level of traffic within the past x minutes. If so, it generates a High Traffic alert that need to be actioned by the Action module instance.

*Out-of-order buffering*:

Events can come out-of-order, e.g. due to a multi-threaded HTTP server, and are buffered for 2 seconds by default (can be made configurable by the analyze.py self._BUFFER_TIME constant).
This is so that an event at time T4 won't trigger the wrong "most common stats" when a number of event at time T3 occurs just after it.
We assume that 2 seconds is enough time, and anything after that is dropped for being too late as we're processing logs in our own machine and not from external servers where network lag goes beyond that.
The buffer is fully flushed once we reach the end-of-file.
This buffering results in an equivalent processing if they were in-order, but just introduce a delay to the final outcome.

Events are buffered and efficiently ordered by time using a heap, then once past the buffer time (2s default) they're processed as a group of events for each second into a queue (for efficient removal from front and insert at back).
Grouping events per second allows very fast processing as a batch, since that's the finest granularity for the interval and alerting threshold parameters.
Moreover, all calculators share the same memory and but their count()/discount() functions are called only when log events enter/exit their individual sliding windows.

Other 'Processor' classes can be implemented, such as persisting the parsed raw data into a time-series database.
Further 'StreamCalculator' classes can be implemented, such as keeping track of the errors per time of day...

**Action**

The TerminalNotifier action class displays the calculated statistics and important information like high-traffic alerts in the screen.

Other 'Action' classes can be implemented such as sending an email notification, or calling an external API.


**Further improvements**

* Multithreadding can be used to process events for each calculator in parallel without adding too much complexity. 

* Python's deque is thread-safe, so we can multithread both  removals and inserts of the collected events that come out of the buffer.
We'll need to synchronize before trigering notification to prevent miscalculations, as otherwise the sliding window can have the wrong length if e.g. we add the new and we call notify before removing the old events shrinking the window size temporarily.

* We can easily add the support of multiple Processor/Action instances to notify in a publish-subscribe form as the project grows.

* Store references to start time of each calculator to know exactly when to advance its start.

Scaling
--------

* Turn each of the parser/processor/action into separate microservices, kafka-connected, with WebLogEvent as the protocol buffer message. Scale instances of each appropriately to avoid idling or contention.

* We can then parse and process sets of logs ingested from multiple server machines, sent possibly using the syslog protocol.
* Give each message a sequence order, which can be useful for idempotence later.
* Persist outputs from each step in a timeseries-db potentially for dynamic querying or further processing.

* For ordering of events (i.e. scaling of the above buffering), another dedicated miscro-server can consume parsed events and use an in-memory datastore like Redis to temporarily store events grouped per second as they come in (or whichever resolution level we'd like). 
* Then once retrieve and delete all from e.g. over 2 seconds ago, to be passed on to the 'processor' for calculations or as Spark batch jobs.
* In the case of Redis failure, we can rebuild it from replaying Kafka messages (i.e. store more than 2 seconds worth of parsed log event streams). Idempotence is essential for easier maintenance/recovery, so that reprocessing already parsed events ends up in the same state at each stage.


Take home Project note
----------------------
I spent a cumulative time of 2 - 3 weeks on this project, ~40% of that was as an opportunity to learn parts of the Python ecosystem I was missing (e.g. project structure, unconventional builtin data structures and algorithms, mypy, best practices, unit-testing, mocking built-in functions...etc). The rest was mostly on reworking the project once I clarified we need to support out-of-order events, and improving performance while keeping code complexity low.
Thank you! I really enjoyed working on this!
PS: .git folder was left intentionally for added history on the repo development.