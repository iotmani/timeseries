# Log Monitor 2000
Monitor your HTTP logs and see interesting statistics, or keep an eye on unusual traffic levels.


## Usage
No additional libraries are needed to run the log monitor.

Simply pass a log file:

`python main.py tests/small_sample_csv.txt`

For more options see help:

```python main.py --help```


## Development

Testing
--------

To run unit-tests:

`python -m unittest`


Install 'black' for standardizing and auto-formatting any code changes you make in your IDE of choice.

`pip install black`

Alternatively, just create a virtual environment:
```
virtualenv venv
source venv/Scripts/activate
pip install -r requirements.txt
```
Then `deactivate` when done.


Architecture
------------

This is made of a parser, analyzer and action modules.
Each part tries to do one thing and passes data to the next stage thanks to forward dependency and dependency injection.

This way, an Action to display to terminal doesn't do any data analysis, the processor doesn't care whether events were HTTP logs or information brought by piegeon, the parser does just the input reading and sanitation. 

**Parser**

Specifically, the HTTP Parser parses a HTTP log file while skipping any invalid lines as best-effort, and generates events to analyse.

Additional protocols or sources can just implement the Parser interface.

**Analyze**

Collects events and applies statistics to determine e.g. if there's a high level of traffic within the past x minutes. If so, it generates a traffic events that need to be actioned somehow.

Other 'Processor's can be implemented, such as persisting the data into a time-series database.

**Action**

The display to terminal Action displays the calculated statistics and important information like high-traffic alerts in the screen.

Other 'Action's can be implemented such as sending an email notification.


We can easily add e.g. multiple processors/actions instances to notify in a publish-subscribe form as the project grows.
