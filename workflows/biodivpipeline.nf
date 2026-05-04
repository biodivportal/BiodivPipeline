/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { COLUMN_STANDARDISE   } from '../modules/local/column_standardise/main'
include { BIODIV_ANNOTATE      } from '../modules/local/biodiv_annotate/main'
include { TAXONOMY_CLASSIFY    } from '../modules/local/taxonomy_classify/main'
include { OUTLIER_DETECT       } from '../modules/local/outlier_detect/main'
include { PROVISIONAL_CONCEPTS } from '../modules/local/provisional_concepts/main'
include { RDF_TRANSFORM        } from '../modules/local/rdf_transform/main'
include { COLLECT_REPORTS      } from '../modules/local/collect_reports/main'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow BIODIVPIPELINE {

    take:
    ch_input       // channel: path to input CSV file
    ch_schema      // channel: path to RDF mapping schema (JSON-LD or Turtle)
    outdir

    main:

    def ch_versions = channel.empty()

    //
    // STEP 1: Column Standardisation (WP6)
    // Map heterogeneous CSV headers to ABCD standard terms
    //
    COLUMN_STANDARDISE( ch_input )
    ch_versions = ch_versions.mix(COLUMN_STANDARDISE.out.versions)

    def ch_standardised = COLUMN_STANDARDISE.out.csv

    //
    // STEP 2: Parallel processing — Annotation, Taxonomy, Outlier Detection
    // These three modules run concurrently on the standardised data
    //

    // WP2: BiodivPortal Annotator
    BIODIV_ANNOTATE( ch_standardised )
    ch_versions = ch_versions.mix(BIODIV_ANNOTATE.out.versions)

    // WP3: Land Taxonomy Classifier
    TAXONOMY_CLASSIFY( ch_standardised )
    ch_versions = ch_versions.mix(TAXONOMY_CLASSIFY.out.versions)

    // WP4: Outlier & Data-Quality Detection
    OUTLIER_DETECT( ch_standardised )
    ch_versions = ch_versions.mix(OUTLIER_DETECT.out.versions)

    //
    // STEP 3: Provisional Concept Registration (WP5)
    // Runs after Annotator — picks up unresolved terms
    //
    PROVISIONAL_CONCEPTS( BIODIV_ANNOTATE.out.unresolved )
    ch_versions = ch_versions.mix(PROVISIONAL_CONCEPTS.out.versions)

    //
    // STEP 4: RDF Transformation (WP7)
    // Combines cleaned data + annotations + taxonomy + expert mapping schema
    //
    RDF_TRANSFORM(
        ch_standardised,
        BIODIV_ANNOTATE.out.annotations,
        TAXONOMY_CLASSIFY.out.resolved,
        ch_schema
    )
    ch_versions = ch_versions.mix(RDF_TRANSFORM.out.versions)

    //
    // STEP 5: Collect all reports into a pipeline summary
    //
    COLLECT_REPORTS(
        OUTLIER_DETECT.out.report,
        RDF_TRANSFORM.out.report,
        COLUMN_STANDARDISE.out.mapping,
        PROVISIONAL_CONCEPTS.out.concepts
    )

    //
    // Collate software versions
    //
    softwareVersionsToYAML(ch_versions)
        .collectFile(
            storeDir: "${outdir}/pipeline_info",
            name: 'biodivpipeline_software_versions.yml',
            sort: true,
            newLine: true
        )

    emit:
    rdf_turtle   = RDF_TRANSFORM.out.rdf_turtle       // channel: path to Turtle RDF output
    rdf_jsonld   = RDF_TRANSFORM.out.rdf_jsonld        // channel: path to JSON-LD RDF output
    quality      = OUTLIER_DETECT.out.report            // channel: path to quality report
    flagged      = OUTLIER_DETECT.out.flagged           // channel: path to flagged records
    taxonomy     = TAXONOMY_CLASSIFY.out.resolved       // channel: path to resolved taxonomy
    summary      = COLLECT_REPORTS.out.summary           // channel: path to pipeline summary
    versions     = ch_versions                           // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
