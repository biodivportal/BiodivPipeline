# Runtime and Resource Monitoring

BiodivPipeline automatically measures end-to-end runtime and resource consumption for every pipeline run. This is configured in `nextflow.config` and requires no additional setup.

## Output Files

All files are written to `<outdir>/pipeline_info/` and include a timestamp suffix to distinguish between runs.

| File | Format | Contents |
|------|--------|---------|
| `execution_report_<timestamp>.html` | HTML | Per-process CPU, memory, and duration charts |
| `execution_timeline_<timestamp>.html` | HTML | Visual timeline showing when each module ran |
| `execution_trace_<timestamp>.txt` | TSV | Raw metrics for every process (see fields below) |
| `pipeline_dag_<timestamp>.html` | HTML | Directed acyclic graph of the pipeline structure |

## Trace Fields

The trace file records the following fields for each process:

| Field | Description |
|-------|-------------|
| `task_id` | Unique task identifier |
| `name` | Process name |
| `status` | Completed / failed / cached |
| `exit` | Exit code |
| `duration` | Wall-clock time from submission to completion |
| `realtime` | Actual execution time |
| `cpus` | Number of CPUs allocated |
| `%cpu` | Actual CPU usage (%) |
| `memory` | Memory allocated |
| `%mem` | Actual memory usage (%) |
| `rss` | Resident set size (actual RAM used) |
| `vmem` | Virtual memory used |
| `peak_rss` | Peak RAM usage |
| `peak_vmem` | Peak virtual memory usage |
| `rchar` | Bytes read from disk |
| `wchar` | Bytes written to disk |

## Why `fields` Was Added

The default trace output only includes a small subset of metrics. The `fields` line was explicitly added to `nextflow.config` to capture detailed CPU, memory, and disk I/O metrics — which are required for the end-to-end resource consumption evaluation.

## Configuration

```groovy
// nextflow.config
timeline {
    enabled = true
    file    = "${params.outdir}/pipeline_info/execution_timeline_${params.trace_report_suffix}.html"
}
report {
    enabled = true
    file    = "${params.outdir}/pipeline_info/execution_report_${params.trace_report_suffix}.html"
}
trace {
    enabled = true
    file    = "${params.outdir}/pipeline_info/execution_trace_${params.trace_report_suffix}.txt"
    fields  = 'task_id,name,status,exit,duration,realtime,cpus,%cpu,memory,%mem,rss,vmem,peak_rss,peak_vmem,rchar,wchar'
}
dag {
    enabled = true
    file    = "${params.outdir}/pipeline_info/pipeline_dag_${params.trace_report_suffix}.html"
}
```

## Usage for Req. 9 Evaluation

When the full pipeline is run against the BGBM dataset, the trace file provides the raw data needed for the end-to-end evaluation:

- **Runtime:** `duration` and `realtime` fields per module, total wall-clock time from the timeline
- **CPU consumption:** `%cpu` and `cpus` fields per module
- **Memory consumption:** `peak_rss` for actual peak RAM usage per module
- **Disk I/O:** `rchar` and `wchar` for read/write volume per module

The HTML report and timeline provide visual summaries.