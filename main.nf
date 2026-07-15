#!/usr/bin/env nextflow
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    nf-core/biodivpipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    A modular nf-core workflow for FAIR biodiversity data processing.
    Transforms raw CSV biodiversity records into quality-annotated,
    taxonomically resolved RDF triples.
----------------------------------------------------------------------------------------
*/

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT FUNCTIONS / MODULES / SUBWORKFLOWS / WORKFLOWS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { BIODIVPIPELINE          } from './workflows/biodivpipeline'
include { PIPELINE_INITIALISATION } from './subworkflows/local/utils_nfcore_biodivpipeline_pipeline'
include { PIPELINE_COMPLETION     } from './subworkflows/local/utils_nfcore_biodivpipeline_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    NAMED WORKFLOWS FOR PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

//
// WORKFLOW: Run main analysis pipeline
//
workflow NFCORE_BIODIVPIPELINE {

    take:
    ch_input   // channel: path to input CSV

    main:

    // Resolve the mapping schema — use provided or fall back to default stub
    def ch_schema = params.mapping_schema
        ? channel.fromPath(params.mapping_schema, checkIfExists: true)
        : channel.fromPath("${projectDir}/assets/default_mapping.jsonld", checkIfExists: true)

    def ch_meta = channel.fromPath("${projectDir}/modules/local/rdf_transform/nextflow/meta.yml", checkIfExists: true)

    //
    // WORKFLOW: Run pipeline
    //
    BIODIVPIPELINE (
        ch_input,
        ch_schema,
        ch_meta,
        params.outdir,
    )

    emit:
    final_dataset = BIODIVPIPELINE.out.final_dataset
    rdf_turtle = BIODIVPIPELINE.out.rdf_turtle
    summary    = BIODIVPIPELINE.out.summary
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow {

    main:
    //
    // SUBWORKFLOW: Run initialisation tasks
    //
    PIPELINE_INITIALISATION (
        params.version,
        params.validate_params,
        params.monochrome_logs,
        args,
        params.outdir,
        params.input,
        params.help,
        params.help_full,
        params.show_hidden
    )

    // Input channel comes from the initialisation subworkflow
    // (validates params and creates the channel from --input path)
    def ch_input = PIPELINE_INITIALISATION.out.input

    //
    // WORKFLOW: Run main workflow
    //
    NFCORE_BIODIVPIPELINE ( ch_input )

    //
    // SUBWORKFLOW: Run completion tasks
    //
    PIPELINE_COMPLETION (
        params.email,
        params.email_on_fail,
        params.plaintext_email,
        params.outdir,
        params.monochrome_logs,
    )
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
