# HTTP Traffic monitor
Monitor your HTTP logs and keep an eye on statistics or unusual traffic levels.


Installation
============

You do not need additional libraries to run the log monitor, just see:

```python main.py --help```

Example:

`python main.py --log path/to/http.csv`



Development
======

Testing
-------

To run tests, you'll need python plugins 'pytest' and optionally 'black' for standardizing and auto-formatting any code changes you make.

`pip install pytest black`

Alternatively, just create a virtual environment:
```
virtualenv venv
source venv/Scripts/activate
pip install -r requirements.txt
```
Then `deactivate` when done.

Architecture
------------

This is made of a parser, analyzer and action modules, with forward dependency. 
Each part tries to do one thing and passes data to the next stage.


**Parser**

Parses a log file while skipping any invalid lines, and generates events to analyse.

Additional protocols or sources can just implement the Parser interface

**Analyze**

Collects log events and applies statistics to determine e.g. if there's a high level of traffix within the past x minutes. If so, it generates a traffic events that need to be actioned some-how.


**Action**

Displays general statistics and important information like high-traffic alerts in the screen.
Other actions can be implemented such as sending an email or triggering oncall for example.

