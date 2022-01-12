# opentelem-python

_Note: This package is part of the [Runtime Insights Early Access Program](https://about.codecov.io/product/feature/runtime-insights/)._

## Purpose

This package allows Python projects to leverage Codecov's [Runtime Insights](https://about.codecov.io/product/feature/runtime-insights/) feature.

More information about Runtime Insights can be found [in Codecov's public documentation](https://docs.codecov.com/docs/runtime-insights).

## Requirements and Pre-requisites

1. A repository that is active on [Codecov](https://codecov.io)
2. A profiling token for that repository, obtainable from Codecov.
3. Python version >=3.6

## Installation

First, install the package:

```
pip install codecovopentelem
```

Second, include the following snippet in your application. Where this is snippet is placed varies depending on the application, see _Integration Examples_ below.

The snippet:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
    SimpleSpanProcessor,
)
from opentelemetry import trace

from codecovopentelem import (
    CoverageSpanFilter,
    get_codecov_opentelemetry_instances,
)
from utils.time import format_time

provider = TracerProvider()
trace.set_tracer_provider(provider)

"""
CONFIGURATION
"""
current_version = "your-application-version"
current_env = "your-application-envrionment"
code=f"{current_version}:{current_env}"
export_rate = 0.01
repository_token="your-repository-profiling-token"
untracked_export_rate = 0

generator, exporter = get_codecov_opentelemetry_instances(
    repository_token=repository_token,
    version_identifier=current_version,
    sample_rate=export_rate,
    filters={
        CoverageSpanFilter.span_kind_filter: [
            trace.SpanKind.SERVER,
            trace.SpanKind.CONSUMER,
        ],
    },
    code=code,
    untracked_export_rate=untracked_export_rate,
    environment=current_env,
)
provider.add_span_processor(generator)
provider.add_span_processor(BatchSpanProcessor(exporter))
```

### Integration Examples

The specifics of how this library is integrated into your project depends on the project itself. This section contains a few common, framework specific, integration approaches along with the general integration approach at the end.

Note that these examples demonstrate _possible_ ways to incorporate this package into your project. As always, your specific needs may vary.

#### Flask

In a Flask application, you could place the code snippet in your application's `app.py` file _before_ the call to initialize your Flask app, like so:

```python

from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Snippet Code ...
# Other Startup Code ...

app = Flask(
    __name__,
    static_url_path='',
    static_folder='',
    template_folder='templates',
)

FlaskInstrumentor().instrument_app(app)

# app.route(...)
# ...

app.run(host='0.0.0.0', port=8080)
```

#### Django

In Django, you can place this snippet in your application's `<application_name>/wsgi.py` file:

```python

import os

from django.core.wsgi import get_wsgi_application

from utils.config import get_settings_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_settings_module())

#... Other Startup Code

from opentelemetry.instrumentation.django import DjangoInstrumentor
try:
    # Snippet Code
except UnableToStartProcessorException:
    # Handle the Exception...

DjangoInstrumentor().instrument()


application = get_wsgi_application()
```

Note that this example also demonstrates how to integrate using a `try/except`.

#### General Integration

If you are not using Django or Flask integration is still possible using the above code snippet. How to do this may vary greatly depending on your use case. In general, though, the code snippet should be placed wherever you would put your application's OpenTelemetry startup code. In lieu of that, this code should be incorporated in such a way that it is part of your application's startup process.

## Configuration

- `current_version` -- _(Required)_ The current version of the application. This can be semver, a commit SHA, or whatever is meaningful to you, but it should uniquely identify the particular version of the code.
- `current_env` -- _(Required)_ The environment in which the application is currently running. Typically "production", but can be other values as well (e.g., "local" / "dev" for testing during setup of the package, "test" for instrumenting in your test environment, etc.)
- `code` -- A unique identifier for the current deployment across all environments where it may be deployed. Conventionally, this is a combination of version number and environment name, but can be anything as long as it is unique in each environment for the version being deployed.
- `export_rate` -- _(Required. Min: 0, Max: 1)_ The percentage of your application's calls that are instrumented using this package. Using this package does incur some performance overhead, and instrumenting 100% of calls is not required. Therefore, for most applications, it is recommended to use 0.01 to 0.05 as the default value. However, low traffic applications may want to use a larger number (such as 0.1 or more).
- `repository_token` -- _(Required)_ The identifying token for this repository. Currently only obtainable by being selected for Codecov's [Runtime Insights Early Access Program](https://about.codecov.io/product/feature/runtime-insights/). It should be treated as a sensitive credential (e.g., not committed to source control, etc.)
- `untracked_export_rate` -- Currently unused, should remain at 0.

If desired, the `filters` parameter can also be changed to provide different filtering on any valid OpenTelemetry `SpanKind` as [defined by the specification](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/api.md#spankind).

## Codecov.yml Changes

You will need to update your `codecov.yml` as follows:

```
comment:
  layout: 'reach,diff,flags,tree,betaprofiling'
  show_critical_paths: true

```

[You can read more about the codecov.yml in Codecov's public documentation](https://docs.codecov.com/docs/codecov-yaml). If you do not have a `codecov.yml` in your project, you can create the file in the root of your project and add the above configuration.
