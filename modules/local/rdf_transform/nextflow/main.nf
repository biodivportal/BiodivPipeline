// nf-core module: tabular dataset (+ RML mapping) → RDF, via the WP8
// RDF Matching and Transformation Service.
//
// The service ships as its own container. Each task starts its FastAPI app
// on localhost, runs /validate as a pre-flight (aborts if the mapping is
// broken or drifted from the ontology), then calls /transform. Same HTTP
// path the WP7 Schema Editor uses, so errors look identical for every caller.
//
// Tunables via task.ext:
//   output_format  'turtle' (default) | 'ntriples' | 'jsonld'
//   delimiter      'COMMA' (default) | 'TAB' | ';' | …   (tabular input only)
//   source_type    'CSV' (default) | 'JSON'
//   skip_validate  false (default) — set true to bypass the /validate gate

process RDF_TRANSFORM {
    tag "rdf_transform"
    label 'process_low'

    container "ghcr.io/biodivportal/rdf-matching-and-transformation-service:0.1"

    input:
    path dataset      // tabular records to transform (CSV / TSV / JSON)
    path schema       // RML mapping that drives the transformation

    output:
    path "transformed.${ext}", emit: rdf         // the materialized RDF
    path "validate.json",      emit: validate    // raw /validate pre-flight result
    path "versions.yml",       emit: versions

    script:
    def output_format = task.ext.output_format ?: 'turtle'
    def delimiter     = task.ext.delimiter     ?: 'COMMA'
    def source_type   = task.ext.source_type   ?: 'CSV'
    def skip_validate = task.ext.skip_validate ?: false
    // Output file extension follows the requested RDF serialization.
    // (No `def`, so the output: block above can see it.)
    ext = output_format == 'jsonld'
            ? 'jsonld'
            : (output_format == 'ntriples' ? 'nt' : 'ttl')
    """
    # Start the service on localhost, kill it when the task ends.
    uvicorn main:app --host 127.0.0.1 --port 8000 \\
        --app-dir /app --log-level warning &
    SERVICE_PID=\$!
    trap "kill \$SERVICE_PID 2>/dev/null" EXIT

    # Wait until it answers (30 s ceiling for the ontology load on cold start).
    for i in \$(seq 1 60); do
        if curl -sf http://127.0.0.1:8000/ > /dev/null 2>&1; then break; fi
        sleep 0.5
    done

    # Pre-flight: validate the mapping against the loaded ontologies.
    curl -sf -X POST http://127.0.0.1:8000/validate \\
        -F "mapping_schema=@${schema}" \\
        -o validate.json

    # Abort the task if the mapping is invalid (unless skipped).
    if [ "${skip_validate}" != "true" ]; then
        python3 -c "import json,sys; r=json.load(open('validate.json')); \\
sys.exit(0 if r['valid'] else (print('Model validation failed:', file=sys.stderr) \\
or [print(f'  {i}', file=sys.stderr) for i in r['issues']] or 1))"
    fi

    # Transform: materialize the RDF into transformed.<ext>.
    curl -sf -X POST http://127.0.0.1:8000/transform \\
        -F "dataset=@${dataset}" \\
        -F "mapping_schema=@${schema}" \\
        -F "source_type=${source_type}" \\
        -F "delimiter=${delimiter}" \\
        -F "output_format=${output_format}" \\
        -o "transformed.${ext}"

    # Record the service version for the pipeline's versions report.
    SERVICE_VERSION=\$(curl -sf http://127.0.0.1:8000/ | python3 -c "import json,sys;print(json.load(sys.stdin)['version'])")
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        rdf-matching-and-transformation-service: \$SERVICE_VERSION
    END_VERSIONS
    """
}
