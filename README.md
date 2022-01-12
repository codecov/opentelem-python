# opentelem-python

_Note: This package is part of the [Runtime Insights Early Access Program](https://about.codecov.io/product/feature/runtime-insights/)._

## Purpose

This package allows Python projects to leverage Codecov's [Runtime Insights](https://about.codecov.io/product/feature/runtime-insights/) feature.

## Requirements and Pre-requisites

1. A repository that is active on [Codecov](https://codecov.io)
2. A profiling token for that repository, obtainable from Codecov.
3. Python version >=3.6

## Installation

First, install the package:

```
pip install codecovopentelem
```

Second, include the following snippet in your application's startup / bootstrapping process:

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
export_rate = 10
untracked_export_rate = 0
profiling_token="your-profiling-token"


generator, exporter = get_codecov_opentelemetry_instances(
    repository_token=profiling_token,
    version_identifier=current_version,
    sample_rate=export_rate,
    filters={
        CoverageSpanFilter.regex_name_filter: None,
        CoverageSpanFilter.span_kind_filter: [
            trace.SpanKind.SERVER,
            trace.SpanKind.CONSUMER,
        ],
    },
    code=f"{current_version}:{current_env}",
    untracked_export_rate=untracked_export_rate,
    environment=current_env,
)
provider.add_span_processor(generator)
provider.add_span_processor(BatchSpanProcessor(exporter))
```

## Configuration

- `current_version` -- _(Required)_ The current version of the application. This can be semver, a commit SHA, or whatever is meaningful to you, but it should uniquely identify the particular version of the code.
- `current_env` -- _(Required)_ The environment in which the application is currently running. Typically "production", but can be other values as well (e.g., "local" / "dev" for testing during setup of the package, "test" for instrumenting in your test environment, etc.)
- `export_rate` -- _(Required)_ The percentage of your application's calls that are instrumented using this package. Using this package does incur some performance overhead, and instrumenting 100% of calls is not required. Therefore, for most applications, it is recommended to use 10 as the default value. However, low traffic applications may want to use a larger number (such as 30 or 50), and highly trafficked applications may want to use a smaller number (such as 1 or 5).
- `repository_token` -- _(Required)_ The identifying token for this repository. Currently only obtainable by being selected for Codecov's [Runtime Insights Early Access Program](https://about.codecov.io/product/feature/runtime-insights/). It should be treated as a sensitive credential (e.g., not committed to source control, etc.)
- `untracked_export_rate` -- Currently unused, should remain at 0.

## Codecov.yml Changes

You will need to update your `codecov.yml` as follows:

```
comment:
  layout: 'reach,diff,flags,tree,betaprofiling'
  show_critical_paths: true

```

If you do not have a `codecov.yml` in your project, you can create the file in the root of your project and add the above configuration.
